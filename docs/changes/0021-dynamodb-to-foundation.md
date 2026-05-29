# 0021 DynamoDB: infra/data-pipeline → infra/foundation

상태: accepted
결정일: 2026-05-21
영향 범위: M4, infra/foundation, infra/data-pipeline, destroy 순서 제약

## 기존 계획

`AEGIS-DynamoDB-FactoryStatus` 테이블을 `infra/data-pipeline/` Terraform으로 관리하고 `destroy-data-pipe.sh` 실행 시 함께 삭제했다.

```text
infra/data-pipeline/
  └── dynamodb.tf   ← resource "aws_dynamodb_table" ...
```

## 변경된 실제 기준

DynamoDB 테이블을 `infra/foundation/` 영구 리소스로 이관하고, `infra/data-pipeline/`에서는 `data "aws_dynamodb_table"` data source로 참조한다.

```text
infra/foundation/
  └── dynamodb.tf   ← resource "aws_dynamodb_table" ...

infra/data-pipeline/
  └── dynamodb.tf   ← data "aws_dynamodb_table" ...  (조회만)
```

## 변경 이유

1. **상태 저장소**: DynamoDB는 IoT Rule/Lambda와 달리 누적 이력 데이터를 보관한다. data-pipeline destroy 시 HISTORY#STATE/GRAPH#5M TTL 아이템이 전부 삭제되면 디버깅 맥락을 잃는다.
2. **Lambda Notifier 대비**: 향후 DynamoDB Streams 기반 Lambda Notifier를 추가할 때 테이블 ARN이 안정적으로 유지되어야 Streams event source mapping 설정이 단순해진다.
3. **비용**: DynamoDB PAY_PER_REQUEST 기준 대기 비용이 사실상 $0이므로 foundation에 유지해도 추가 비용이 없다.

## 영향

### destroy 순서 제약

`data "aws_dynamodb_table"` 은 `terraform destroy` 계획 단계에서도 해당 테이블이 실제로 존재해야 한다. 따라서 다음 순서를 반드시 지켜야 한다:

```text
destroy-data-pipe.sh  → foundation destroy 이전에 반드시 먼저 실행
destroy-foundation.sh → data-pipeline이 삭제된 상태여야 함
```

역순으로 실행하면 `terraform destroy`가 data source lookup 실패로 종료된다.

### build 순서

DynamoDB가 foundation에 있으므로 data-pipeline 배포 전에 foundation이 apply되어 있어야 한다:

```text
build-foundation.sh → build-data-pipe.sh  (순서 유지)
```

`build-all.sh`는 foundation → hub → data-pipe 순서로 실행하므로 자동 준수된다.

### 변경된 Terraform 파일

| 파일 | 변경 내용 |
| --- | --- |
| `infra/foundation/dynamodb.tf` | resource 추가 |
| `infra/foundation/variables.tf` | `dynamodb_table_name` 변수 추가 |
| `infra/foundation/outputs.tf` | `dynamodb_table_name`, `dynamodb_table_arn` output 추가 |
| `infra/foundation/terraform.tfvars.example` | `dynamodb_table_name` 예시 추가 |
| `infra/data-pipeline/dynamodb.tf` | resource → data source 전환 |
| `infra/data-pipeline/lambda.tf` | `data.aws_dynamodb_table.factory_status.*` 참조로 변경 |
| `infra/data-pipeline/outputs.tf` | data source 기반 output으로 변경 |
| `infra/data-pipeline/terraform.tfvars.example` | 주석 업데이트 |

## 업데이트 필요한 문서

- `scripts/build/README.md` — data-pipeline 설명에서 DynamoDB 제거 ✓
- `scripts/destroy/README.md` — destroy 순서 제약, data-pipeline layer 추가 ✓
- `docs/ops/00_quick_start.md` — foundation 리소스 목록 갱신 ✓
- `docs/ops/15_aws_cost_baseline.md` — DynamoDB foundation 섹션으로 이동 ✓
- `docs/specs/data_storage_pipeline.md` — 테이블 레이어 명시 ✓
- `docs/issues/M4_data-plane.md` — Issue 6 구현 메모 반영 ✓
- `docs/README.md` — Hub bootstrap roots 설명 갱신 ✓

## 검증

- `infra/foundation/`: `terraform fmt -check` 통과
- `infra/data-pipeline/`: `terraform fmt -check` 통과
- 실제 `terraform apply`/`destroy` 검증: 다음 AWS 배포 사이클에서 확인
