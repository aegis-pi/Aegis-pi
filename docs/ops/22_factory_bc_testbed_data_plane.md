# Factory B/C Testbed Data Plane

상태: source of truth  
기준일: 2026-05-28

## 목적

`factory-b`, `factory-c` 테스트베드형 Spoke에서 더미 데이터를 생성하고, 공통 `edge-iot-publisher`를 통해 IoT Core와 S3 raw 경로까지 전송하는 운영 기준을 정리한다.

이 문서는 `factory-b/c`가 실제 공장을 대체한다는 의미가 아니라, 멀티 factory 배포/수집/분리 흐름을 검증하기 위한 기준이다.

## 결정

`factory-b/c`의 dummy data generator는 Kubernetes Deployment가 아니라 VM 로컬 script 또는 systemd service로 시작한다. Hub ArgoCD는 `edge-iot-publisher`만 공통 Helm chart로 배포한다. VM 로컬 dummy publisher systemd는 현재 표준 운영 경로가 아니며, 과거 smoke/legacy 용도로만 남긴다.

```text
factory-b/c worker node
  local dummy generator
    -> /var/lib/aegis/outbox/*.json

K3s workload on same worker node
  edge-iot-publisher Pod
    -> hostPath /var/lib/aegis/outbox
    -> AWS IoT Core
    -> S3 raw/factory-b 또는 raw/factory-c
```

`factory-a`와의 차이는 아래처럼 둔다.

| 항목 | `factory-a` 운영형 | `factory-b/c` 테스트베드형 |
| --- | --- | --- |
| 데이터 생산자 | `factory-a-log-adapter` Pod | VM 로컬 dummy generator |
| outbox 저장소 | Longhorn PVC | worker node hostPath |
| publisher | `edge-iot-publisher` Pod | `edge-iot-publisher` Pod |
| 배포 기준 | ArgoCD + manual/conservative | ArgoCD + testbed values |
| 검증 목적 | 실제 edge data-plane | 멀티 factory 흐름 검증 |

## Helm Values 기준

공통 chart는 `charts/aegis-spoke`를 사용하고, 공장별 차이는 GitOps repo의 values에서 관리한다.

```text
aegis-pi-gitops
├── charts/aegis-spoke/
└── envs/
    ├── factory-a/values.yaml
    ├── factory-b/values.yaml
    └── factory-c/values.yaml
```

목표 values 기준은 아래와 같다.

`factory-a`:

```yaml
outbox:
  type: pvc
  path: /var/lib/aegis/outbox
  storage:
    size: 1Gi
    accessModes:
      - ReadWriteOnce
    storageClassName: longhorn

factoryALogAdapter:
  enabled: true

edgeIotPublisher:
  enabled: true
```

`factory-b/c`:

```yaml
outbox:
  type: hostPath
  path: /var/lib/aegis/outbox

factoryALogAdapter:
  enabled: false

edgeIotPublisher:
  enabled: false  # IoT Secret 준비 전 임시 상태

placement:
  nodeSelector:
    aegis.workload-node: "true"
```

IoT Secret 준비 후 현재 운영 기준에서는 `factory-b/c`에서 K3s publisher를 켠다.

```yaml
edgeIotPublisher:
  enabled: true
  iot:
    secretName: aws-iot-factory-b-cert
```

`factory-c`는 `aws-iot-factory-c-cert`를 사용한다.

## Chart 변경 기준

`charts/aegis-spoke`는 `outbox.type`에 따라 volume을 분기해야 한다.

```text
outbox.type=pvc:
  - PersistentVolumeClaim 생성
  - Deployment volume은 persistentVolumeClaim 사용

outbox.type=hostPath:
  - PersistentVolumeClaim 생성하지 않음
  - Deployment volume은 hostPath 사용
```

hostPath volume 기준:

```yaml
volumes:
  - name: outbox
    hostPath:
      path: /var/lib/aegis/outbox
      type: DirectoryOrCreate
```

`hostPath`는 node-local storage이므로, publisher Pod는 반드시 dummy generator가 파일을 쓰는 worker node에 떠야 한다. 따라서 `factory-b/c` worker node에는 아래 label을 유지한다.

```text
aegis.workload-node=true
```

## VM Worker 준비

각 VM의 worker node에서 outbox 디렉터리를 만든다.

`factory-b` worker:

```bash
sudo mkdir -p /var/lib/aegis/outbox
sudo chown -R oosnim:oosnim /var/lib/aegis/outbox
chmod 750 /var/lib/aegis/outbox
```

`factory-c` worker:

```bash
sudo mkdir -p /var/lib/aegis/outbox
sudo chown -R aegis:aegis /var/lib/aegis/outbox
chmod 750 /var/lib/aegis/outbox
```

확인:

```bash
ls -ld /var/lib/aegis/outbox
```

## Local Dummy Generator 기준

초기 generator는 factory별 CLI script로 시작한다.

```bash
AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox \
  python3 apps/dummy-sensor/factory_b_dummy_generator.py --once all
```

`factory-c`:

```bash
AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox \
  python3 apps/dummy-sensor/factory_c_dummy_generator.py --once all
```

상시 실행은 `apps/dummy-sensor/docs/factory-b-c-dummy-systemd-runbook.md`의 systemd 유닛 기준을 따른다.

생성 파일은 M4 canonical JSON 계약을 따른다.

```text
/var/lib/aegis/outbox/<message_id>.json
```

write 방식:

1. `outbox/tmp`에 임시 파일 작성
2. fsync 또는 flush
3. outbox root의 `<message_id>.json`으로 atomic rename

publisher는 publish 성공 후 파일을 삭제한다. invalid JSON은 `outbox/quarantine/`으로 이동한다.

## 운영 스크립트 기준

Hub를 내리기 전과 다시 올린 뒤에는 repository의 운영 스크립트를 사용한다.

```bash
scripts/destroy/stop-dummy-generators.sh
scripts/ops/manage-dummy-generators.sh start factory-b
scripts/ops/manage-dummy-generators.sh start factory-c
scripts/ops/manage-dummy-generators.sh status factory-b
scripts/ops/manage-dummy-generators.sh status factory-c
```

접속 정보 기본값은 `scripts/ops/dummy-generators.env`에서 읽는다. 다른 값을 쓰려면 `AEGIS_DUMMY_GENERATORS_ENV=/path/to/file`을 지정한다.

`manage-dummy-generators.sh start/status`는 local dummy generator만 다룬다. `stop`은 generator를 멈추고, legacy local dummy publisher unit이 설치돼 있으면 함께 멈춘다. 현재 publish는 K3s `edge-iot-publisher`가 담당하므로 local publisher service가 없는 것은 정상이다.

개발 중 Hub 비용 절감을 위해 Hub만 내리고 data-pipeline을 유지하는 경우에는 dummy generator를 멈추지 않는다. Hub ArgoCD가 내려가도 기존 Spoke K3s `edge-iot-publisher` pod가 Running이면 outbox -> IoT Core publish는 계속 가능하다.

출근 후 Hub를 다시 올리고 Spoke를 다시 등록할 때는 기존 publisher pod를 불필요하게 재시작하지 않도록 Hub-only reconnect 모드를 사용한다.

```bash
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-b.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-c.sh [MFA_OTP]
scripts/ops/check-spoke-publisher-safety.sh factory-b factory-c
```

GitOps values/image 변경을 실제 반영해야 하는 경우에만 `SYNC_SPOKE_APP=true`를 명시한다.

## 진행 순서

2026-05-21 기준 아래 순서는 완료됐다. 이후 재구축 또는 장애 복구 시 같은 순서로 반복한다.

1. `factory-b/c` cluster registration과 ApplicationSet 생성을 완료한다.
2. `charts/aegis-spoke`에 `outbox.type` 분기를 추가한다.
3. `factory-b/c` values를 `outbox.type: hostPath`로 변경한다.
4. ApplicationSet을 재적용하고 `aegis-spoke-factory-b/c`가 `Synced` 되는지 확인한다.
5. VM worker node에 `/var/lib/aegis/outbox`를 준비한다.
6. local dummy generator script를 작성하고 outbox 파일 생성을 확인한다.
7. `factory-b/c` IoT Thing/certificate/K3s Secret을 생성한다.
8. `factory-b/c` values에서 `edgeIotPublisher.enabled: true`로 전환한다.
9. Application sync 후 publisher Pod가 Running인지 확인한다.
10. S3 raw prefix 분리 적재를 확인한다.

## 검증 명령

Application:

```bash
kubectl -n argocd get application aegis-spoke-factory-b aegis-spoke-factory-c
```

Spoke namespace:

```bash
kubectl --kubeconfig ~/Aegis/.aegis/secrets/kubeconfig/factory-b.tailscale-ip.kubeconfig -n ai-apps get all,pvc,sa
kubectl --kubeconfig ~/Aegis/.aegis/secrets/kubeconfig/factory-c.tailscale-ip.kubeconfig -n ai-apps get all,pvc,sa
```

outbox:

```bash
find /var/lib/aegis/outbox -maxdepth 2 -type f -print
```

S3 raw:

```bash
aws s3 ls s3://aegis-bucket-data/raw/factory-b/ --recursive --region ap-south-1
aws s3 ls s3://aegis-bucket-data/raw/factory-c/ --recursive --region ap-south-1
```

## 현재 알려진 상태

2026-05-21 기준:

- `factory-b` Tailnet IP: `100.98.121.77`
- `factory-b` worker IP/user: `192.168.128.11`, `oosnim`
- `factory-c` Tailnet IP: `100.76.243.72`
- `factory-c` worker IP/user: `192.168.56.20`, `aegis`
- Hub ArgoCD cluster Secret: `cluster-factory-b`, `cluster-factory-c`
- egress Service: `factory-b-master-tailnet`, `factory-c-master-tailnet`
- Application: `aegis-spoke-factory-b`, `aegis-spoke-factory-c`
- GitOps chart `outbox.type: pvc|hostPath` 분기 지원, `factory-b/c` values `hostPath` 전환 완료 (aegis-pi-gitops commit `04f90b2`, remote push 완료)
- factory-b worker1 `/var/lib/aegis/outbox`: `drwxrwx--- 10001:10001` 생성 확인
- factory-c worker `/var/lib/aegis/outbox`: 생성 확인 (kubectl pod exit 0, uid 10001 write 성공)
- factory-b/c local dummy generator systemd service 배포 및 canonical JSON 생성 확인
- factory-b/c IoT Thing/certificate/K3s Secret 준비 완료
- factory-b/c `edge-iot-publisher` Pod Running 확인
- S3 raw prefix 분리 적재 확인: `raw/factory-b/...`, `raw/factory-c/...`
- 다음 단계: Lambda data processor가 S3 raw 이후 DynamoDB LATEST/HISTORY, S3 processed, `pipeline_status`를 갱신하도록 구현

### factory-c 네트워크 및 Flannel/CoreDNS 통신 장애 조치 내역 (2026-05-20)

**문제 현상**:
VirtualBox NAT 네트워크 복제 설정으로 인해 `factory-c-master`와 `factory-c-worker` VM의 `INTERNAL-IP`가 둘 다 `10.0.2.15`로 중복 등록되었습니다. 이로 인해 K3s flannel CNI를 통한 노드 간 VXLAN 터널링 및 Pod-to-Pod 통신이 차단되었고, `edge-iot-publisher` Pod에서 CoreDNS를 찾지 못해 `Temporary failure in name resolution` 오류가 발생하며 AWS IoT로 데이터를 전송하지 못했습니다.

**조치 사항**:
NAT IP 충돌 문제를 방지하기 위해, 각 VM의 호스트 전용 어댑터(Host-only Adapter) 인터페이스인 `enp0s8`의 고유 IP 대역을 K3s 및 Flannel의 CNI 바인딩용 인터페이스로 강제 지정하였습니다.

1. **`factory-c-master` 설정**:
   - `/etc/rancher/k3s/config.yaml` 파일에 아래 설정을 적용하여 내부 IP와 flannel 인터페이스를 고정:
     ```yaml
     node-ip: 192.168.56.10
     flannel-iface: enp0s8
     ```
   - 설정 후 K3s 서비스 재시작: `sudo systemctl restart k3s`

2. **`factory-c-worker` 설정**:
   - `/etc/rancher/k3s/config.yaml` 파일에 아래 설정을 적용:
     ```yaml
     node-ip: 192.168.56.20
     flannel-iface: enp0s8
     ```
   - 설정 후 K3s-agent 서비스 재시작: `sudo systemctl restart k3s-agent`

**결과**:
`kubectl get nodes -o wide` 실행 시 노드들의 `INTERNAL-IP`가 중복 없이 각각 `192.168.56.10`, `192.168.56.20`으로 올바르게 인식되며, 멀티 노드 간 네트워크 통신이 복구되어 `edge-iot-publisher`의 CoreDNS 질의 및 AWS IoT Core publish가 정상화되었습니다.

---

### factory-b 워커 노드 시각 동기화 (Clock Drift) 조치 내역 (2026-05-20)

**문제 현상**:
Factory B의 더미 생성기(`dummy-generator`)가 생성한 파일명 및 데이터 내 타임스탬프 시각과 S3의 LastModified 시각 사이에 약 32분의 시간 오차(Clock Drift)가 발생하였습니다 (예: 파일명 내 시간은 `08:34 UTC`이나 실제 전송 및 업로드 시각은 `09:06 UTC`).

**원인**:
Factory B의 `worker1` VM 노드의 시스템 시간이 실제 시각보다 32분 정도 느리게 차이가 나고 있었고, 이로 인해 로컬 파일 생성기 시각이 부정확해졌습니다. 시스템에 설치된 `chrony` 데몬이 작동하고 있었으나 오차의 임계치 기준을 초과하여 자동 도약 동기화가 중단된 상태였습니다.

**조치 사항**:
`worker1` 노드 내부에서 NTP 시간 강제 동기화 도약 명령을 수행하여 클럭 오차를 복구했습니다.
```bash
# factory-b worker1 노드에서 실행
sudo chronyc makestep
```

**결과**:
- 조치 전 `worker1` 시스템 시간: `08:37 UTC`
- 조치 후 `worker1` 시스템 시간: `09:08 UTC` (실제 표준 시각과 동기화 완료)
- 동기화 직후 더미 생성기에서 생성되는 파일의 타임스탬프(`09:09Z`)와 S3 저장 메타데이터 상의 최종 수정 일시가 실시간 정합성을 이루게 되었습니다.
