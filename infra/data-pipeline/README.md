# infra/data-pipeline

상태: source of truth
기준일: 2026-06-01

## 목적

IoT Core → Lambda data processor 처리 파이프라인과 5분 그래프 집계 인프라를 관리한다.
Hub EKS와 독립적으로 올리고 내릴 수 있는 on-demand 레이어다.

## 레이어 특성

- **On-demand**: `scripts/build/build-data-pipe.sh` / `scripts/destroy/destroy-data-pipe.sh`로 개별 관리
- **Foundation 의존**: S3 버킷(`aegis-bucket-data`)과 DynamoDB 테이블(`AEGIS-DynamoDB-FactoryStatus`)은 `infra/foundation` 영구 리소스를 `data` source로 참조
- **Hub 독립**: EKS Hub와 교차 의존 없음. Hub 없이도 단독 apply/destroy 가능

## 관리 리소스

| 리소스 | 이름 | 역할 |
| --- | --- | --- |
| IoT Rule (factory-a) | `AEGIS_IoTRule_factory_a_raw_s3` | `aegis/factory-a/+` → S3 raw 적재 |
| IoT Rule (factory-b) | `AEGIS_IoTRule_factory_b_raw_s3` | `aegis/factory-b/+` → S3 raw 적재 |
| IoT Rule (factory-c) | `AEGIS_IoTRule_factory_c_raw_s3` | `aegis/factory-c/+` → S3 raw 적재 |
| Lambda | `AEGIS-Lambda-DataProcessor` | IoT Core 수신 메시지 처리 |
| IAM Role | `AEGIS-IAMRole-Lambda-DataProcessor` | Lambda 실행 역할 (DynamoDB R/W, S3 processed PutObject) |
| CloudWatch Log Group | `/aws/lambda/AEGIS-Lambda-DataProcessor` | Lambda 실행 로그 |
| EventBridge Scheduler | `AEGIS-Schedule-DataProcessorRefresh1m` | 1분 주기 stale pipeline_status/risk refresh |
| IAM Role | `AEGIS-IAMRole-Scheduler-DataProcessorRefresh` | DataProcessor refresh Scheduler의 Lambda invoke 역할 |
| Lambda | `AEGIS-Lambda-GraphAggregator5m` | DynamoDB HISTORY#STATE → GRAPH#5M / S3 processed_agg 집계 |
| EventBridge Scheduler | `AEGIS-Schedule-GraphAggregator5m` | 5분 주기 graph aggregator 호출 |
| IAM Role | `AEGIS-IAMRole-Scheduler-GraphAggregator5m` | GraphAggregator5m Scheduler의 Lambda invoke 역할 |
| CloudWatch Log Group | `/aws/lambda/AEGIS-Lambda-GraphAggregator5m` | graph aggregator 실행 로그 |

## Foundation 참조 구조

```hcl
# dynamodb.tf
data "aws_dynamodb_table" "factory_status" {
  name = var.dynamodb_table_name
}
```

DynamoDB 테이블은 `infra/foundation`에서 생성하고, 이 레이어에서는 조회만 한다.
이 구조 때문에 **destroy 순서가 중요하다**.

## Destroy 순서 제약

```text
destroy-data-pipe.sh  ← 반드시 먼저 실행
destroy-foundation.sh ← data-pipeline 삭제 후 실행
```

역순으로 실행하면 `data "aws_dynamodb_table"` lookup이 실패하고 `terraform destroy`가 중단된다.

## Build 순서 제약

```text
build-foundation.sh  ← 반드시 먼저 (DynamoDB, S3 생성)
build-data-pipe.sh   ← foundation apply 후 실행
```

## 파일

| 파일 | 역할 |
| --- | --- |
| `iot_rule.tf` | IoT Rule × 3 (factory-a/b/c), IAM Role/Policy, S3 raw 적재 설정 |
| `lambda.tf` | DataProcessor Lambda 함수, IAM Role/Policy, CloudWatch Log Group, DataProcessorRefresh1m Scheduler |
| `graph_aggregator_lambda.tf` | GraphAggregator5m Lambda, IAM, EventBridge Scheduler |
| `dynamodb.tf` | foundation DynamoDB 테이블 data source 조회 |
| `data.tf` | foundation S3 버킷 등 외부 리소스 data source 참조 |
| `variables.tf` | 입력 변수 정의 |
| `outputs.tf` | IoT Rule 이름, Lambda ARN, GraphAggregator5m, DynamoDB name/ARN |
| `versions.tf` | Terraform/provider 버전 고정 |
| `providers.tf` | AWS provider 설정 |
| `locals.tf` | 공통 태그 등 로컬 값 |
| `terraform.tfvars.example` | 변수 예시 (실제 `terraform.tfvars`는 Git 제외) |
| `lambda_data_processor.zip` | Terraform `archive_file`이 생성하는 DataProcessor 배포 아티팩트. Git에는 저장하지 않음 |
| `lambda_graph_metrics_aggregator.zip` | Terraform `archive_file`이 생성하는 GraphAggregator5m 배포 아티팩트. Git에는 저장하지 않음 |

## Lambda 배포 아티팩트

`lambda_data_processor.zip`은 Terraform `archive_file` data source가 `apps/data-processor/`의 Python 코드를 패키징해 생성한다. `lambda_graph_metrics_aggregator.zip`은 `apps/graph-metrics-aggregator/`를 패키징한다. 둘 다 수동 zip 생성은 필요 없다.

코드 변경 후 재배포 시:

```bash
scripts/build/build-data-pipe.sh [MFA_OTP]
```

## terraform.tfvars 예시

```hcl
dynamodb_table_name        = "AEGIS-DynamoDB-FactoryStatus"
dynamodb_history_ttl_hours = 2

lambda_graph_aggregator_name             = "AEGIS-Lambda-GraphAggregator5m"
graph_aggregator_enabled                 = true
graph_aggregator_factory_ids             = ["factory-a", "factory-b", "factory-c"]
graph_bucket_minutes                     = 5
graph_aggregator_lookback_buckets        = 1
graph_bucket_ttl_hours                   = 48
graph_expected_sample_interval_seconds   = 3
graph_ai_score_threshold                 = 0.7
```

## 실행

```bash
# 진입점 사용 권장
scripts/build/build-data-pipe.sh [MFA_OTP]
scripts/destroy/destroy-data-pipe.sh [MFA_OTP]

# 직접 실행
cd infra/data-pipeline
terraform init
terraform plan
terraform apply
```

## 검증 절차 (build 후)

1. IoT Core 콘솔에서 `aegis/factory-a/factory_state` topic으로 테스트 메시지 publish
2. CloudWatch Logs `/aws/lambda/AEGIS-Lambda-DataProcessor`에서 처리 로그 확인
3. DynamoDB `AEGIS-DynamoDB-FactoryStatus`에서 LATEST 아이템 조회
4. S3 `processed/{factory_id}/state_snapshot/` 경로에서 TTL 없는 전체 상태 snapshot 확인
5. EventBridge Scheduler `AEGIS-Schedule-GraphAggregator5m` 상태와 GraphAggregator5m CloudWatch Logs 확인
6. DynamoDB `GRAPH#5M#...` 아이템과 S3 `processed_agg/{factory_id}/metrics_5m/...` 객체 확인
