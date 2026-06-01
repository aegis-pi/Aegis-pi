# Quick Start

상태: source of truth
기준일: 2026-06-01

## 목적

현재 `factory-a` Safe-Edge 기준선의 상태를 빠르게 확인하고, 다음 운영 문서로 이동할 수 있게 안내한다.

## 현재 상태

- `factory-a` 로컬 Raspberry Pi 3-node K3s 기준선 구축이 완료됐다.
- ArgoCD, Longhorn, Grafana, InfluxDB, AI/Audio/BME280 워크로드가 동작한다.
- AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선은 `scripts/build/build-hub.sh`로 재생성 가능하다. 현재 build 흐름은 Hub와 factory cluster 등록을 먼저 끝내고, IoT Secret 준비 후 Spoke ApplicationSet을 배포하도록 분리되어 있다.
- Foundation S3 bucket `aegis-bucket-data`, ECR, DynamoDB `AEGIS-DynamoDB-FactoryStatus`는 Hub/data-pipeline destroy와 분리되는 foundation 영구 리소스다. AMP는 비용 최적화 기준에서 active 구성에서 제거한다.
- IoT Rule(factory-a/b/c), Lambda(DataProcessor), DataProcessorRefresh1m, GraphAggregator5m, CloudInfraFastCollector1m, CloudInfraSlowCollector5m은 `infra/data-pipeline` 레이어로 분리되어 `scripts/build/build-data-pipe.sh` / `scripts/destroy/destroy-data-pipe.sh`로 개별 관리된다. SlowCollector는 EKS access entry를 생성하므로 현재 build 순서는 foundation -> hub -> data-pipeline이다.
- IoT Core `factory-a` Thing/certificate/policy와 K3s Secret은 `scripts/build/build-iot-factory-a.sh`에서 생성/갱신한다. 같은 단계에서 ArgoCD ApplicationSet을 적용해 `factory-a` data-plane workload 배포를 시작한다.
- Hub만 삭제/재생성한 경우에는 IoT Core Thing/certificate와 Spoke K3s Secret을 다시 만들지 않는다. `scripts/build/build-hub.sh` 이후 UI 연결과 `factory-a/b/c` ArgoCD cluster 등록을 각각 별도 실행 파일로 복구한다.
- `risk/risk-normalizer` IRSA S3 권한은 M1 검증 이력이며 최신 데이터 처리 구현 대상은 Lambda data processor와 DynamoDB/S3 processed다.
- Hub Prometheus Agent는 rebuild 시 재설치하지 않는다. 기존 클러스터에 남은 `observability/prometheus-agent`는 cleanup playbook으로 제거한다.
- 내부 Grafana는 rebuild 시 `observability` 네임스페이스에서 재설치되며, AMP datasource 없이 Grafana health를 검증한다.
- AWS Load Balancer Controller와 Admin UI HTTPS Ingress는 `scripts/build/build-admin-ui-after-ns.sh`로 ACM 발급 확인 후 활성화한다.
- `factory-b`, `factory-c`는 VM 테스트베드 Spoke로 Hub ArgoCD cluster 등록, ApplicationSet Application 생성, GitOps `hostPath` outbox 전환, local dummy generator systemd 실행, K3s `edge-iot-publisher` 활성화, IoT Core -> S3 raw prefix 분리 적재까지 완료했다.
- Lambda data processor(`apps/data-processor/`) 구현 완료. DynamoDB는 `LATEST`와 `HISTORY#STATE#{updated_at}` snapshot 이력 구조를 사용하며, history에는 `LATEST`와 같은 구조에 `ttl`만 추가한다. DataProcessorRefresh1m은 새 메시지가 없는 factory도 `pipeline_status`와 `risk`를 현재 시각 기준으로 재계산한다. GraphAggregator5m은 `HISTORY#STATE`를 읽어 `GRAPH#5M`과 S3 `processed_agg`를 만들며, `GRAPH#5M.infra.nodes[]`에 node별 CPU/memory/disk 5분 집계를 저장한다. Terraform 인프라(`infra/data-pipeline/`) 구현 완료.
- Cloud infra collectors 구현/배포 완료. FastCollector는 ECS/ALB/Lambda/DynamoDB/Scheduler/factory freshness를 1분마다 `CLOUD#infra/LATEST.fast`에 저장하고, SlowCollector는 EKS/Kubernetes/ArgoCD/S3 freshness를 5분마다 `CLOUD#infra/LATEST.slow`에 저장한다. CloudWatch Container Insights는 기본 OFF이고 `metrics-server`는 기본 ON이다.
- IoT -> Lambda -> DynamoDB/S3 processed end-to-end 검증과 pipeline_status 동작 확인은 `factory-a/b/c` 기준 완료됐다. 2026-05-29 기준 `factory-a`는 2026-05-28T07:54Z 이후 입력 중단으로 `pipeline_status=critical`, `risk.score=0`, `risk.level=danger`로 refresh 확인됐고, `factory-b/c`는 정상 입력 기준 `risk.score=100`이다.
- Lambda data processor의 `risk-v0.2.0` Risk Score 계산은 구현/검증 완료됐다. 다음 Risk 작업은 `configs/runtime/runtime-config.yaml`을 실제 Lambda Risk 계산에 연결하고, Risk Twin/Dashboard가 읽을 read model 필드를 고정하는 것이다.
- Dashboard page와 Dashboard VPC는 별도 담당 범위다. 이 repo에서는 DynamoDB/S3 processed 데이터 계약과 report 산출물 계약을 유지한다.
- Daily Factory Report는 로컬 테스트, Bedrock Sonnet 실호출, `infra/reporting` AWS 배포, `factory-b` Step Functions 수동 실행, S3 산출물 검증까지 완료했다. 비용 방지를 위해 reporting stack은 검증 후 삭제했으며 S3 input/output object는 보존한다.
- 후속 구현은 Terraform = 인프라, Ansible = bootstrap/설정/소프트웨어, GitHub Actions = CI, GitHub+ArgoCD = CD 기준을 따른다.

## 현재 운영 주소

| 항목 | 값 |
| --- | --- |
| master | `10.10.10.10` |
| worker1 | `10.10.10.11` |
| worker2 | `10.10.10.12` |
| ArgoCD UI | `http://10.10.10.200` |
| Longhorn UI | `http://10.10.10.201` |
| Grafana UI | `http://10.10.10.202` |
| GitOps repo | `https://github.com/aegis-pi/safe-edge-config-main.git` |

## 우선 읽을 문서

1. `docs/ops/05_factory_a_status.md`
2. `docs/ops/06_argocd_gitops.md`
3. `docs/ops/07_grafana_dashboard.md`
4. `docs/ops/08_data_retention.md`
5. `docs/ops/09_failover_failback_test_results.md`
6. `docs/ops/04_troubleshooting.md`
7. `docs/changes/README.md`
8. `docs/ops/14_hub_run_commands.md`
9. `docs/ops/22_factory_bc_testbed_data_plane.md`
10. `docs/ops/24_daily_factory_report.md`
11. `docs/ops/25_daily_factory_report_cost.md`
12. `docs/ops/26_dynamodb_key_model.md`

## 빠른 상태 확인

master에서 확인한다.

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

정상 기준:

```text
master, worker1, worker2: Ready
safe-edge-monitoring: Synced / Healthy
safe-edge-ai-apps: Synced / Healthy
monitoring/influxdb, prometheus, grafana: Running
ai-apps/bme280-sensor, safe-edge-integrated-ai, safe-edge-audio: worker2 Running
safe-edge-image-prepull: worker1, worker2 Running
Longhorn volumes: attached / healthy
```

## 현재 완료된 범위

```text
K3s 3-node 구성
Longhorn PVC 저장소
MetalLB 내부 IP 노출
ArgoCD Helm 설치
GitHub GitOps repo 기반 배포
monitoring / ai-apps Application 분리
InfluxDB safe_edge_db 1일 retention
Grafana InfluxDB dashboard 구성
Prometheus Node Exporter Full 1860 dashboard 사용
worker2 preferred affinity + 30초 tolerationSeconds
master OS cron 기반 Kubernetes-only failback
safe-edge-image-prepull DaemonSet
AI snapshot node-local hostPath + 24시간 cleanup + 매일 03:00 KST purge
AI inference result InfluxDB PVC 기반 Longhorn 저장
LAN 제거 장애 테스트
k3s-agent 중지 장애 테스트
Hub EKS ArgoCD + Tailscale factory-a cluster 등록 자동화
aegis-pi-gitops ApplicationSet 기반 factory-a data-plane 배포
factory-b/factory-c Hub ArgoCD cluster 등록 및 Application 생성
factory-b/factory-c local dummy generator 및 K3s edge-iot-publisher 활성화
factory-a/factory-b/factory-c IoT Core -> S3 raw 적재 검증
factory-a/factory-b/factory-c IoT Core -> Lambda -> DynamoDB/S3 processed 적재 검증
GraphAggregator5m DynamoDB GRAPH#5M / S3 processed_agg 집계 검증
GraphAggregator5m `GRAPH#5M.infra.nodes[]` node별 5분 집계 검증
DataProcessorRefresh1m pipeline_status/risk freshness refresh 검증
Lambda data processor risk-v0.2.0 Risk Score 계산 검증
CloudInfraFastCollector1m / CloudInfraSlowCollector5m DynamoDB CLOUD#infra / S3 processed/cloud_infra 검증
Daily Factory Report local/AWS manual execution 검증
```

## 다음 단계

1. Hub를 내리는 경우 `scripts/destroy/stop-dummy-generators.sh`로 VM 데이터 생성을 먼저 멈춘 뒤 `scripts/destroy/destroy-hub.sh <MFA_OTP>` 또는 `scripts/destroy/destroy-all.sh <MFA_OTP>`를 실행한다.
2. Hub만 다시 올리는 경우 `scripts/build/build-hub.sh <MFA_OTP>`를 먼저 실행하고, 필요에 따라 `build-admin-ui-after-ns.sh`, `register-spoke-factory-a.sh`, `register-spoke-factory-b.sh`, `register-spoke-factory-c.sh`, `scripts/ops/manage-dummy-generators.sh start factory-b`, `scripts/ops/manage-dummy-generators.sh start factory-c`를 순서대로 실행한다. ALB/Admin UI HTTPS를 쓰면 `connect-hub-tailscale-ui.sh`는 선택 사항이다.
3. 계획과 실제 구현이 달라진 항목은 `docs/changes/`에 Change Record로 남긴다.
4. `README.md`, `docs/README.md`, architecture 문서를 현재 `factory-a/b/c` 기준으로 유지한다.
5. Grafana/dashboard 스펙을 실제 InfluxDB + Prometheus 기준으로 유지한다.
6. M1 Issue 9 AWS Load Balancer Controller, M1 Issue 10 ArgoCD/Grafana HTTPS Admin Ingress, M1 Issue 12 `runtime-config.yaml` 구조 초안, M3 Issue 1~5/7/8 배포 기준선, M4 Issue 1~8 data-pipeline 검증, M5 factory-b/c 테스트베드 수집 검증, `risk-v0.2.0` Risk Score 계산과 DataProcessor freshness refresh, Bedrock 기반 Daily Factory Report MVP 검증은 완료됐다.
7. 다음 repo 작업은 `runtime-config.yaml`을 Lambda Risk 계산에 연결하고, Risk Twin read model을 DynamoDB/S3 processed 계약에 맞춰 고정하는 것이다. Daily Report는 S3 read 병렬화, `state_snapshot` 입력 축소, `generation-metadata.json` 비용 관측값 보강이 후속 고도화다.

## 개발 환경 빌드/종료 퀵스타트

### 시작

| 순서 | 명령 | 생성/복구되는 리소스 |
| --- | --- | --- |
| 1 | `scripts/build/build-foundation.sh [MFA_OTP]` | S3 `aegis-bucket-data`, ECR x3, DynamoDB `AEGIS-DynamoDB-FactoryStatus`, GitHub Actions OIDC/IAM, Admin UI Route53 Hosted Zone/ACM certificate. AMP는 active 구성에서 제거됨 |
| 2 | `scripts/build/build-hub.sh [MFA_OTP]` | Hub VPC, Subnet x4, NAT Gateway x1, EKS Cluster/NodeGroup, EKS-bound IRSA, Hub platform(ArgoCD/Grafana/AWS LB Controller, Prometheus Agent cleanup). Admin UI DNS/ACM은 foundation output 참조 |
| 3 | `scripts/build/build-admin-ui-after-ns.sh [MFA_OTP]` | 선택: ArgoCD/Grafana HTTPS Ingress, ALB/TargetGroup/SecurityGroup, Route53 record |
| 4 | `scripts/build/connect-hub-tailscale-ui.sh [MFA_OTP]` | 선택: Tailnet 경유 ArgoCD/Grafana UI 접근 |
| 5 | `scripts/build/register-spoke-factory-a.sh [MFA_OTP]` | factory-a Tailscale egress, ArgoCD cluster Secret, `aegis-spoke-factory-a` Application |
| 6 | `scripts/build/register-spoke-factory-b.sh [MFA_OTP]` | factory-b Tailscale egress, ArgoCD cluster Secret, `aegis-spoke-factory-b` Application |
| 7 | `scripts/build/register-spoke-factory-c.sh [MFA_OTP]` | factory-c Tailscale egress, ArgoCD cluster Secret, `aegis-spoke-factory-c` Application |
| 8 | `scripts/ops/manage-dummy-generators.sh start factory-b` | factory-b worker SSH -> `aegis-factory-b-dummy-generator.service` 시작 |
| 9 | `scripts/ops/manage-dummy-generators.sh start factory-c` | factory-c worker SSH -> `aegis-factory-c-dummy-generator.service` 시작 |
| 10 | `scripts/build/build-data-pipe.sh [MFA_OTP]` | IoT Topic Rule x3, Lambda `AEGIS-Lambda-DataProcessor`, Lambda `AEGIS-Lambda-GraphAggregator5m`, Lambda `AEGIS-Lambda-CloudInfraFastCollector`, Lambda `AEGIS-Lambda-CloudInfraSlowCollector`, EventBridge Scheduler x4, CloudWatch Log Groups, IAM role/policy, SlowCollector EKS AdminView read access entry, S3 `processed/`/`processed_agg/`/`processed/cloud_infra/` 적재 경로 |
| 11 | `scripts/build/build-reporting.sh [MFA_OTP]` | 선택/on-demand: reporting Lambda x4, Step Functions, EventBridge Scheduler, CloudWatch Log Groups, IAM role/policy. 입력은 S3 `processed/`, 출력은 S3 `reports/daily/` |

### 종료

| 순서 | 명령 | 삭제/정지되는 리소스 |
| --- | --- | --- |
| 1 | `scripts/destroy/stop-dummy-generators.sh` | factory-b/c worker 더미 generator systemd service 정지. 데이터 수집 유지 모드에서는 실행하지 않음 |
| 2 | `scripts/destroy/destroy-reporting.sh [MFA_OTP]` | EventBridge Scheduler, Step Functions, reporting Lambda x4, CloudWatch Log Groups, IAM role/policy. S3 `processed/`와 `reports/daily/` 객체는 보존 |
| 3 | `scripts/destroy/destroy-data-pipe.sh [MFA_OTP]` | IoT Rules x3, Lambda DataProcessor, Lambda GraphAggregator5m, CloudInfraFastCollector, CloudInfraSlowCollector, EventBridge Scheduler x4, CloudWatch Log Groups, IAM role/policy, SlowCollector EKS access entry. DynamoDB/S3 데이터는 보존 |
| 4 | `scripts/destroy/destroy-hub.sh [MFA_OTP]` | Hub EKS/NodeGroup, VPC/Subnet, NAT Gateway/EIP, EKS-bound IRSA, Hub platform 리소스. Route53 Hosted Zone/ACM은 foundation에 보존 |
| - | `DESTROY_FOUNDATION=true scripts/destroy/destroy-foundation.sh [MFA_OTP]` | 선택/완전 삭제: S3, ECR x3, DynamoDB, GitHub Actions OIDC/IAM, Admin UI Route53/ACM. S3 데이터와 ECR 이미지는 복구 불가 |

### 데이터 수집 유지 모드

퇴근 후에도 데이터를 계속 쌓아야 하면 data-pipeline과 Spoke publisher는 유지하고 Hub만 내린다.

| 시점 | 명령 | 목적 |
| --- | --- | --- |
| 퇴근 | `scripts/destroy/destroy-hub.sh [MFA_OTP]` | Hub EKS/VPC/NAT 고정비만 제거 |
| 출근 | `scripts/build/build-hub.sh [MFA_OTP]` | Hub 제어 plane 복구 |
| 출근 | `HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-a.sh [MFA_OTP]` | 기존 factory-a pod를 건드리지 않고 Hub ArgoCD 제어 경로 재연결 |
| 출근 | `HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-b.sh [MFA_OTP]` | 기존 factory-b publisher 유지하며 재연결 |
| 출근 | `HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-c.sh [MFA_OTP]` | 기존 factory-c publisher 유지하며 재연결 |
| 확인 | `scripts/ops/check-spoke-publisher-safety.sh` | factory별 `edge-iot-publisher` 중복 pod와 rollout strategy 확인 |

### 보고서 파이프라인 메모

| 항목 | 기준 |
| --- | --- |
| 리전 | `ap-south-1` |
| 기본 Bedrock 모델 | `anthropic.claude-3-sonnet-20240229-v1:0` |
| 입력 | S3 `processed/{factory_id}/{factory_state,risk_score,infra_state,state_snapshot}/...` |
| primary source | `factory_state`, `risk_score`, `infra_state` |
| auxiliary source | `state_snapshot` |
| 출력 prefix | `s3://aegis-bucket-data/reports/daily/yyyy=YYYY/mm=MM/dd=DD/{factory_id}/` |
| 필수 산출물 | `intermediate/hourly/hh=00..23.json`, `factory-daily-summary.json`, `report-context.json`, `report.md`, `generation-metadata.json` |
| 운영 기준 | 수동 검증 후 stack은 `destroy-reporting.sh`로 삭제 가능. S3 input/output 객체는 보존 |
