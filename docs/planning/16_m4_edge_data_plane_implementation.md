# M4 Edge Data-Plane 구현 기록

상태: 완료 기록
기준일: 2026-05-19

## 목적

M4 Issues 2~5를 단일 세션에서 완료한 과정을 기록한다.
ECR 이미지 빌드부터 factory-a K3s 배포, S3 raw 적재 검증까지 전 과정의 결정 사항과 버그 수정 내역을 포함한다.

---

## 컴포넌트 구조

```text
factory-a K3s (ai-apps namespace, worker2)
  factory-a-log-adapter
    -> InfluxDB safe_edge_db (HTTP query)
    -> Kubernetes API (in-cluster ServiceAccount)
    -> /var/lib/aegis/outbox/{message_id}.json  (Longhorn PVC 공유)

  edge-iot-publisher
    -> /var/lib/aegis/outbox/{message_id}.json  (Longhorn PVC 공유)
    -> AWS IoT Core MQTT 8883 (mTLS, QoS0)
    -> IoT Rule
    -> S3 raw (aegis-bucket-data)
```

두 컴포넌트는 Longhorn PVC(`aegis-spoke-outbox`, 1Gi, RWO)를 통해 outbox를 공유한다.
adapter가 canonical JSON을 atomic rename으로 넣고, publisher가 읽어 전송 후 삭제한다.

---

## ECR 저장소 및 이미지 전략

```text
611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/factory-a-log-adapter
611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/edge-iot-publisher
```

- Terraform `infra/foundation/ecr.tf`에서 두 저장소와 lifecycle policy를 생성했다.
- tag 전략: `sha-<7-char-git-sha>` 고정 배포 tag, `main`/`latest`는 moving debug tag
- `.github/workflows/build-push.yaml` matrix 빌드: `edge-agent`, `factory-a-log-adapter`, `edge-iot-publisher` 3개 이미지

검증 기준 image tag: `sha-f71a104`

---

## Helm Chart 구조

chart: `charts/aegis-spoke`
factory-a values: `envs/factory-a/values.yaml`

배포 namespace: `ai-apps` (기존 IoT Secret 재사용)
placement: `kubernetes.io/hostname=worker2`

추가된 chart 설정:

```yaml
imagePullSecrets:
  - name: ecr-registry

podSecurityContext:
  fsGroup: 10001

outbox:
  storage:
    storageClassName: longhorn
```

RBAC: adapter가 Kubernetes API node/pod status를 조회하기 위한 ServiceAccount + ClusterRole/ClusterRoleBinding 포함

---

## 배포 방식

초기 M4 검증은 직접 배포 방식으로 완료했다.

```bash
helm template aegis-spoke charts/aegis-spoke \
  --namespace ai-apps \
  -f envs/factory-a/values.yaml \
  | kubectl apply -f -
```

factory-a master (10.10.10.10) SSH에서 실행. ECR pull secret `ecr-registry`는 별도로 ai-apps namespace에 사전 생성.

2026-05-19 기준 정식 배포 경로는 Hub ArgoCD ApplicationSet으로 전환했다.

```text
build-hub.sh
  -> Hub ArgoCD 설치
  -> Tailscale egress
  -> argocd/cluster-factory-a 등록

build-iot-factory-a.sh
  -> AWS IoT Thing/Policy/certificate
  -> factory-a K3s Secret
  -> hub_aegis_spoke_applicationset_bootstrap.yml
  -> aegis-spoke-factory-a Application
```

GitOps 기준:

```text
repo: https://github.com/aegis-pi/aegis-pi-gitops.git
chart: charts/aegis-spoke
values: envs/factory-a/values.yaml
destination: factory-a / ai-apps
```

---

## 발견된 버그와 수정

### Bug 1: CrashLoopBackOff (factory-a-log-adapter)

원인: Dockerfile CMD가 `--once all`로 설정되어 있어 한 번 실행 후 exit 0 → 재시작 반복.

수정: `apps/factory-a-log-adapter/Dockerfile`

```dockerfile
# 변경 전
CMD ["python", "/app/factory_a_log_adapter.py", "--once", "all"]

# 변경 후
CMD ["python", "/app/factory_a_log_adapter.py", "--loop"]
```

### Bug 2: PVC 권한 오류 (PermissionError on outbox)

원인: Longhorn PVC가 root 소유로 마운트되어 uid=10001(aegis) 컨테이너가 outbox/tmp 디렉토리에 쓰기 불가.

오류: `PermissionError: [Errno 13] Permission denied: '/var/lib/aegis/outbox/tmp'`

수정: 양쪽 Deployment의 pod spec에 `securityContext.fsGroup: 10001` 추가.
Kubernetes가 볼륨 마운트 시 group을 10001로 설정하고 g+rwx를 부여한다.

`charts/aegis-spoke/templates/factory-a-log-adapter-deployment.yaml`:

```yaml
spec:
  template:
    spec:
      securityContext:
        fsGroup: {{ .Values.podSecurityContext.fsGroup }}
```

### Bug 3: MQTT DNS 조회 실패 (Name or service not known)

원인: IoT endpoint를 Kubernetes Secret `endpoint.txt`에서 읽을 때 값 끝에 `\n`이 포함됨.
`socket.create_connection("xxx.iot.ap-south-1.amazonaws.com\n", 8883)` DNS 조회 실패.

수정: `apps/edge-iot-publisher/edge_iot_publisher.py`

```python
# 변경 전
endpoint = os.getenv("AEGIS_IOT_ENDPOINT")

# 변경 후
endpoint = (os.getenv("AEGIS_IOT_ENDPOINT") or "").strip() or None
```

### Bug 4: Cross-user 파일 읽기 권한 오류 (outbox 파일 0o600)

원인: `tempfile.NamedTemporaryFile` 기본 생성 mode가 0o600.
atomic rename 후 최종 파일이 0o600(owner-only)로 유지되어 publisher(uid=1000, supplemental group 10001)가 읽기 불가.

수정: `apps/factory-a-log-adapter/factory_a_log_adapter.py`

```python
tmp_path.replace(target)
target.chmod(0o640)  # group(10001) read 허용
```

---

## 수집 주기 및 데이터 확인

| source_type | 주기 | 내용 |
|---|---|---|
| `factory_state` | 3초 | 온도/습도/기압 평균, AI fire/fall/bend score 평균, abnormal_sound |
| `infra_state` | 20초 | 노드 상태, Pod 상태/restart count, heartbeat, 장치 summary |

실제 InfluxDB 데이터 확인:
- `environment_data`: 온도/습도/기압 정상 수집 확인
- `ai_detection`: fire/fall/bend 모두 0.0 (AI가 현재 이상 없음 판단)
- `acoustic_detection`: is_danger=0 → `abnormal_sound: "none"`

---

## S3 적재 검증 결과

검증 날짜: 2026-05-18

S3 경로 패턴:

```text
s3://aegis-bucket-data/raw/factory-a/factory_state/yyyy=2026/mm=05/dd=18/<message_id>.json
s3://aegis-bucket-data/raw/factory-a/infra_state/yyyy=2026/mm=05/dd=18/<message_id>.json
```

검증 결과:
- `factory_state`, `infra_state` 두 source_type 경로에 파일이 분리 적재됨 확인
- S3 object body가 canonical JSON 계약과 일치 확인
- 필수 envelope 필드(`schema_version`, `message_id`, `factory_id`, `node_id`, `environment_type`, `input_module_type`, `source_type`, `source_timestamp`, `published_at`, `data_plane_instance_id`, `payload`) 모두 존재 확인
- `ai_result` 포함 실제 InfluxDB 데이터 반영 확인

---

## 현재 상태 (2026-05-19 기준)

- 두 Pod는 Hub ArgoCD ApplicationSet의 배포 대상이다.
- Longhorn PVC(`aegis-spoke-outbox`)는 `ai-apps` namespace에서 outbox buffer로 사용한다.
- ECR 이미지(`sha-f71a104`)는 유지된다. `destroy-hub.sh`는 ECR을 삭제하지 않는다.
- IoT Certificate Secret(`aws-iot-factory-a-cert`)은 ai-apps namespace에 존재한다.
- ECR pull secret(`ecr-registry`)은 ai-apps namespace에 존재한다.

표준 재배포는 아래 순서다.

```bash
scripts/build/build-hub.sh
scripts/build/build-admin-ui-after-ns.sh
scripts/build/build-iot-factory-a.sh
scripts/build/verify-complete.sh
```

---

## 다음 단계 (M4 Issue 6)

Lambda data processor 구현:
- IoT Core Rule에서 Lambda 트리거 연결
- 수신 메시지 정규화 및 Risk Score 계산
- DynamoDB LATEST/HISTORY#STATE 갱신
- S3 processed 저장

Hub 재구성 시:
- `build-hub.sh`가 Hub 인프라와 Hub 내부 platform을 등록
- `build-iot-factory-a.sh`가 IoT Secret 준비 후 ArgoCD cluster Secret과 ApplicationSet을 배포
- `verify-complete.sh`가 Hub/IoT/factory-a rollout을 통합 검증
