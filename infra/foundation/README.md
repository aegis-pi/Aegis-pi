# Foundation Layer

이 디렉터리는 Hub EKS 생명주기와 분리해야 하는 영속 리소스를 관리한다.

`infra/hub`는 비용 절감을 위해 자주 destroy할 수 있지만, 이 root의 리소스는 Hub EKS를 내렸다 올려도 유지한다.

## 현재 관리 리소스

- S3 데이터 버킷: `aegis-bucket-data`
- DynamoDB 테이블: `AEGIS-DynamoDB-FactoryStatus` (LATEST/HISTORY#STATE/GRAPH#5M, PAY_PER_REQUEST, TTL enabled)
- ECR repository: `aegis/edge-agent`, `aegis/factory-a-log-adapter`, `aegis/edge-iot-publisher`
- GitHub Actions OIDC provider와 ECR push role: `AEGIS-GitHubActions-ECRPush`
- Admin UI Route53 Hosted Zone: `minsoo-tech.cloud`
- Admin UI ACM certificate: `minsoo-tech.cloud`, `argocd.minsoo-tech.cloud`, `grafana.minsoo-tech.cloud`

IoT Rule × 3 (factory-a/b/c)와 Lambda DataProcessor는 `infra/data-pipeline/` on-demand 레이어에서 관리한다.
Hub Admin UI Ingress가 만드는 ALB는 `infra/hub`/Ansible 생명주기를 따르지만, registrar NS 위임과 ACM 인증서는 이 foundation root가 보존한다.

## DynamoDB 기준

```text
table:            AEGIS-DynamoDB-FactoryStatus
billing_mode:     PAY_PER_REQUEST
hash_key:         pk (String)
range_key:        sk (String)
TTL:              ttl (enabled; item별 ttl 값은 data-pipeline Lambda가 설정)
PITR:             enabled
stream_enabled:   true
stream_view_type: NEW_AND_OLD_IMAGES
```

DynamoDB Streams는 M6 Risk Twin/Dashboard 구현을 위한 change-data-capture 기반 확장 경로 확보 목적으로 활성화했다. 현재 소비자는 없으며 비용 추가는 없다.

아이템 구조:

| 아이템 유형 | PK | SK |
| --- | --- | --- |
| LATEST | `FACTORY#{factory_id}` | `LATEST` |
| HISTORY#STATE | `FACTORY#{factory_id}` | `HISTORY#STATE#{updated_at}` |
| GRAPH#5M | `FACTORY#{factory_id}` | `GRAPH#5M#{bucket_start}` |

DynamoDB `HISTORY#STATE`는 갱신된 `LATEST`와 같은 구조를 저장하고 `ttl`만 추가한다. 같은 snapshot은 S3 processed `state_snapshot/`에도 저장하되 S3에는 `ttl`을 제외한다. `GRAPH#5M`은 data-pipeline의 GraphAggregator5m Lambda가 `HISTORY#STATE`를 5분 단위로 집계해 저장한다.

DynamoDB는 Hub EKS destroy와 무관하게 유지한다. `infra/data-pipeline/`에서 `data "aws_dynamodb_table"`로 참조하므로, data-pipeline destroy는 반드시 foundation destroy 이전에 먼저 수행해야 한다.

## Admin UI DNS / ACM 기준

```text
domain:          minsoo-tech.cloud
argocd host:     argocd.minsoo-tech.cloud
grafana host:    grafana.minsoo-tech.cloud
hosted zone id:  Z04285032XLZT6GPVQEE4
certificate arn: arn:aws:acm:ap-south-1:611058323802:certificate/528e603a-9109-4427-bfea-c20f3a619be6
```

Route53 Hosted Zone과 ACM certificate는 Hub 비용 절감을 위한 `destroy-hub.sh` 대상이 아니다.
가비아 네임서버는 foundation Hosted Zone 생성 후 최초 1회만 Route53 NS 4개로 위임한다.
이 foundation root를 destroy해서 Hosted Zone을 새로 만들 때만 가비아 NS 재설정이 필요하다.

Hub Admin UI ALB는 매번 Hub/Ingress 재생성 때 바뀔 수 있으며, `scripts/build/build-admin-ui-after-ns.sh`가 기존 Hosted Zone의 `argocd.*`/`grafana.*` record를 현재 ALB로 다시 연결한다.

## ECR 기준

```text
repository: aegis/edge-agent
repository URL: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/edge-agent
repository ARN: arn:aws:ecr:ap-south-1:611058323802:repository/aegis/edge-agent
image tag mutability: MUTABLE
scan on push: enabled
encryption: AES256
deployment tag: sha-<7-char-git-sha>
moving tags: main, latest
untagged image expiration: 7 days
sha-* image retention: latest 50 images
```

Lambda data processor는 zip 배포(`lambda_data_processor.zip`)를 기본으로 하며 별도 ECR repository를 사용하지 않는다. `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator` repository는 만들지 않는다.

현재 ECR repository:
- `aegis/edge-agent`: M3 smoke image 검증용
- `aegis/factory-a-log-adapter`: factory-a raw/log → canonical JSON 변환
- `aegis/edge-iot-publisher`: local spool/outbox → IoT Core publish (factory-a/b/c 공통)

모든 ECR repository에 `force_delete = true`를 설정해 `terraform destroy` 시 이미지가 남아있어도 repository를 삭제할 수 있도록 했다.

```text
deployment tag: sha-<7-char-git-sha>
moving tags: main, latest
untagged image expiration: 7 days
sha-* image retention: latest 50 images
```

M5에서 `dummy-data-generator`를 구현할 때 별도 repository를 추가한다.

ArgoCD가 배포할 Helm values는 `sha-<7자리>` 태그를 배포 기준으로 삼는다. `main`과 `latest`는 빌드 확인과 수동 디버깅을 위한 이동 태그로만 사용한다.

Spoke K3s는 EKS managed node가 아니므로 EKS node role의 ECR pull 권한으로는 이미지를 받을 수 없다. M3 Issue 3~4에서 GitHub Actions push role과 Spoke K3s `imagePullSecret` 갱신 방식을 별도 연결한다.

## GitHub Actions OIDC / ECR Push Role

M3 Issue 3 기준 code repository의 GitHub Actions는 장기 AWS access key를 저장하지 않고 GitHub OIDC로 AWS role을 assume한다.

```text
OIDC provider: arn:aws:iam::611058323802:oidc-provider/token.actions.githubusercontent.com
role: arn:aws:iam::611058323802:role/AEGIS-GitHubActions-ECRPush
allowed repository subject: repo:aegis-pi/Aegis-pi:ref:refs/heads/main
allowed ECR repositories:
- arn:aws:ecr:ap-south-1:611058323802:repository/aegis/edge-agent
- arn:aws:ecr:ap-south-1:611058323802:repository/aegis/factory-a-log-adapter
- arn:aws:ecr:ap-south-1:611058323802:repository/aegis/edge-iot-publisher
workflow: .github/workflows/build-push.yaml
```

Role policy는 ECR authorization token 조회와 현재 3개 ECR repository image push에 필요한 권한만 허용한다. GitHub Actions가 Spoke K3s 또는 Hub EKS에 직접 `kubectl apply`하지 않는다는 CD 경계는 유지한다.

검증 결과:

```text
terraform validate: success
terraform apply target: aws_ecr_repository.edge_agent, aws_ecr_lifecycle_policy.edge_agent
apply result: 2 added, 0 changed, 0 destroyed
aws ecr describe-repositories: MUTABLE, scanOnPush=true, AES256
terraform destroy target: aws_ecr_lifecycle_policy.edge_agent, aws_ecr_repository.edge_agent
destroy result: 0 added, 0 changed, 2 destroyed
current AWS state: deleted, RepositoryNotFoundException 확인
```

## S3 데이터 버킷 기준

```text
bucket: aegis-bucket-data
region: ap-south-1
versioning: enabled
encryption: SSE-S3 (AES256)
public access block: enabled
force destroy: enabled for MVP teardown
terraform apply: 10 added, 0 changed, 0 destroyed
```

Prefix 기준:

```text
raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
processed/{factory_id}/{dataset}/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
processed_agg/{factory_id}/metrics_5m/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/mm={MM}.json
```

MVP 기준 Dashboard의 현재 상태는 S3 `latest/` object가 아니라 DynamoDB LATEST에서 조회하고, 최근 그래프는 GRAPH#5M을 우선 조회한다. 이 Terraform root에는 과거 초안의 `latest/` lifecycle rule이 남아 있지만, 현재 데이터 플레인 계약에서 `latest/`는 primary current-state 저장소가 아니다. 장기 이력과 재처리는 S3 `raw/`, `processed/`, `processed_agg/`를 기준으로 하고, 화면 current state는 DynamoDB를 기준으로 한다.

## IoT Rule 기준

IoT Rule × 3 (factory-a/b/c)는 `infra/data-pipeline/`에서 관리한다. foundation에는 IoT Rule이 없다.

S3 raw 적재 경로:

```text
raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
```

S3 raw object body는 publisher가 보낸 canonical JSON과 동일하다.

## Lifecycle 기준

| Prefix | 기준 |
| --- | --- |
| `raw/` | 90일 후 Glacier Instant Retrieval 전환 |
| `processed/` | 365일 후 Standard-IA 전환 |
| `processed_agg/` | `processed/`와 같은 장기 분석/그래프 보조 산출물 prefix. lifecycle가 필요하면 `processed/`와 같은 보존 정책으로 맞춘다 |
| `latest/` | 현재 MVP primary 경로는 아님. 과거 초안 호환용 lifecycle만 유지 |
| 전체 | incomplete multipart upload는 7일 후 중단 |

`raw/` 원본은 재처리 근거이므로 바로 삭제하지 않는다. `processed/`와 `processed_agg/`는 대시보드와 분석 조회 가능성이 높아 더 오래 Standard에 둔다. DynamoDB LATEST/GRAPH#5M/HISTORY#STATE가 현재 상태와 최근 그래프의 hot store 역할을 하므로 S3 `latest/`를 Dashboard current state 경로로 사용하지 않는다.

## Public access 기준

Public access block은 켠다. 다른 VPC 또는 EKS workload가 접근해야 할 때도 S3를 public으로 열지 않고 IAM Role, S3 VPC Endpoint, bucket policy로 접근시킨다.

## Destroy 기준

MVP 환경에서는 `scripts/destroy/destroy-all.sh`가 비용 누수를 남기지 않도록 `data_bucket_force_destroy=true`를 기본값으로 둔다. 따라서 IoT Rule 테스트 객체와 versioned object가 남아 있어도 foundation destroy 시 버킷 내부 객체와 버전을 함께 삭제한다.

데이터 보존이 필요한 운영 환경으로 전환하면 `data_bucket_force_destroy=false`로 바꾸고, 별도 백업/반출 절차를 만든 뒤 foundation을 삭제한다.

## 실행

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/foundation
terraform init
terraform validate
terraform plan
terraform apply
```

삭제는 신중하게 수행한다. 이 root는 데이터와 영속 리소스를 관리하므로 일반적으로 `infra/hub`처럼 실험 종료 시 매번 destroy하지 않는다. 비용을 완전히 0으로 맞추는 전체 정리 시에는 `scripts/destroy/destroy-all.sh`가 이 root까지 삭제한다.

## 검증 결과

2026-05-04 기준 확인:

```text
terraform state list:
- aws_s3_bucket.data
- aws_s3_bucket_lifecycle_configuration.data
- aws_s3_bucket_ownership_controls.data
- aws_s3_bucket_public_access_block.data
- aws_s3_bucket_server_side_encryption_configuration.data
- aws_s3_bucket_versioning.data

terraform output data_bucket_name:
aegis-bucket-data

aws s3api get-bucket-versioning:
Status Enabled

aws s3api get-public-access-block:
BlockPublicAcls true
IgnorePublicAcls true
BlockPublicPolicy true
RestrictPublicBuckets true

aws s3api get-bucket-encryption:
SSEAlgorithm AES256

AMP Workspace:
removed from foundation Terraform on 2026-05-27
```
