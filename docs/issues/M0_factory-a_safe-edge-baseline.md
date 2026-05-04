# M0. `factory-a` Safe-Edge 기준선 구축

상태: completed with deferred items
기준일: 2026-04-28

> **마일스톤 목표**: Aegis-Pi 전체 구현의 출발점인 `factory-a` Raspberry Pi 3-node K3s Safe-Edge 기준선을 구축하고 검증한다.
> 현재 M0의 핵심 기준선은 구축 및 장애 테스트까지 완료됐다. AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선은 M1에서 재생성/검증 후 2026-05-04 전체 destroy로 삭제했으며, `factory-b`, `factory-c` 확장은 후속 단계다.

## 수정 이력

| 날짜 | 수정 버전 | 수정 내용 |
| --- | --- | --- |
| 2026-05-04 | rev-20260504-01 | Hub EKS/VPC/namespace/ArgoCD bootstrap 검증 및 destroy 완료 상태를 M0 보류/후속 범위와 분리해 반영 |
| 2026-05-04 | rev-20260504-02 | Hub EKS/ArgoCD active 검증 상태와 M1 후속 범위를 당시 기준으로 반영 |
| 2026-05-04 | rev-20260504-03 | 전체 destroy 완료 후 Hub/Foundation/IoT 삭제 상태를 현재 기준으로 반영 |

## 현재 결과 요약

```text
Cluster: Raspberry Pi 3-node K3s
K3s: v1.34.6+k3s1
master: 10.10.10.10
worker1: 10.10.10.11
worker2: 10.10.10.12

ArgoCD UI: 10.10.10.200
Longhorn UI: 10.10.10.201
Grafana UI: 10.10.10.202

GitOps repo: https://github.com/aegis-pi/safe-edge-config-main.git
ArgoCD apps:
- safe-edge-monitoring
- safe-edge-ai-apps
```

## 완료 항목

### Issue 1 - [Safe-Edge/OS] Raspberry Pi 기본 세팅

상태: 완료

완료 내용:
- master, worker1, worker2 노드 준비
- SSH 접근 및 Kubernetes 운영 가능 상태 확인
- worker2 기준 센서/카메라/마이크 워크로드 배치 가능 상태 확인

완료 기준:
- 3개 노드가 K3s cluster에 참여한다.
- `kubectl get nodes -o wide`에서 모두 `Ready` 상태다.

### Issue 2 - [Safe-Edge/네트워크] 내부망 기준선 구성

상태: 완료

완료 내용:
- 노드 IP 고정
  - `master`: `10.10.10.10`
  - `worker1`: `10.10.10.11`
  - `worker2`: `10.10.10.12`
- 관리 UI IP 확정
  - ArgoCD: `10.10.10.200`
  - Longhorn: `10.10.10.201`
  - Grafana: `10.10.10.202`

완료 기준:
- 내부망에서 Kubernetes API와 주요 UI에 접근 가능하다.

### Issue 3 - [Safe-Edge/K3s] 3-Node 클러스터 구성

상태: 완료

완료 내용:
- master control plane 구성
- worker1, worker2 조인
- worker2를 센서/AI/Audio 우선 노드로 사용
- worker1을 failover standby로 사용

확인:

```bash
kubectl get nodes -o wide
```

### Issue 4 - [Safe-Edge/MetalLB] 내부 서비스 노출

상태: 완료

완료 내용:
- 내부망에서 ArgoCD, Longhorn, Grafana 접근 가능
- 서비스 IP를 문서화된 주소로 고정

완료 기준:
- `10.10.10.200`, `10.10.10.201`, `10.10.10.202` 접근 가능

### Issue 5 - [Safe-Edge/Longhorn] 저장소 구성

상태: 완료

완료 내용:
- Longhorn 설치
- InfluxDB PVC 구성
- Grafana PVC 구성
- AI 추론 결과를 InfluxDB PVC를 통해 Longhorn에 저장
- AI snapshot 저장소는 Longhorn PVC가 아니라 node-local hostPath로 변경
- worker2 전원 제거 테스트에서 Longhorn volume degraded 후 healthy 복귀 확인

변경 기록:

```text
docs/changes/0001-ai-snapshot-pvc-to-hostpath.md
```

확인:

```bash
kubectl -n longhorn-system get volumes.longhorn.io -o wide
kubectl -n monitoring get pvc
```

완료 기준:
- Longhorn volume이 `attached / healthy` 상태다.
- 장애 복구 후 healthy로 복귀한다.

### Issue 6 - [Safe-Edge/NFS] Host PC Cold Storage

상태: 보류

현재 판단:
- 클라우드 마이그레이션 전 로컬 데이터 누적을 줄이기 위해 우선 InfluxDB retention policy를 1일로 설정했다.
- NFS Cold Storage / Hot-Cold tiering은 현재 M0 핵심 완료 조건에서 제외하고 후속 검토로 둔다.

대체 적용:
- InfluxDB `safe_edge_db` retention: `1d`
- AI snapshot retention: `24h`

변경 기록:

```text
docs/changes/0003-nfs-cold-storage-deferred.md
```

### Issue 7 - [배포/ArgoCD] GitHub + ArgoCD GitOps

상태: 완료

변경된 기준:
- 기존 로컬 저장소 기준이 아니라 GitHub repo를 사용한다.
- ArgoCD 설치는 Helm으로 진행했다.
- GitHub repo 등록 및 sync는 ArgoCD UI에서 진행한다.

변경 기록:

```text
docs/changes/0004-safe-edge-config-github-gitops.md
```

GitOps repo:

```text
https://github.com/aegis-pi/safe-edge-config-main.git
```

Application:

```text
safe-edge-monitoring
safe-edge-ai-apps
```

확인:

```bash
kubectl -n argocd get application -o wide
```

완료 기준:
- Application이 `Synced / Healthy` 상태다.
- GitHub push 후 ArgoCD sync로 K3s 리소스가 반영된다.

### Issue 8 - [관제/Grafana] Prometheus + InfluxDB + Grafana

상태: 완료

완료 내용:
- InfluxDB datasource 구성
- Prometheus datasource 구성
- Grafana UI: `10.10.10.202`
- Node Exporter Full dashboard `1860` 사용
- 센서/AI 결과 dashboard 구성

InfluxDB 측정값:

```text
environment_data.temperature
environment_data.humidity
environment_data.pressure
ai_detection.fire_detected
ai_detection.fallen_detected
ai_detection.bending_detected
acoustic_detection.is_danger
```

완료 기준:
- Grafana에서 센서 time series와 AI 상태가 보인다.
- Prometheus 1860 dashboard에서 노드 상태가 보인다.

### Issue 9 - [데이터/BME280] 센서 입력 계층

상태: 완료

완료 내용:
- BME280 데이터가 InfluxDB에 적재된다.
- Grafana에서 온도/습도/기압을 확인한다.
- InfluxDB retention policy 1일을 적용했다.

확인:

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM environment_data ORDER BY time DESC LIMIT 3'
```

### Issue 10 - [Safe-Edge/AI] 통합 AI + Audio 파드 배포

상태: 완료

완료 내용:
- `safe-edge-integrated-ai` worker2 우선 배치
- `safe-edge-audio` worker2 우선 배치
- AI 결과 InfluxDB 저장
- AI event image `/app/snapshots` 저장
- `/app/snapshots`는 node-local hostPath `/var/lib/safe-edge/snapshots`에 연결
- `snapshot-cleanup` sidecar로 24시간 초과 이미지 삭제

변경 기록:

```text
docs/changes/0001-ai-snapshot-pvc-to-hostpath.md
```

확인:

```bash
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c ai-processor -- mount | grep snapshots
```

### Issue 11 - [Safe-Edge/Failover] Failover / Failback 정책

상태: 완료

완료 내용:
- 대상 Pod에 `tolerationSeconds: 30` 적용
- worker2 preferred affinity 적용
- worker2 장애 시 worker1 failover 확인
- master OS cron 기반 Kubernetes-only failback 적용
- worker2에 대상 Pod가 이미 있으면 skip하도록 설계

변경 기록:

```text
docs/changes/0002-failback-cron-instead-of-k8s-cronjob.md
```

대상 Pod:

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
```

전원 제거 테스트 결과:

```text
전원 제거 첫 관찰 -> worker2 NotReady: 약 42초
worker2 NotReady -> worker1 전체 Running: 약 32초
전원 제거 첫 관찰 -> worker1 전체 Running: 약 74초
전원 재연결 첫 관찰 -> worker2 전체 Running: 약 2분 11초
```

### Issue 12 - [자동화] Ansible / Hot-Cold Tiering

상태: 부분 완료

현재 판단:
- 기존 Kubernetes CronJob 방식 failback은 하드웨어 의존 워크로드에서 불안정했다.
- 현재는 master OS cron 기반 Kubernetes-only failback을 사용한다.
- `start_test` 기반 반복 점검은 Ansible playbook으로 구현했다.
- Ansible 장애 관측 자동화와 NFS Hot-Cold tiering은 후속 자동화 과제로 분리한다.

구현:

```text
scripts/ansible/playbooks/02_start_test.yml
scripts/ansible/inventory/group_vars/factory_a.yml
docs/ops/11_ansible_test_automation.md
```

운영 기준:

```bash
cd scripts/ansible
ansible-playbook playbooks/02_start_test.yml
```

비밀번호는 playbook prompt로만 입력하고 파일에 저장하지 않는다. 실행 산출물은 `scripts/ansible/evidence/`에 생성되지만 Git push 대상에서는 제외한다.

변경 기록:

```text
docs/changes/0002-failback-cron-instead-of-k8s-cronjob.md
docs/changes/0003-nfs-cold-storage-deferred.md
```

### Issue 13 - [검증/통합] Safe-Edge 기준선 통합 검증

상태: 완료

완료된 검증:
- 시작 상태 점검
- ArgoCD sync 확인
- InfluxDB write 확인
- Grafana dashboard 확인
- Longhorn healthy 확인
- LAN 제거 failover/failback 테스트
- 전원 제거 failover/failback 테스트
- 10초/1초 bucket 데이터 공백 분석
- image prepull 효과 확인

전원 제거 테스트 1초 bucket 연속 공백:

```text
failover environment_data: 최대 65초
failover ai_detection: 최대 72초
failover acoustic_detection: 최대 75초
failback environment_data: 최대 2초
failback ai_detection: 최대 2초
failback acoustic_detection: 최대 2초
```

## M0 완료 판단

M0은 `factory-a` 로컬 Safe-Edge 기준선 구축 관점에서 완료로 판단한다.

보류 항목:

```text
NFS Cold Storage
Ansible 기반 장애 관측 자동화
Ansible 기반 Hot-Cold tiering
AWS Hub 연동
factory-b / factory-c 확장
IoT Core / S3 / ECR / GitHub Actions
```

위 항목은 M1 이후 또는 별도 후속 작업으로 다룬다.
