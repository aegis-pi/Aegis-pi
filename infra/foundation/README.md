# Foundation Layer

이 디렉터리는 Hub EKS 생명주기와 분리해야 하는 영속 리소스를 관리한다.

`infra/hub`는 비용 절감을 위해 자주 destroy할 수 있지만, 이 root의 리소스는 Hub EKS를 내렸다 올려도 유지한다.

## 현재 관리 리소스

- S3 데이터 버킷: `aegis-bucket-data` 생성 완료

## 후속 후보 리소스

- ECR 이미지 저장소
- AMP workspace
- IoT Core Thing, 인증서, Rule

## S3 데이터 버킷 기준

```text
bucket: aegis-bucket-data
region: ap-south-1
versioning: enabled
encryption: SSE-S3 (AES256)
public access block: enabled
terraform apply: 6 added, 0 changed, 0 destroyed
```

Prefix 기준:

```text
raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
processed/{dataset}/{factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
latest/{factory_id}/status.json
latest/{factory_id}/risk-score.json
```

공장별 prefix를 분리한다. 이후 `factory-b`, `factory-c`가 추가되어도 권한, lifecycle, Athena/Glue partition, 장애 분석 기준을 독립적으로 다루기 쉽기 때문이다.

## Lifecycle 기준

| Prefix | 기준 |
| --- | --- |
| `raw/` | 90일 후 Glacier Instant Retrieval 전환 |
| `processed/` | 365일 후 Standard-IA 전환 |
| `latest/` | current object 삭제 없음, noncurrent version은 30일 후 삭제 |
| 전체 | incomplete multipart upload는 7일 후 중단 |

`raw/` 원본은 재처리 근거이므로 바로 삭제하지 않는다. `processed/`는 대시보드와 분석 조회 가능성이 높아 더 오래 Standard에 둔다. `latest/`는 애플리케이션이 현재 상태 객체를 덮어쓰는 영역이므로 current object lifecycle 삭제를 걸지 않는다.

## Public access 기준

Public access block은 켠다. 다른 VPC 또는 EKS workload가 접근해야 할 때도 S3를 public으로 열지 않고 IAM Role, S3 VPC Endpoint, bucket policy로 접근시킨다.

## 실행

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/foundation
terraform init
terraform validate
terraform plan
terraform apply
```

삭제는 신중하게 수행한다. 이 root는 데이터와 영속 리소스를 관리하므로 `infra/hub`처럼 실험 종료 시 매번 destroy하지 않는다.

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
```
