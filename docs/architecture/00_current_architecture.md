# 현재 구조 요약

상태: source of truth
기준일: 2026-05-28

## 목적

현재 실제로 구축된 `factory-a` Safe-Edge 로컬 구조를 설명한다.

## 현재 상태

- 현재 구현 범위는 운영형 `factory-a` Spoke와 테스트베드 `factory-b/c` Spoke다. `factory-b/c`는 Hub ArgoCD cluster/Application 등록, hostPath outbox 전환, local dummy generator, 공통 publisher, S3 raw 적재 검증까지 완료했다. Hub EKS/ArgoCD/Grafana/Admin UI HTTPS 기준선은 `scripts/build/build-hub.sh`와 `scripts/build/build-admin-ui-after-ns.sh`로 재생성 가능하다.
- AWS Hub는 M1 Issue 0~10에서 EKS/VPC/namespace/ArgoCD bootstrap, foundation S3/IoT Rule, IoT Thing/certificate/policy/K3s Secret, IRSA S3 권한, AWS Load Balancer Controller, Route53/ACM, Admin UI HTTPS Ingress를 검증했다. 과거 AMP/Prometheus Agent/Grafana AMP datasource 검증 이력은 보존하지만, 2026-05-27 비용 최적화 기준에서는 active 구성에서 제거한다. 현재 build 흐름은 Hub platform, Spoke cluster 등록, Spoke workload 배포를 분리한다.
- M1 Issue 4에서 foundation S3 data bucket `aegis-bucket-data`를 생성했고, M1 Issue 5에서 IoT Thing/certificate/policy 및 K3s Secret 등록, IoT Rule -> S3 raw 적재 검증을 완료했다.
- 후속 구현 책임 경계는 Terraform = 인프라, Ansible = bootstrap/설정/소프트웨어, GitHub Actions = CI, GitHub+ArgoCD = CD로 고정한다.
- `factory-b`, `factory-c`는 VM K3s/Tailnet/ArgoCD cluster/Application 등록, worker `hostPath` outbox, 로컬 dummy generator, IoT Secret, `edge-iot-publisher` 활성화와 S3 raw 적재 검증까지 완료했다.
- Lambda data processor는 DynamoDB LATEST/HISTORY와 S3 processed 적재, `pipeline_status`, 기본 Risk Score 계산까지 검증했다.
- Daily Factory Report는 로컬 검증, Bedrock Sonnet 실호출, AWS reporting stack 배포, `factory-b` Step Functions 수동 실행, S3 산출물 검증까지 완료했다. reporting stack은 검증 후 삭제했으며 S3 input/output object는 보존한다.
- Dashboard page와 Dashboard VPC는 별도 담당 범위다. 이 repo의 현재 책임은 Dashboard가 조회할 DynamoDB/S3 processed read model과 Risk output 계약을 유지하는 것이다.
- 이 문서는 현재 동작 중인 로컬 기준선과 rebuild 가능한 Hub 기준선을 함께 기록한다.

## 물리 / 클러스터 구조

```text
factory-a
├── master  10.10.10.10  K3s control plane
├── worker1 10.10.10.11  failover standby
└── worker2 10.10.10.12  sensor / AI / audio preferred
```

Kubernetes:

```text
K3s v1.34.6+k3s1
```

## Namespace 구조

```text
argocd
longhorn-system
monitoring
ai-apps
```

역할:

| Namespace | 역할 |
| --- | --- |
| `argocd` | GitOps 배포 제어 |
| `longhorn-system` | PVC 및 replica storage |
| `monitoring` | InfluxDB, Prometheus, Grafana |
| `ai-apps` | BME280, integrated AI, audio, image prepull |

## 관리 UI

| UI | 주소 |
| --- | --- |
| ArgoCD | `http://10.10.10.200` |
| Longhorn | `http://10.10.10.201` |
| Grafana | `http://10.10.10.202` |

## 배포 구조

현재 배포 흐름:

```text
GitHub safe-edge-config-main
    -> ArgoCD UI refresh / sync
    -> safe-edge-monitoring
    -> safe-edge-ai-apps
    -> factory-a K3s
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

로컬 Safe-Edge 기준선은 `safe-edge-config-main`과 로컬 ArgoCD Application을 사용한다. Hub data-plane 배포 기준선은 별도 `aegis-pi-gitops` 저장소와 Hub ArgoCD ApplicationSet을 사용한다.

## 현재 Hub 상태

M1 Hub 기준선은 Terraform과 Ansible로 생성/검증했고, 필요할 때 `scripts/build/build-hub.sh`로 재생성한다. Hub build는 Hub 내부 platform까지만 수행하고, Spoke cluster 등록과 Spoke workload ApplicationSet은 IoT/Spoke 등록 단계에서 적용한다.

```text
AWS actual state: Hub EKS is ephemeral/rebuildable; foundation S3/ECR/DynamoDB and IoT are separate durable baseline resources
EKS: AEGIS-EKS target
VPC CIDR: 10.0.0.0/16 target on rebuild
AZ: ap-south-1a, ap-south-1c
NAT Gateway: single Azone NAT target
Hub namespaces: recreated by Ansible bootstrap
Prometheus Agent: retired, legacy resources cleaned up during Hub platform build
Grafana: observability/grafana internal management UI, no AMP datasource
Admin UI: https://argocd.minsoo-tech.cloud and https://grafana.minsoo-tech.cloud through shared Public ALB after DNS/ACM readiness
```

Terraform root:

```text
infra/hub         VPC, subnet, single NAT Gateway, EKS cluster, node group, IRSA
infra/foundation  S3/ECR/DynamoDB, Admin UI Route53/ACM
infra/data-pipeline IoT Rule, Lambda data processor
```

Hub Kubernetes bootstrap:

```text
scripts/ansible  kubeconfig 갱신, namespace, LimitRange, ArgoCD Helm install, legacy Prometheus Agent cleanup, Grafana, AWS Load Balancer Controller, Admin UI Ingress, Tailscale, ArgoCD cluster Secret, Spoke ApplicationSet. 기본 Hub build는 ArgoCD/Grafana/LB Controller까지만 실행하고, Admin UI와 factory-a/b/c K3s 의존 단계는 별도 entrypoint 또는 playbook에서 실행한다.
```

## 데이터 구조

현재 데이터 흐름:

```text
BME280 / camera / mic / AI
    -> ai-apps Pods
    -> InfluxDB safe_edge_db
    -> Grafana dashboard
```

M4 Issues 2~5에서 `factory-a-log-adapter`와 `edge-iot-publisher`를 구현하고 S3 raw 적재까지 검증했다. 두 컴포넌트는 `aegis-pi-gitops`의 `charts/aegis-spoke`와 `envs/factory-a/values.yaml` 기준으로 Hub ArgoCD ApplicationSet 배포 대상이다.

실제 데이터 흐름 (검증 완료):

```text
InfluxDB safe_edge_db / Kubernetes API
  -> factory-a-log-adapter (ai-apps, worker2)
  -> /var/lib/aegis/outbox (Longhorn PVC 공유)
  -> edge-iot-publisher (ai-apps, worker2)
  -> AWS IoT Core MQTT
  -> IoT Rule
  -> S3 raw (aegis-bucket-data)
```

수집 주기: `factory_state` 3초, `infra_state` 20초

`factory-b/c` 현재 데이터 흐름:

```text
VM local dummy generator
  -> /var/lib/aegis/outbox (worker hostPath)
  -> edge-iot-publisher (ai-apps, worker)
  -> AWS IoT Core MQTT
  -> IoT Rule
  -> S3 raw (aegis-bucket-data)
```

`factory-b/c`에서는 dummy generator를 Kubernetes Deployment로 배포하지 않는다. 각 VM 담당자가 로컬 script 또는 systemd service로 실행하고, Hub ArgoCD는 publisher와 Kubernetes 리소스만 관리한다.

InfluxDB measurement:

```text
environment_data
ai_detection
acoustic_detection
```

주요 field:

```text
environment_data.temperature
environment_data.humidity
environment_data.pressure
ai_detection.fire_detected
ai_detection.fallen_detected
ai_detection.bending_detected
acoustic_detection.is_danger
```

## 저장소 구조

```text
InfluxDB PVC -> Longhorn
AI snapshot -> node-local hostPath
AI inference result -> InfluxDB PVC -> Longhorn
```

보존 정책:

```text
InfluxDB safe_edge_db: 1일 retention
AI snapshots: 24시간 초과 jpg/jpeg/png 삭제
AI snapshots: 매일 03:00 KST worker1/worker2 local directory 전체 purge
```

AI snapshot:

```text
mount path: /app/snapshots
hostPath: /var/lib/safe-edge/snapshots
cleanup: snapshot-cleanup sidecar
daily purge: safe-edge-snapshot-daily-purge-worker1 / worker2 CronJob
```

## 모니터링 구조

Grafana datasource:

```text
InfluxDB: 센서 / AI / 소리 데이터
Prometheus: 노드 상태
```

Dashboard:

```text
Factory-A sensor / AI dashboard
Node Exporter Full 1860
```

## Failover / Failback 구조

정책:

```text
worker2 preferred affinity
tolerationSeconds: 30
worker1 failover standby
master OS cron 기반 Kubernetes-only failback
```

대상 Pod:

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
```

Failback 원칙:

- worker2가 Ready일 때만 진행한다.
- worker2에 대상 Pod가 이미 Running이면 skip한다.
- worker1에 남은 대상 Pod만 순차 삭제한다.
- Kubernetes CronJob이 아니라 master OS cron에서 `kubectl`만 실행한다.

## Image Prepull 구조

`safe-edge-image-prepull` DaemonSet은 worker1/worker2에 큰 이미지를 미리 받아 둔다.

목적:

```text
failover 시 worker1에서 이미지 pull 지연 감소
새 이미지 태그 배포 전 worker1/worker2 이미지 준비
```

## 현재 검증 결과

LAN 제거:

```text
Failover 성공
Failback 성공
AI/audio/BME worker1 Running 성공
worker2 복구 후 worker2 failback 성공
Longhorn Multi-Attach 재발 없음
```

`k3s-agent` 중지:

```text
Failover 성공
Failback 성공
AI/audio/BME worker1 Running 성공
worker2 복구 후 worker2 failback 성공
Longhorn Multi-Attach 재발 없음
```

LAN 제거 InfluxDB 공백:

```text
1초 bucket:
  ai_detection:        87초
  acoustic_detection:  90초
  environment_data:    83초

10초 bucket 운영 기준:
  ai_detection:        80초
  acoustic_detection:  80초
  environment_data:    70초
```

## 현재 구조 밖의 항목

다음 항목은 현재 구조가 아니라 후속 목표 구조 또는 별도 담당 범위다.

```text
Dashboard VPC / Risk Twin UI
runtime-config 기반 Risk weight/threshold 적용
Risk Twin read model 고도화
```

2026-05-28 기준 아래 항목은 구조에 포함됐다.

```text
IoT Core         Thing/certificate/policy/Rule (검증 완료)
S3               aegis-bucket-data raw 적재 (검증 완료)
Lambda           DataProcessor DynamoDB/S3 processed 적재와 기본 Risk 계산 (검증 완료)
Daily Report     reporting stack 수동 검증 완료, 현재 stack은 삭제, S3 산출물 보존
ECR              aegis/factory-a-log-adapter, aegis/edge-iot-publisher (sha-f71a104)
GitHub Actions   ARM64 matrix 빌드 (검증 완료)
Tailscale        Hub -> factory-a K3s API egress 및 ArgoCD cluster Secret 자동화
ApplicationSet   aegis-pi-gitops 기반 factory-a data-plane 배포
factory-a-log-adapter  ECR 이미지 존재, GitOps 배포 대상
edge-iot-publisher     ECR 이미지 존재, GitOps 배포 대상
```

후속 구조는 `docs/architecture/01_target_architecture.md`에서 관리한다.
