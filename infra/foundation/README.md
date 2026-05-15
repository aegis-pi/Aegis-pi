# Foundation Layer

이 디렉터리는 Hub EKS 생명주기와 분리해야 하는 영속 리소스를 관리한다.

`infra/hub`는 비용 절감을 위해 자주 destroy할 수 있지만, 이 root의 리소스는 Hub EKS를 내렸다 올려도 유지한다.

## 현재 관리 리소스

- S3 데이터 버킷: `aegis-bucket-data`
- IoT Rule -> S3 raw 적재: `AEGIS_IoTRule_factory_a_raw_s3`
- AMP Workspace: `AEGIS-AMP-hub`
- ECR repository: `aegis/edge-agent`
- GitHub Actions OIDC provider와 ECR push role: `AEGIS-GitHubActions-ECRPush`

2026-05-08 기준 위 리소스는 검증 후 비용 정리를 위해 `scripts/destroy/destroy-all.sh`로 삭제했다. 이 디렉터리는 다음 rebuild 때 같은 기준으로 foundation 리소스를 다시 생성하는 Terraform source of truth다.

## 후속 후보 리소스

- IoT Core Thing, 인증서

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

M3 Issue 2 기준 ECR 대상은 smoke image 검증용 `edge-agent` 하나다. Lambda data processor는 zip 배포를 기본으로 하며, `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator` repository는 만들지 않는다.

M4에서 실제 데이터 플레인 이미지를 구현하면 `factory-a-log-adapter`, `edge-iot-publisher`, `dummy-data-generator`의 ECR repository naming과 lifecycle policy를 별도로 확정한다.

ArgoCD가 배포할 Helm values는 `sha-<7자리>` 태그를 배포 기준으로 삼는다. `main`과 `latest`는 빌드 확인과 수동 디버깅을 위한 이동 태그로만 사용한다.

Spoke K3s는 EKS managed node가 아니므로 EKS node role의 ECR pull 권한으로는 이미지를 받을 수 없다. M3 Issue 3~4에서 GitHub Actions push role과 Spoke K3s `imagePullSecret` 갱신 방식을 별도 연결한다.

## GitHub Actions OIDC / ECR Push Role

M3 Issue 3 기준 code repository의 GitHub Actions는 장기 AWS access key를 저장하지 않고 GitHub OIDC로 AWS role을 assume한다.

```text
OIDC provider: arn:aws:iam::611058323802:oidc-provider/token.actions.githubusercontent.com
role: arn:aws:iam::611058323802:role/AEGIS-GitHubActions-ECRPush
allowed repository subject: repo:aegis-pi/Aegis-pi:ref:refs/heads/main
allowed ECR repository: arn:aws:ecr:ap-south-1:611058323802:repository/aegis/edge-agent
workflow: .github/workflows/build-push.yaml
```

Role policy는 ECR authorization token 조회와 `aegis/edge-agent` repository image push에 필요한 권한만 허용한다. GitHub Actions가 Spoke K3s 또는 Hub EKS에 직접 `kubectl apply`하지 않는다는 CD 경계는 유지한다.

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

## AMP Workspace 기준

```text
alias: AEGIS-AMP-hub
last verified workspace id before destroy: ws-762fb9c1-ad1f-433d-991b-20f768186759
current state: deleted
terraform apply: 10 added, 0 changed, 0 destroyed
```

AMP Workspace는 `infra/foundation`에서 관리한다. Hub EKS를 비용 절감을 위해 destroy/recreate해도 메트릭 저장소의 생명주기를 EKS와 분리하기 위해서다.

Prometheus/Agent가 이 Workspace로 remote_write할 IAM/IRSA Role은 EKS OIDC provider에 묶이므로 `infra/hub`에서 관리한다.

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
processed/{dataset}/{factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
latest/{factory_id}/status.json
latest/{factory_id}/risk-score.json
```

## IoT Rule -> S3 raw 적재 기준

```text
rule: AEGIS_IoTRule_factory_a_raw_s3
topic filter: aegis/factory-a/+
target bucket: aegis-bucket-data
target key: raw/factory-a/${topic(3)}/yyyy=${parse_time("yyyy", timestamp(), "UTC")}/mm=${parse_time("MM", timestamp(), "UTC")}/dd=${parse_time("dd", timestamp(), "UTC")}/${get_or_default(message_id, newuuid())}.json
role: AEGIS-IAMRole-IoTRule-S3
policy scope: s3:PutObject to arn:aws:s3:::aegis-bucket-data/raw/factory-a/*
```

검증 결과:

```text
test topic: aegis/factory-a/sensor
test message_id: manual-20260506T014423Z-31668
test object: raw/factory-a/sensor/yyyy=2026/mm=05/dd=06/manual-20260506T014423Z-31668.json
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

terraform output amp_workspace_id:
ws-6a8853dc-0eb4-43e7-9b97-efade5b75765
```
