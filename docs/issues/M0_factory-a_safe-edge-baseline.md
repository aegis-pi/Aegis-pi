# M0. `factory-a` Safe-Edge 기준선 구축

상태: completed with deferred items
기준일: 2026-05-08

> **마일스톤 목표**: Aegis-Pi 전체 구현의 출발점인 `factory-a` Raspberry Pi 3-node K3s Safe-Edge 기준선을 구축하고 검증한다.
> 현재 M0의 핵심 기준선은 구축 및 장애 테스트까지 완료됐다. AWS Hub EKS/VPC/namespace/ArgoCD bootstrap, AWS Load Balancer Controller, Admin UI HTTPS Ingress, foundation S3/AMP/IoT Rule, `factory-a` IoT/K3s Secret은 M1에서 재생성/검증했고 2026-05-08 비용 정리를 위해 destroy 완료 상태이며, `factory-b`, `factory-c` 확장은 후속 단계다.

## 수정 이력

| 날짜 | 수정 버전 | 수정 내용 |
| --- | --- | --- |
| 2026-05-04 | rev-20260504-01 | Hub EKS/VPC/namespace/ArgoCD bootstrap 검증 및 destroy 완료 상태를 M0 보류/후속 범위와 분리해 반영 |
| 2026-05-04 | rev-20260504-02 | Hub EKS/ArgoCD active 검증 상태와 M1 후속 범위를 당시 기준으로 반영 |
| 2026-05-04 | rev-20260504-03 | 전체 destroy 완료 후 Hub/Foundation/IoT 삭제 상태를 현재 기준으로 반영 |
| 2026-05-06 | rev-20260506-01 | Hub/Foundation/IoT active 및 AMP/IRSA 검증 상태를 현재 기준으로 반영 |
| 2026-05-06 | rev-20260506-02 | build-all 실행 후 Hub/Foundation/IoT active 검증 상태를 반영 |
| 2026-05-06 | rev-20260506-03 | 각 완료/보류 issue에 GitHub comment용 진행 요약을 추가 |

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: `factory-a`의 master/worker1/worker2 Raspberry Pi 노드를 운영 가능한 K3s 기반으로 준비했고, SSH와 Kubernetes 운영 접근을 확인했다.
- 변경/확인: 노드 역할과 주소 기준은 `docs/ops/00_quick_start.md`, `docs/ops/05_factory_a_status.md`, `docs/architecture/00_current_architecture.md`에 반영했다.
- 검증: `kubectl get nodes -o wide` 기준 3개 노드 `Ready` 상태를 확인했다.
- 후속: 없음

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: `factory-a` 내부망 IP 기준을 고정하고 ArgoCD, Longhorn, Grafana 관리 UI 주소를 확정했다.
- 변경/확인: 노드 IP와 UI IP 기준을 `README.md`, `docs/ops/00_quick_start.md`, `docs/architecture/00_current_architecture.md`에 정리했다.
- 검증: Kubernetes API 접근과 `10.10.10.200`, `10.10.10.201`, `10.10.10.202` UI 접근 기준을 확인했다.
- 후속: 없음

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: master control plane과 worker1/worker2 조인을 완료하고, worker2는 센서/AI/Audio 우선 노드, worker1은 failover standby로 정했다.
- 변경/확인: 현재 클러스터 구조를 `docs/architecture/00_current_architecture.md`와 `docs/ops/05_factory_a_status.md`에 반영했다.
- 검증: `kubectl get nodes -o wide`로 3-node K3s 구성을 확인했다.
- 후속: 없음

### Issue 4 - [Safe-Edge/MetalLB] 내부 서비스 노출

상태: 완료

완료 내용:
- 내부망에서 ArgoCD, Longhorn, Grafana 접근 가능
- 서비스 IP를 문서화된 주소로 고정

완료 기준:
- `10.10.10.200`, `10.10.10.201`, `10.10.10.202` 접근 가능

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: MetalLB 기반 LoadBalancer IP를 사용해 ArgoCD, Longhorn, Grafana를 내부망 고정 주소로 노출했다.
- 변경/확인: 서비스 주소와 운영 접근 기준을 `docs/ops/00_quick_start.md`, `docs/ops/06_argocd_gitops.md`, `docs/ops/07_grafana_dashboard.md`에 반영했다.
- 검증: 각 관리 UI의 고정 IP 접근 가능 상태를 확인했다.
- 후속: 없음

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: Longhorn을 PVC 저장소 기준으로 구성하고, InfluxDB/Grafana 데이터는 Longhorn PVC에 두되 AI snapshot은 node-local hostPath로 분리했다.
- 변경/확인: `safe-edge/safe-edge-config-main/monitoring/grafana.yaml`, InfluxDB PVC manifest, `docs/changes/0001-ai-snapshot-pvc-to-hostpath.md`를 확인했다.
- 검증: Longhorn volume `attached / healthy`, 장애 후 degraded에서 healthy 복귀를 확인했다.
- 후속: 없음

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

### GitHub Issue Comment Draft

- 상태: 보류
- 진행 요약: NFS Cold Storage와 Hot-Cold tiering은 M0 핵심 완료 조건에서 제외하고, 우선 InfluxDB 1일 retention과 AI snapshot 24시간 보존 정책으로 로컬 누적 데이터를 제한했다.
- 변경/확인: 보류 판단은 `docs/changes/0003-nfs-cold-storage-deferred.md`와 `docs/ops/08_data_retention.md`에 정리했다.
- 검증: InfluxDB `safe_edge_db` retention 1일 기준과 snapshot cleanup/daily purge 기준을 확인했다.
- 후속: NFS 또는 cold storage가 필요해지는 시점에 별도 후속 issue로 재검토한다.

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: 로컬 manifest 기준에서 GitHub GitOps repo와 ArgoCD Application sync 기준으로 전환했다.
- 변경/확인: `safe-edge/safe-edge-config-main`의 `monitoring/`, `ai-apps/` 구성을 확인했고, 전환 기록은 `docs/changes/0004-safe-edge-config-github-gitops.md`에 남겼다.
- 검증: `safe-edge-monitoring`, `safe-edge-ai-apps` Application이 `Synced / Healthy` 상태로 동작하는 기준을 확인했다.
- 후속: Hub ApplicationSet 기반 멀티 Spoke 배포는 M3에서 진행한다.

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: InfluxDB와 Prometheus를 Grafana에 연결해 센서/AI 결과와 노드 상태를 함께 보는 관제 기준을 구성했다.
- 변경/확인: `safe-edge/safe-edge-config-main/monitoring/grafana.yaml`, Prometheus/InfluxDB manifest, `docs/ops/07_grafana_dashboard.md`를 확인했다.
- 검증: Grafana `10.10.10.202`에서 센서 time series, AI 상태, Node Exporter Full `1860` dashboard 기준을 확인했다.
- 후속: Hub/AMP 기반 중앙 관측은 M1 Issue 6~8에서 이어간다.

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: BME280 센서 데이터를 InfluxDB `environment_data` measurement에 적재하고 Grafana에서 온도/습도/기압을 확인하는 흐름을 구성했다.
- 변경/확인: `safe-edge/safe-edge-config-main/monitoring/bme280-sensor.yaml`과 Grafana/InfluxDB 운영 문서를 확인했다.
- 검증: InfluxDB query로 최신 `environment_data` 적재 상태를 확인하는 기준을 남겼다.
- 후속: 중앙 수집용 표준 스키마와 Edge data-plane 송신은 M4에서 진행한다.

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: 통합 AI와 Audio 파드를 worker2 우선 배치로 구성하고, AI 결과는 InfluxDB에 저장하며 event snapshot은 hostPath에 24시간 보존하도록 정리했다.
- 변경/확인: `safe-edge/safe-edge-config-main/ai-apps/values.yaml`, `ai-apps/templates/integrated-ai.yaml`, `ai-apps/templates/audio-deployment.yaml`을 확인했다.
- 검증: `kubectl -n ai-apps get pod -o wide`와 snapshot mount 확인 기준을 남겼다.
- 후속: 이미지 빌드/ECR/GitHub Actions 전환은 M3에서 진행한다.

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: worker2 장애 시 AI/Audio/BME 워크로드가 worker1로 넘어가고, worker2 복구 후 master OS cron 기반 failback으로 되돌아오는 정책을 검증했다.
- 변경/확인: `safe-edge/scripts/safe-edge-failback.sh`, `safe-edge/scripts/safe-edge-preflight-repair.sh`, `docs/changes/0002-failback-cron-instead-of-k8s-cronjob.md`를 확인했다.
- 검증: LAN 제거, `k3s-agent` 중지, 전원 제거 테스트에서 failover/failback 성공과 Longhorn Multi-Attach 재발 없음 기준을 확인했다.
- 후속: Hub에 장애 상태를 송신하는 Edge data-plane/pipeline status 검증은 M4/M7에서 진행한다.

### Issue 12 - [자동화] Ansible / Hot-Cold Tiering

상태: 부분 완료

현재 판단:
- 기존 Kubernetes CronJob 방식 failback은 하드웨어 의존 워크로드에서 불안정했다.
- 현재는 master OS cron 기반 Kubernetes-only failback을 사용한다.
- `start_test` 기반 반복 점검은 Ansible playbook으로 구현했다.
- Ansible 장애 관측 자동화와 NFS Hot-Cold tiering은 후속 자동화 과제로 분리한다.

구현:

```text
scripts/ansible/playbooks/start_test.yml
scripts/ansible/inventory/group_vars/factory_a.yml
docs/ops/11_ansible_test_automation.md
```

운영 기준:

```bash
cd scripts/ansible
ansible-playbook -i inventory/factory-a.ini playbooks/start_test.yml
```

비밀번호는 playbook prompt로만 입력하고 파일에 저장하지 않는다. 실행 산출물은 `scripts/ansible/evidence/`에 생성되지만 Git push 대상에서는 제외한다.

2026-05-08 기준 `start_test.yml`은 master Tailscale 상태를 검증하기 전에 master `wlan0`의 IPv4, default route, `controlplane.tailscale.com` DNS/HTTPS reachability를 먼저 확인한다. control host가 `10.10.10.0/24` 내부망에 붙어 있으면 기본 inventory의 `10.10.10.10`으로 실행하고, master Tailscale IP는 SSH 실행 경로로 사용하지 않는다.

변경 기록:

```text
docs/changes/0002-failback-cron-instead-of-k8s-cronjob.md
docs/changes/0003-nfs-cold-storage-deferred.md
```

### GitHub Issue Comment Draft

- 상태: 부분 완료
- 진행 요약: Safe-Edge 시작 점검은 Ansible playbook으로 자동화했고, failback은 Kubernetes CronJob 대신 master OS cron에서 `kubectl`만 사용하는 방식으로 확정했다.
- 변경/확인: 현재 코드 기준은 `scripts/ansible/playbooks/start_test.yml`, `scripts/ansible/inventory/group_vars/factory_a.yml`, `safe-edge/scripts/safe-edge-failback.sh`다.
- 검증: Ansible evidence 출력 경로와 preflight/failback 운영 기준을 확인했다.
- 후속: 장애 관측 자동화와 Hot-Cold tiering은 후속 자동화 issue로 분리한다.

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

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: `factory-a` Safe-Edge 기준선의 배포, 관측, 데이터 적재, 저장소 복구, failover/failback을 통합 검증했다.
- 변경/확인: 검증 결과는 `docs/ops/09_failover_failback_test_results.md`, `safe-edge/failback/`, `docs/ops/03_test_checklist.md` 기준으로 정리했다.
- 검증: LAN 제거/전원 제거/k3s-agent 중지 시나리오에서 워크로드 재스케줄, 데이터 공백, failback 복귀 시간을 확인했다.
- 후속: 멀티 공장 확장과 중앙 Hub 연동은 M1 이후 issue에서 진행한다.

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
