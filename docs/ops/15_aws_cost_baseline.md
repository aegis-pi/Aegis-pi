# AWS Cost Baseline

상태: source of truth
기준일: 2026-06-02
리전: `ap-south-1` / Asia Pacific (Mumbai)

## 목적

이 문서는 Aegis-Pi AWS Hub를 켜 두었을 때와 `destroy-all` 이후의 시간당 비용 기준을 기록한다.

새 AWS 리소스, 관리형 서비스, 상시 실행 컴포넌트, 저장소, 네트워크 경로가 추가되면 이 문서를 함께 갱신한다. 특히 `infra/hub`, `infra/foundation`, Dashboard VPC, ECR, Load Balancer, NAT Gateway, Public IPv4, EBS, S3 lifecycle, CloudWatch Logs, IoT Core 사용량 기준이 바뀌면 비용 영향을 다시 계산한다.

## 현재 Aegis 리소스 상태

2026-06-01 코드 기준 Hub cost target이다. AMP는 active Terraform 구성에서 제거했고, Hub NAT Gateway는 `ap-south-1a` 단일 NAT로 축소한다. ALB는 현재 비활성이며 UI 접근은 Tailscale을 통해 이루어진다. DataProcessor freshness refresh Scheduler는 1분 주기로 활성화되어 있지만 EventBridge Scheduler와 Lambda 호출량은 사용량 기반의 소액 비용이며 Hub 고정 시간 비용에는 포함하지 않는다. EKS 상태 확인은 기본적으로 `metrics-server`와 AWS/Kubernetes API 조회를 사용한다. `amazon-cloudwatch-observability` EKS managed add-on은 비용이 큰 optional monitoring path로 두며, 기본값은 disabled다.

| 영역 | 리소스 | 수량/크기 | 상태 |
| --- | --- | ---: | --- |
| EKS | `AEGIS-EKS` control plane (K8s v1.34) | 1 | running |
| EC2 | `AEGIS-EKS-node` t3.medium | 2 | running (ap-south-1a, 1c) |
| EBS | EKS node root volume gp3 20 GiB × 2 | 40 GiB | attached |
| VPC/Subnet | `AEGIS-VPC` (10.0.0.0/16), public/private × 2 AZ | 1 VPC / 4 subnet | active |
| NAT Gateway | `AEGIS-NAT-public-Azone` | 1 | target active |
| Elastic IP | NAT Gateway용 | 1 | target in-use |
| S3 | `aegis-bucket-data` | 1 | active |
| IoT Core | Thing / cert (factory-a) | 1 set | active |
| IoT Rules | `AEGIS_IoTRule_factory_a/b/c_raw_s3` (data-pipeline layer) | 3 | active (build-data-pipe 실행 시) |
| Lambda | `AEGIS-Lambda-DataProcessor`, `AEGIS-Lambda-GraphAggregator5m` (data-pipeline layer) | 2 | active (build-data-pipe 실행 시) |
| Lambda | `AEGIS-Lambda-CloudInfraFastCollector`, `AEGIS-Lambda-CloudInfraSlowCollector` | 2 | active (build-data-pipe 실행 시, usage based) |
| Lambda | `AEGIS-Lambda-RiskAlertDispatcher` | 1 | active (build-data-pipe 실행 시, S3 event based) |
| EventBridge Scheduler | `AEGIS-Schedule-DataProcessorRefresh1m`, `AEGIS-Schedule-GraphAggregator5m`, `AEGIS-Schedule-CloudInfraFastCollector1m`, `AEGIS-Schedule-CloudInfraSlowCollector5m` | 4 | active (build-data-pipe 실행 시, usage based) |
| DynamoDB | `AEGIS-DynamoDB-FactoryStatus` (foundation layer) | 1 | active (PAY_PER_REQUEST, 상시) |
| Secrets Manager | RiskAlertDispatcher Slack webhook secret metadata | 4 | active (cloud, factory-a, factory-b, factory-c) |
| AMP | removed | 0 | deletion target |
| ECR | `aegis/edge-agent`, `aegis/factory-a-log-adapter`, `aegis/edge-iot-publisher` | 3 repo | active |
| Route53 | public hosted zone `minsoo-tech.cloud` | 1 | active |
| ACM | `minsoo-tech.cloud` + SAN 2개 | 1 | issued (no charge) |
| KMS | AEGIS EKS cluster encryption key | 1 | active |
| ALB | `aegis-admin-ui` | **0** | **not created** (Tailscale 접근 중) |
| EKS workload | ArgoCD (7 pod), Grafana | active | observability/argocd ns |
| EKS workload | AWS LB Controller × 2, Tailscale Operator + 3 proxy | active | kube-system/tailscale ns |
| EKS add-on | `metrics-server` | 1 | active, default version |
| EKS add-on | `amazon-cloudwatch-observability` | 0 | optional, disabled by default |
| CloudWatch Logs | `/aws/eks/AEGIS-EKS/cluster` | 1 | EKS control plane logs |
| CloudWatch Logs | `/aws/containerinsights/AEGIS-EKS/{application,dataplane,host}` | optional | Container Insights 활성화 시 생성 |
| Reporting | Daily factory report stack | 0 | 수동 검증 완료 후 destroy, 필요 시 on-demand 재배포 |

2026-05-08 destroy 이후 KMS key `775cd837-1961-4660-893f-f220d9f250be` 등 이전 키는 `PendingDeletion` 상태(삭제 예정일 2026-06-07)이며 대기 기간 동안 monthly key storage charge는 없다.

EKS managed node group Auto Scaling Group은 직접 비용 리소스가 아니므로 EC2/EBS/NAT/EKS 기준으로 비용 계산한다.

## 시간당 비용 계산

### Hub active 시 고정 비용 (현재 상태: ALB 없음, Tailscale 접근)

2026-05-27 Terraform target 기준이다. 기존 배포에 NAT Gateway 2개와 AMP workspace가 남아 있으면 다음 `terraform apply`에서 Czone NAT/EIP와 AMP workspace 삭제가 계획되어야 한다.

| 비용 항목 | 수량 | 단가 | 계산 | 시간당 비용 |
| --- | ---: | ---: | --- | ---: |
| EKS standard cluster | 1 | `$0.1000 / hour` | `1 * 0.1000` | `$0.1000` |
| EC2 Linux `t3.medium` | 2 | `$0.0448 / hour` | `2 * 0.0448` | `$0.0896` |
| NAT Gateway hourly | 1 | `$0.0560 / hour` | `1 * 0.0560` | `$0.0560` |
| Elastic IP in-use (NAT) | 1 | `$0.0050 / hour` | `1 * 0.0050` | `$0.0050` |
| EBS gp3 storage | 40 GiB | `$0.0912 / GB-month` | `40 * 0.0912 / 730` | `$0.0050` |
| KMS customer managed key | 1 | `$1.00 / month` | `1 / 730` | `$0.0014` |
| Route53 public hosted zone | 1 | `$0.50 / month` | `0.50 / 730` | `$0.0007` |
| S3 Standard storage | ~negligible | `$0.025 / GB-month` | negligible | `~$0.0000` |
| **고정 합계 (ALB 없음)** | | | | **`$0.2577 / hour`** |

```text
0.1000 + 0.0896 + 0.0560 + 0.0050 + 0.0050 + 0.0014 + 0.0007 = 0.2577 USD/hour
```

| 기간 | 고정 비용 |
| --- | ---: |
| 1시간 | `~$0.26` |
| 24시간 | `~$6.18` |
| 730시간 (1개월 상시) | `~$188.1` |

위 계산은 세금, 크레딧, Free Tier, Savings Plans, Reserved Instances, 환율을 반영하지 않은 온디맨드 기준이다. AWS Load Balancer Controller pod 자체는 EKS node 위에서 실행되므로 고정 시간 비용에 별도 항목이 없다.

### Admin UI Ingress 활성화 시 추가 비용

`hub_admin_ingress_bootstrap.yml` Ansible playbook으로 Admin UI Ingress를 활성화하면 Public ALB 1개가 추가된다. 현재는 비활성이다.

| 비용 항목 | 수량 | 단가 | 계산 | 시간당 비용 |
| --- | ---: | ---: | --- | ---: |
| Application Load Balancer | 1 | `$0.0239 / hour` | `1 * 0.0239` | `$0.0239` |
| ALB LCU | 최소 사용량 기준 1 LCU 가정 | `$0.0080 / LCU-hour` | `1 * 0.0080` | `$0.0080` |
| Public IPv4 for internet-facing ALB | 2개 추정 | `$0.0050 / IP-hour` | `2 * 0.0050` | `$0.0100` |
| **ALB 추가 합계** | | | | **`$0.0419 / hour`** |

ALB 포함 시 고정 시간 비용: `0.2577 + 0.0419 = 0.2996 USD/hour` (~$218.7/month 상시)

실제 LCU와 public IPv4 수는 트래픽, AZ, ALB 동작 상태에 따라 달라질 수 있으므로 `aws elbv2 describe-load-balancers`, Cost Explorer, Public IP Insights로 다시 확인한다.

## 사용량 기반 추가 비용

### EKS Observability: metrics-server + CloudWatch Container Insights

2026-06-01 `infra/hub/observability_addons.tf` 기준으로 EKS 관측 add-on은 두 단계로 나눈다.

| 항목 | 상태 | 비용 영향 |
| --- | --- | --- |
| `metrics-server` EKS managed add-on | ACTIVE (`v0.8.1-eksbuild.6`) | 별도 AWS 과금 없음. 기존 EKS node 위에 pod 2개 실행 |
| `amazon-cloudwatch-observability` EKS managed add-on | optional, default disabled | CloudWatch Container Insights observations, logs ingest/storage 과금 발생 |
| `CloudWatchAgentServerPolicy` | CloudWatch Observability 활성화 시에만 attach | 자체 과금 없음 |

기본 상태에서 확인 가능한 값:

```text
kubectl top nodes/pods: metrics-server로 조회
EKS cluster/nodegroup/ASG 상태: AWS API로 조회
Pod phase/restart/ArgoCD health: Kubernetes API로 조회
```

CloudWatch Observability를 임시 활성화하면 추가로 확인 가능한 값:

```text
ContainerInsights metrics: node_cpu_utilization, pod_cpu_utilization 등 생성 확인
Log groups:
  /aws/containerinsights/AEGIS-EKS/application
  /aws/containerinsights/AEGIS-EKS/dataplane
  /aws/containerinsights/AEGIS-EKS/host
```

현재 클러스터 규모:

| 컴포넌트 | 수 |
| --- | ---: |
| cluster | 1 |
| nodes | 2 |
| namespaces | 10 |
| services | 27 |
| workloads (`deployment` + `statefulset` + `daemonset`) | 24 |
| pods | 27 |
| containers | 29 |

AWS 공식 Container Insights enhanced observability 예시는 EKS 컴포넌트별 평균 observations/minute를 아래처럼 계산한다.

```text
cluster      = 1,720 observations/min
node         = 68 observations/min
namespace    = 2 observations/min
service      = 2 observations/min
workload     = 7 observations/min
pod          = 138 observations/min
container    = 21 observations/min
```

현재 AEGIS-EKS 기준 월 observations 추정:

```text
per-minute observations
= 1*1720 + 2*68 + 10*2 + 27*2 + 24*7 + 27*138 + 29*21
= 6,433 observations/min

monthly observations
= 6,433 * 43,200 minutes
= 277,905,600 observations/month
```

AWS 공식 예시 단가 `$0.21 / 1M observations`를 적용하면:

```text
277.9M * 0.21 = ~$58.4/month
```

CloudWatch Logs는 observation 비용과 별도다. AWS 공식 예시의 Kubernetes performance event 평균 로그량을 현재 클러스터 크기에 적용하면:

```text
cluster    1 * 0.01621 GB = 0.016 GB/month
namespace 10 * 0.01850 GB = 0.185 GB/month
service   27 * 0.02182 GB = 0.589 GB/month
node       2 * 0.21365 GB = 0.427 GB/month
pod       27 * 0.45845 GB = 12.378 GB/month

estimated performance event logs = ~13.6 GB/month
```

CloudWatch Logs ingest를 `$0.50 / GB` 기준으로 잡으면:

```text
13.6 GB * 0.50 = ~$6.8/month
```

따라서 현재 2-node Hub 기준 CloudWatch Observability를 켰을 때의 optional 월 추가 비용은 아래처럼 잡는다.

| 항목 | 월 추정 |
| --- | ---: |
| Container Insights enhanced observations | `~$58/month` |
| CloudWatch Logs ingest, low-traffic baseline | `~$7/month` |
| CloudWatch Logs storage | `~$0.5/month 이하` |
| Metrics-server 자체 | `$0` |
| **합계** | **`~$65~75/month`** |

이 값은 CloudWatch Observability를 켠 상태로 상시 운영하는 730시간 기준이다. 작업 시간에만 Hub를 켜거나 Observability를 임시 활성화하는 경우 시간 비례로 줄어든다.

| 사용 패턴 | EKS observability 추가 비용 |
| --- | ---: |
| 하루 4시간 × 20일 (80시간) | `~$7~8/month` |
| 하루 8시간 × 20일 (160시간) | `~$14~16/month` |
| 하루 8시간 × 30일 (240시간) | `~$21~25/month` |
| 상시 운영 (730시간) | `~$65~75/month` |

비용 통제 기준:

- Container Insights는 Dashboard VPC에서 EKS node/pod CPU, memory, restart, ready 상태를 CloudWatch로 장기 조회해야 할 때만 켠다.
- 기본 Dashboard는 ECS/ALB/Lambda/DynamoDB/Scheduler는 CloudWatch에서 조회하고, EKS 내부 상태는 AWS API/Kubernetes API/metrics-server로 조회한다.
- 장시간 사용하지 않을 때는 `destroy-hub.sh`로 Hub와 함께 내린다.
- Container Insights log group retention은 별도 설정이 없으면 장기 저장 비용이 누적될 수 있으므로 후속 작업에서 7~14일 retention을 명시한다.
- application container stdout/stderr 로그량이 늘면 위 `$65~75/month`를 초과할 수 있다. 특히 ArgoCD/Grafana/Tailscale 로그 레벨을 debug로 올리지 않는다.

### AMP (Amazon Managed Prometheus)

AMP는 2026-05-27 비용 최적화 기준에서 active 구성에서 제거했다. 사용자는 AMP로 EKS 상태를 직접 확인하지 않고, 현재 데이터 처리 상태의 source of truth는 IoT Core -> Lambda data processor -> DynamoDB LATEST/HISTORY#STATE + S3 processed, DataProcessorRefresh1m -> stale `pipeline_status`/`risk` refresh, GraphAggregator5m -> DynamoDB GRAPH#5M + S3 processed_agg이다.

제거 대상:

| 대상 | 처리 |
| --- | --- |
| `infra/foundation/amp.tf` | 삭제 |
| `infra/hub/irsa_prometheus_remote_write.tf` | 삭제 |
| `infra/hub/irsa_grafana_amp_query.tf` | 삭제 |
| `observability/prometheus-agent` | Hub platform build에서 cleanup |
| Grafana AMP datasource | 제거, Grafana health 검증만 유지 |

기존 running 상태에서 estimated AMP 비용은 월 ~$66-112였고, active 구성 제거 후 목표 비용은 `$0/month`이다.

### NAT Gateway 데이터 처리

| 트래픽 원인 | 추정량 | 비고 |
| --- | --- | --- |
| ArgoCD git polling (3분 간격) | ~100 MB/일 | GitHub API + git fetch |
| AWS API 호출 (EKS, IAM 등) | ~50 MB/일 | |
| ECR 이미지 pull | ~500 MB/회 | 배포 시 일회성 |

추정 NAT 데이터량: **10–15 GB/월** → 비용: **~$0.56–0.84/월** (데모 수준에서 무시 가능)

### 기타 사용량 기반 항목

| 항목 | 기준 | 현재 판단 |
| --- | --- | --- |
| EC2 data transfer | 방향/리전/AZ에 따라 다름 | 현재 별도 대량 전송 없음 |
| t3 unlimited CPU credit | surplus credit 사용 시 과금 | 2026-05-06 확인 결과 `CPUSurplusCreditsCharged = 0` |
| S3 request/transfer | request 수와 data transfer 기준 | factory_state/infra_state raw 적재가 시작되면 PUT request가 주 비용 변수 |
| IoT Core messaging/rules | 메시지와 rule action 사용량 기준 | `build-iot-factory-a.sh` 이후 publisher 송신량에 따라 증가 |
| ECR storage | $0.10 / GB-month (50GB 초과분) | 현재 이미지 용량 기준 free tier 이내 |
| Route53 DNS queries | query 수 기준 | Hosted Zone 고정 비용 외 소량 |
| KMS API requests | 월 20,000 request free tier 이후 과금 | Hub EKS 실행 중 secret 암호화 수준 |
| CloudWatch Logs ingest/storage | ingest bytes와 저장량 기준 | Container Insights optional 활성화 시 월 `~$7+storage` 추정 |
| CloudWatch Container Insights | EKS observations 기준 | optional 활성화 시 2-node 현재 규모 월 `~$58` 추정 |
| ACM public certificate | public certificate 기준 | ALB에 연결하는 public ACM certificate 자체는 과금 없음 |
| ALB LCU | new connections, processed bytes 기준 | Admin UI Ingress 활성화 후 접속량에 따라 증가 |

### Cloud Infra Fast/Slow Collectors

2026-06-01 기준 cloud infra dashboard용 collector 2개가 data-pipeline layer에 추가됐다.

| 항목 | 값 |
| --- | --- |
| Fast Lambda | `AEGIS-Lambda-CloudInfraFastCollector`, 1분 주기 |
| Slow Lambda | `AEGIS-Lambda-CloudInfraSlowCollector`, 5분 주기 |
| Fast Scheduler | `AEGIS-Schedule-CloudInfraFastCollector1m` |
| Slow Scheduler | `AEGIS-Schedule-CloudInfraSlowCollector5m` |
| DynamoDB write | 실행마다 `CLOUD#infra/LATEST` PutItem + history PutItem |
| S3 PUT | 실행마다 `processed/cloud_infra/{fast,slow}/...` snapshot 1개 |
| History TTL | `HISTORY#FAST` 6시간, `HISTORY#SLOW` 24시간 |

월 실행 횟수:

```text
FastCollector 1분 = 43,200회/month
SlowCollector 5분 = 8,640회/month
합계 = 51,840회/month
```

대략 월 추가 비용:

| 항목 | 월 추정 |
| --- | ---: |
| Lambda invocation/duration | `~$0.3~0.8` |
| EventBridge Scheduler invocation | `~$0~0.05` |
| DynamoDB on-demand read/write | `~$0.3~0.6` |
| S3 PUT | `~$0.26` |
| S3 storage | `~$0.01~0.05` |
| CloudWatch metric API / Lambda logs | `~$0.1~0.4` |
| **합계** | **`~$1~3/month`** |

SlowCollector는 EKS access entry로 `AmazonEKSAdminViewPolicy`를 cluster scope에 연결한다. 이는 쓰기 권한 비용이 아니라 cluster-wide read visibility를 부여하는 보안/권한 영향이다.

이 collector 방식은 CloudWatch Container Insights를 기본 OFF로 유지하면서 Dashboard에 필요한 요약만 DynamoDB/S3 read model로 저장하기 위한 비용 절감 경로다. Container Insights optional 활성화 비용(`~$65~75/month`)과 별개로 계산한다.

### RiskAlertDispatcher

2026-06-02 기준 RiskAlertDispatcher가 data-pipeline layer에 추가됐다.

| 항목 | 값 |
| --- | --- |
| Lambda | `AEGIS-Lambda-RiskAlertDispatcher`, S3 event based |
| Trigger | S3 `processed/{factory}/state_snapshot/`, `processed/cloud_infra/{fast,slow}/` ObjectCreated |
| DynamoDB write | alert reserve/result 기록 시 `ALERT#{scope}` UpdateItem |
| Secrets Manager read | Slack 전송 시 scope별 webhook secret GetSecretValue |
| Secrets Manager secrets | cloud/default 1개 + factory-a/b/c 3개 |
| CloudWatch Logs | `/aws/lambda/AEGIS-Lambda-RiskAlertDispatcher`, 30일 retention |

비용 영향:

- Lambda/S3 event/DynamoDB write는 warning/danger snapshot이 발생할 때만 의미 있게 증가한다.
- DynamoDB cooldown/dedupe 때문에 동일 조건 반복 알림은 지정된 cooldown 동안 Slack 재전송을 건너뛴다.
- Secrets Manager secret 4개는 secret value 저장용 관리형 리소스 비용이 발생한다. 로컬 `.secrets/`의 URL 값은 repo와 Terraform state에 저장하지 않는다.
- 개발/MVP 규모에서는 월 추가 비용이 소액이지만, 알림 채널을 factory별로 늘리면 Secrets Manager secret 수와 Slack 전송 횟수 기준으로 재산정한다.

### Daily Factory Report Reporting Stack

2026-05-28 기준 Bedrock 기반 factory별 일일 운영 보고서는 `infra/reporting/` 별도 Terraform root module로 배포/검증했다. `factory-b`, `report_date=2026-05-27` 수동 Step Functions 실행은 `SUCCEEDED`였고 S3 `reports/daily/` 산출물을 확인했다. 검증 후 자동 실행 비용 방지를 위해 `destroy-reporting.sh`로 stack을 삭제했다.

설계 기준:

```text
EventBridge Scheduler: 1회/day
Step Functions Standard: DailyFactoryReportStateMachine
Lambda: PrepareReportWindow 1회/day
Lambda: AggregateFactoryHour 72회/day
Lambda: MergeFactoryDaily 3회/day
Lambda: GenerateFactoryReport 3회/day
S3 input: processed/factory-a,b,c/{factory_state,risk_score,infra_state,state_snapshot}
S3 output: reports/daily/yyyy=YYYY/mm=MM/dd=DD/{factory_id}/
Bedrock input: report-context.json only
```

factory-b 기준 실측 근사 비용은 `docs/ops/25_daily_factory_report_cost.md`를 source of truth로 둔다.

| 실행 범위 | 비용 추정 |
| --- | ---: |
| factory 1개 report 1회 | `$0.12~$0.18` |
| factory 3개 daily run 1일 | `$0.36~$0.54` |
| factory 3개 daily run 30일 | `$10.8~$16.2/month` |

이 비용은 Free Tier 제외 marginal cost 기준이다. 주요 변수는 Bedrock token, Lambda billed duration, S3 `GetObject` request count다.

기존 설계 시점의 월간 MVP 추정 비용은 아래와 같았으나, 실제 factory-b 실행에서는 Claude 3 Sonnet과 `state_snapshot` 입력이 포함되어 더 높게 잡는다.

| 항목 | 월 추정 비용 | 비고 |
| --- | ---: | --- |
| Lambda | ~$1.1~$2.2 | 79 invocation/day, AggregateFactoryHour 중심 |
| Step Functions Standard | ~$0.1 | state transition 기준 소량 |
| S3 GET/LIST/PUT | ~$2.3 | processed small object read가 주 비용 |
| CloudWatch Logs | ~$0.02~$0.15 | payload logging 금지 전제 |
| Bedrock Claude 3 Haiku | ~$0.35~$0.75 | factory별 보고서 3개/day |
| Bedrock Claude 3.5 Haiku | ~$1.10~$2.35 | 모델 변경 시 대체 추정 |
| **합계** | **~$3.8~$7/month** | 보수적으로 ~$10/month 이하를 초기 기준으로 둠 |

비용 통제 기준:

- S3 `raw/`는 Bedrock에 직접 넣지 않는다.
- `state_snapshot/` 전체 읽기는 비용/성능 병목이므로 latest N개 또는 hour별 마지막 snapshot으로 축소한다.
- Bedrock에는 `report-context.json`만 전달한다.
- `MAX_CONTEXT_EVENTS=10`, `MAX_CONTEXT_BYTES=120000` 기본값을 유지한다.
- Lambda 로그에는 raw payload와 Bedrock prompt 전문을 남기지 않는다.
- reporting Terraform은 `data_bucket_name` variable로 기존 S3 bucket을 조회하고, foundation remote state에 의존하지 않는다.
- reporting stack은 필요할 때만 `build-reporting.sh`로 올리고, 검증 후 `destroy-reporting.sh`로 내린다.

## 주요 비용 원인 분석 (2026-06-01 기준)

현재 기본 target 상태(ALB 없음, AMP 없음, NAT Gateway 1개, EKS Container Insights disabled)에서 월 30일 상시 운영 가정 시 비용 구조:

| 순위 | 항목 | 월 비용 | 전체 비중 | 비고 |
| ---: | --- | ---: | ---: | --- |
| 1 | EKS control plane | $73.0 | ~39% | 고정 비용 |
| 2 | EC2 t3.medium × 2 | $65.4 | ~35% | 인스턴스 타입 조정 가능 |
| 3 | NAT Gateway (hourly × 1) | $40.9 | ~22% | 단일 NAT 확정 |
| 4 | 기타 (EBS, Route53, KMS, NAT 데이터 등) | ~$9 | ~5% | |
| | **합계** | **~$188** | 100% | |

**고정 비용 합계 (ALB 없음): ~$188.1/월**
**기본 사용량 기반 합계 (NAT 데이터 등): 소량**
**총합 (상시 운영, CloudWatch Observability off): ~$189/월**

CloudWatch Observability optional 활성화 시: +$65~75/월 → **~$253~263/월**
Admin UI ALB 추가 시: +$30.5/월 → **~$219/월** 기본, **~$284~294/월** Observability 포함

## 실제 사용 패턴별 월 비용

이 프로젝트처럼 작업 시에만 Hub를 재생성하고 사용 후 destroy하는 패턴 기준이다.

| 사용 패턴 | 월 가동 시간 | 기본 비용 | Observability optional 추가 | 합계 |
| --- | ---: | ---: | ---: | ---: |
| 하루 4시간 × 20일 | 80시간 | ~$20.6 | ~$7~8 | **~$20.6 기본 / ~$28~29 포함** |
| 하루 8시간 × 20일 | 160시간 | ~$41.2 | ~$14~16 | **~$41.2 기본 / ~$55~57 포함** |
| 하루 8시간 × 30일 | 240시간 | ~$61.8 | ~$21~25 | **~$61.8 기본 / ~$83~87 포함** |
| 상시 운영 | 730시간 | ~$188.1 | ~$65~75 | **~$189 기본 / ~$253~263 포함** |

`destroy-data-pipe.sh` + `destroy-hub.sh` 실행 후 (foundation 유지 시) 고정 비용은 사실상 $0/hr 이 된다.

### destroy-data-pipe + destroy-hub 후 (Foundation 유지) 비용 기준

2026-05-21 기준. Hub와 data-pipeline을 내리고 foundation만 남은 상태.

| 리소스 | 서비스 | 시간당 비용 | 비고 |
| --- | --- | ---: | --- |
| S3 버킷 (aegis-bucket-data) | S3 Standard | ~$0.000003 | 개발 중 ~100MB |
| ECR × 3 repos | ECR | **~$0.00008** | ~600MB 이미지 기준 |
| DynamoDB (AEGIS-DynamoDB-FactoryStatus) | DynamoDB | ~$0 | PAY_PER_REQUEST, `HISTORY#STATE`/`GRAPH#5M` TTL 후 idle |
| GitHub Actions OIDC + IAM | IAM | $0 | |
| IoT Thing/Cert/Policy | IoT Core | $0 | 연결 없으면 메시지 과금 없음 |
| **합계** | | **~$0.00009/hr** | **~$0.07/월** |

비용의 전부가 ECR 이미지 스토리지. 이미지 미push 상태면 사실상 $0/hr.

### destroy-all (Foundation 포함) 후 비용 기준

`DESTROY_FOUNDATION=true scripts/destroy/destroy-foundation.sh` 실행 후 EKS, EC2, EBS, VPC, NAT Gateway, Public IPv4, Route53 Hosted Zone, ACM certificate, S3, IoT Core, DynamoDB, ECR이 모두 삭제되면 active AEGIS fixed-cost resource는 0개가 된다. 이 상태의 고정 시간 비용은 `0.0000 USD/hour`이다. 삭제 예약된 historical KMS key는 대기 기간 동안 monthly key storage charge가 없다.

## 태그 기반 비용 조회 기준

공통 비용 태그:

```text
Project     = AEGIS
Environment = hub-mvp 또는 foundation-mvp
ManagedBy   = terraform
Component   = hub 또는 foundation
```

Hub의 Terraform provider `default_tags`는 직접 생성 리소스에 적용된다. EKS managed node group이 간접 생성하는 EC2 instance, EBS volume, network interface는 launch template `tag_specifications`를 통해 같은 공통 태그를 전파한다.

비용 검증 시에는 아래 리소스를 우선 확인한다.

```text
EC2 instances: tag:Project=AEGIS and Name=AEGIS-EKS-node
EBS volumes: tag:Project=AEGIS
NAT Gateway/EIP: tag:Project=AEGIS
EKS cluster/nodegroup: AEGIS-EKS / AEGIS-EKS-node
AMP workspace: removed from active Terraform configuration
S3 bucket: aegis-bucket-data
IoT resources: AEGIS-IoTThing-factory-a, AEGIS-IoTPolicy-factory-a, AEGIS_IoTRule_factory_a_raw_s3
Route53 hosted zone: minsoo-tech.cloud
ALB: aegis-admin-ui
```

EKS가 관리하는 Auto Scaling Group은 직접 비용이 붙는 리소스가 아니다. ASG 태그가 비어 있어도 실제 비용은 EC2 instance, EBS volume, NAT Gateway, Public IPv4, EKS control plane에서 발생하므로 해당 리소스 태그를 기준으로 비용을 산정한다.

## 비용 절감 기준

작업을 멈추거나 장시간 사용하지 않을 때 가장 먼저 내릴 대상은 Hub다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-hub.sh
```

이 명령으로 줄어드는 주요 비용:

- EKS control plane
- EC2 EKS worker node
- NAT Gateway
- NAT Gateway Elastic IP
- EBS root volume
- EKS encryption용 customer managed KMS key
- Route53 Hosted Zone `minsoo-tech.cloud`
- Admin UI Ingress Public ALB, target group, listener, security group, public IPv4
- EKS Container Insights observations/log ingest (optional 활성화 시)

`infra/foundation`은 S3, ECR, DynamoDB처럼 Hub EKS 생명주기와 분리되는 영속 리소스다. 전체 비용 제거가 필요하면 `scripts/destroy/destroy-all.sh`로 IoT, Hub, foundation을 모두 내린다.

2026-05-08 `destroy-all` 후 최신 EKS key `775cd837-1961-4660-893f-f220d9f250be`를 포함한 AEGIS EKS KMS key들이 `PendingDeletion` 상태임을 확인했다. 최신 key의 삭제 예정일은 2026-06-07이다. AWS KMS 공식 가격 기준으로 삭제 예약된 customer managed key는 대기 기간 동안 monthly key storage charge가 없다.

## 갱신 규칙

다음 변경이 생기면 이 문서를 다시 계산한다.

- `infra/hub`에 AWS 리소스가 추가, 삭제, 크기 변경됨
- `infra/foundation`에 ECR, S3 lifecycle, IoT Rule, DynamoDB, KMS 같은 리소스가 추가됨
- `docs/issues/` 또는 `docs/planning/`에 새 상시 운영 AWS 컴포넌트가 추가됨
- NAT Gateway 수, node instance type, node desired size, EBS 크기, EKS Kubernetes support tier가 바뀜
- Dashboard VPC, ALB, WAF, Cognito, CloudFront, Route53 같은 외부 접근 경로가 추가됨
- Grafana/CloudWatch Logs처럼 관측 계층의 수집량 또는 저장량 기준이 바뀜
- Hub EKS 관측 경로(CloudWatch, 후속 경량 Prometheus 등)가 추가됨

비용 갱신 시 기록할 내용:

```text
1. 현재 실제 리소스 조회 결과
2. 단가 확인 날짜와 리전
3. 시간당 고정 비용
4. 사용량 기반 비용
5. 종료하거나 줄일 수 있는 비용원
```

## 가격 출처

2026-06-01 기준 AWS 공식 가격 문서와 현재 `AEGIS-EKS` 실측 리소스 수를 함께 확인했다. Container Insights 단가는 AWS 공식 예시의 US East 기준 단가를 적용했으며, 실제 청구는 `ap-south-1` 리전 가격과 Free Tier/크레딧 적용 여부에 따라 달라질 수 있다.

- Amazon EKS pricing: https://aws.amazon.com/eks/pricing/
- Amazon EC2 On-Demand pricing: https://aws.amazon.com/ec2/pricing/on-demand/
- NAT Gateway pricing: https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
- Public IPv4 pricing announcement: https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/
- Amazon EBS pricing: https://aws.amazon.com/ebs/pricing/
- Amazon S3 pricing: https://aws.amazon.com/s3/pricing/
- AWS KMS pricing: https://aws.amazon.com/kms/pricing/
- Elastic Load Balancing pricing: https://aws.amazon.com/elasticloadbalancing/pricing/
- Amazon Route53 pricing: https://aws.amazon.com/route53/pricing/
- AWS Certificate Manager pricing: https://aws.amazon.com/certificate-manager/pricing/
- Amazon Managed Service for Prometheus pricing: https://aws.amazon.com/prometheus/pricing/
- Amazon CloudWatch pricing: https://aws.amazon.com/cloudwatch/pricing/
- Amazon CloudWatch Container Insights docs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html
