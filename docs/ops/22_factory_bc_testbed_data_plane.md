# Factory B/C Testbed Data Plane

상태: source of truth  
기준일: 2026-05-20

## 목적

`factory-b`, `factory-c` 테스트베드형 Spoke에서 더미 데이터를 생성하고, 공통 `edge-iot-publisher`를 통해 IoT Core와 S3 raw 경로까지 전송하는 운영 기준을 정리한다.

이 문서는 `factory-b/c`가 실제 공장을 대체한다는 의미가 아니라, 멀티 factory 배포/수집/분리 흐름을 검증하기 위한 기준이다.

## 결정

`factory-b/c`의 dummy data generator는 Kubernetes Deployment가 아니라 VM 로컬 script 또는 systemd service로 시작한다. Hub ArgoCD는 `edge-iot-publisher`만 공통 Helm chart로 배포한다.

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
  enabled: false  # IoT Secret 준비 전

placement:
  nodeSelector:
    aegis.workload-node: "true"
```

IoT Secret 준비 후 `factory-b/c`에서 publisher를 켠다.

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

초기 generator는 CLI script로 시작한다.

```bash
python3 dummy_data_generator.py \
  --factory-id factory-b \
  --environment-type vm-mac \
  --input-module-type dummy \
  --scenario normal \
  --outbox-dir /var/lib/aegis/outbox
```

`factory-c`:

```bash
python3 dummy_data_generator.py \
  --factory-id factory-c \
  --environment-type vm-windows \
  --input-module-type dummy \
  --scenario warning \
  --outbox-dir /var/lib/aegis/outbox
```

생성 파일은 M4 canonical JSON 계약을 따른다.

```text
/var/lib/aegis/outbox/<message_id>.json
```

write 방식:

1. `outbox/tmp`에 임시 파일 작성
2. fsync 또는 flush
3. outbox root의 `<message_id>.json`으로 atomic rename

publisher는 publish 성공 후 파일을 삭제한다. invalid JSON은 `outbox/quarantine/`으로 이동한다.

## 진행 순서

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

2026-05-20 기준:

- `factory-b` Tailnet IP: `100.98.121.77`
- `factory-c` Tailnet IP: `100.76.243.72`
- Hub ArgoCD cluster Secret: `cluster-factory-b`, `cluster-factory-c`
- egress Service: `factory-b-master-tailnet`, `factory-c-master-tailnet`
- Application: `aegis-spoke-factory-b`, `aegis-spoke-factory-c`
- GitOps chart `outbox.type: pvc|hostPath` 분기 지원, `factory-b/c` values `hostPath` 전환 완료 (aegis-pi-gitops commit `04f90b2`, remote push 완료)
- factory-b worker1 `/var/lib/aegis/outbox`: `drwxrwx--- 10001:10001` 생성 확인
- factory-c worker `/var/lib/aegis/outbox`: 생성 확인 (kubectl pod exit 0, uid 10001 write 성공)

### factory-c-worker K3s node-ip 수정 내역

factory-c는 VirtualBox NAT 구조로 master/worker 모두 `INTERNAL-IP=10.0.2.15`로 K3s에 등록되는 문제가 있었다.
worker의 host-only 인터페이스 `enp0s8` IP `192.168.56.20`은 netplan에 static으로 고정되어 있음을 확인하고 아래와 같이 수정했다.

```bash
# factory-c-worker에서 적용 (2026-05-20)
sudo mkdir -p /etc/rancher/k3s
echo "node-ip: 192.168.56.20" | sudo tee /etc/rancher/k3s/config.yaml
sudo systemctl restart k3s-agent
```

적용 후 `kubectl get nodes -o wide`에서 `factory-c-worker INTERNAL-IP: 192.168.56.20` 확인.

주의: `kubectl logs` / `kubectl exec`가 worker 대상일 때 502 Bad Gateway가 나는 케이스가 남아 있다.
pod 배포/스케줄링/outbox write에는 영향 없다. 근본 원인(kubelet 인증서 SAN 미포함 가능성)은 추후 확인한다.
