# RiskAlertDispatcher 운영 기준

상태: 구현/테스트/운영 배포 검증 완료
기준일: 2026-06-04
관련 코드: `apps/risk-alert-dispatcher/`, `infra/data-pipeline/risk_alert_dispatcher.tf`

---

## 개요

RiskAlertDispatcher는 S3 `processed/`에 저장되는 factory state snapshot과 cloud infra fast/slow snapshot을 S3 ObjectCreated 이벤트로 받아 `warning`/`danger` 조건을 판단하고 Slack으로 알림을 보낸다.

이 컴포넌트는 `infra/data-pipeline` Terraform root에 포함된다. 따라서 `scripts/build/build-data-pipe.sh`로 생성되고 `scripts/destroy/destroy-data-pipe.sh`로 삭제된다.

2026-06-04 기준 Cloud alert는 specific 원인을 먼저 평가하고, 같은 원인을 포괄하는 generic section alert는 fallback으로만 사용한다. 예를 들어 Lambda error가 있으면 `data_pipeline_lambda_errors`만 생성하고 `data_pipeline_warning`은 생성하지 않는다. Pod warning이 있으면 `pods_warning`만 생성하고 `eks_management_warning`은 생성하지 않는다. 서로 독립적인 문제, 예를 들어 nodes와 pods 문제가 동시에 있으면 두 specific alert는 모두 유지한다.

```text
S3 ObjectCreated
  processed/factory-a/state_snapshot/*.json
  processed/factory-b/state_snapshot/*.json
  processed/factory-c/state_snapshot/*.json
  processed/cloud_infra/fast/*.json
  processed/cloud_infra/slow/*.json
    -> Lambda AEGIS-Lambda-RiskAlertDispatcher
      -> snapshot parse
      -> warning/danger rule evaluate
      -> warning confirmation when required
      -> DynamoDB dedupe/cooldown reserve
      -> Slack webhook routing
      -> DynamoDB Slack send result update
```

---

## 배포 리소스

Terraform 리소스는 `infra/data-pipeline/risk_alert_dispatcher.tf`에 있다.

| 리소스 | 내용 |
| --- | --- |
| `aws_lambda_function.risk_alert_dispatcher` | S3 processed snapshot alert dispatcher |
| `aws_iam_role.risk_alert_dispatcher` | Lambda execution role |
| `aws_iam_role_policy.risk_alert_dispatcher` | S3 read, DynamoDB update, Secrets Manager read, CloudWatch Logs |
| `aws_cloudwatch_log_group.risk_alert_dispatcher` | `/aws/lambda/AEGIS-Lambda-RiskAlertDispatcher`, retention 30일 |
| `aws_lambda_permission.risk_alert_dispatcher_s3` | S3가 Lambda를 invoke하도록 허용 |
| `aws_s3_bucket_notification.data_processed_alerts` | processed prefix 5개에 ObjectCreated trigger 연결 |
| `aws_secretsmanager_secret.risk_alert_slack_webhook` | cloud/default Slack webhook secret metadata |
| `aws_secretsmanager_secret.risk_alert_slack_webhook_factory` | factory-a/b/c Slack webhook secret metadata |

Secrets Manager secret 값은 Terraform state에 넣지 않는다. Terraform은 secret metadata만 관리하고, 값은 build script가 로컬 파일에서 `file://`로 주입한다.

---

## Slack Webhook Routing

Lambda는 `alert.scope` 기준으로 Slack webhook을 선택한다.

| Scope | Slack secret env | Secrets Manager name |
| --- | --- | --- |
| `cloud-infra` | `SLACK_WEBHOOK_SECRET_CLOUD` | `AEGIS/foundation-mvp/risk-alert/slack-webhook-url` |
| `factory-a` | `SLACK_WEBHOOK_SECRET_FACTORY_A` | `AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-a` |
| `factory-b` | `SLACK_WEBHOOK_SECRET_FACTORY_B` | `AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-b` |
| `factory-c` | `SLACK_WEBHOOK_SECRET_FACTORY_C` | `AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-c` |

기존 cloud/default secret 이름은 유지한다. Slack 채널 변경은 Slack 쪽 webhook 설정 또는 로컬 secret 파일 교체 후 build script 재실행으로 처리한다.

로컬 secret 파일 기본 경로:

```text
/home/vicbear/Aegis/.secrets/aegis_slack_webhook_url
/home/vicbear/Aegis/.secrets/aegis_slack_webhook_factory_a
/home/vicbear/Aegis/.secrets/aegis_slack_webhook_factory_b
/home/vicbear/Aegis/.secrets/aegis_slack_webhook_factory_c
```

권장 권한:

```bash
chmod 600 /home/vicbear/Aegis/.secrets/aegis_slack_webhook_*
```

주의: webhook URL 원문은 채팅, 문서, repo, Terraform 변수, Terraform state에 넣지 않는다.

---

## DynamoDB Dedupe

Alert 중복 제어는 foundation DynamoDB 테이블 `AEGIS-DynamoDB-FactoryStatus`를 사용한다. data-pipeline은 이 테이블을 data source로 참조한다.

Alert state item:

```text
pk = ALERT#{scope}
sk = {severity}#{reason}#{status}
```

예시:

```text
pk = ALERT#factory-c
sk = danger#nodes_all_not_ready#state_snapshot
```

저장 필드:

| 필드 | 내용 |
| --- | --- |
| `scope` | `factory-a`, `factory-b`, `factory-c`, `cloud-infra` |
| `source_type` | `factory_state_snapshot`, `cloud_infra_fast`, `cloud_infra_slow` |
| `severity` | `warning` 또는 `danger` |
| `reason` | alert fingerprint reason |
| `status` | pipeline/cloud status |
| `last_sent_at` | 마지막 Slack 전송 epoch seconds |
| `last_observed_at` | 마지막 관측 epoch seconds |
| `cooldown_until` | 재전송 제한 해제 epoch seconds |
| `last_score` | factory risk score |
| `last_source_key` | 원본 S3 object key |
| `last_source_updated_at` | snapshot updated timestamp |
| `last_slack_status` | `pending`, `sent`, `failed` |
| `last_slack_error` | Slack 전송 실패 메시지 |
| `ttl` | alert state TTL |

현재 기본 cooldown:

```text
factory warning = 900s
factory danger  = 300s
cloud warning   = 900s
cloud danger    = 300s
```

즉 `danger`도 cooldown이 적용된다. 같은 `pk/sk`는 cooldown 동안 Slack 재전송을 skip한다. 또한 `last_source_updated_at`보다 오래된 snapshot은 stale로 보고 skip한다.

Cloud warning 중 일부는 Slack 전송 전 연속 관측 확인을 먼저 수행한다. 확인 상태 item은 기존 alert cooldown item과 분리해서 저장한다.

```text
pk = ALERT#cloud-infra
sk = OBSERVATION#{severity}#{reason}#{status}
```

첫 관측은 `awaiting_confirmation`으로 skip하고, 같은 window 안에서 더 최신 snapshot이 필요한 횟수만큼 관측되면 cooldown 예약과 Slack 전송 단계로 넘어간다.

---

## Alert Rule 기준

### Factory state snapshot

대상 key:

```text
processed/{factory-id}/state_snapshot/**/*.json
```

주요 판단:

- `risk.level`이 `warning` 또는 `danger`
- `pipeline_status.status`가 `warning` 또는 `critical`
- `risk.top_causes[]`에 `severity=danger`
- `risk.gates[]`에 `severity=danger`

`pipeline_status`가 warning/critical이면 freshness 관련 weighted cause와 gate는 별도 알림으로 보내지 않고
`pipeline_status` 알림 1건으로 통합한다. 같은 snapshot에 node/AI/device 등 독립 위험 원인이 있으면 해당 알림은 유지한다.

Factory의 비-pipeline 알림은 현재 pipeline 상태를 Slack 메시지에는 표시하지만, fingerprint에는 포함하지 않는다.
따라서 동일한 node/AI/device 원인은 pipeline 상태가 normal/warning/critical로 바뀌어도
`{severity}#{reason}#state_snapshot` 하나의 cooldown을 공유한다. `pipeline_status` 알림만 warning/critical 상태를 fingerprint에 유지한다.

### Cloud infra fast snapshot

대상 key:

```text
processed/cloud_infra/fast/**/*.json
```

주요 판단:

- `backend_runtime`, `data_pipeline` status가 normal이 아님
- `factory_freshness`는 Cloud fast snapshot과 대시보드 참고 데이터에 유지되며, 2026-06-04 AWS 배포본 기준 Cloud `overall_status`에도 포함
- Lambda `errors_5m > 0`
- Lambda `throttles_5m > 0`
- DynamoDB read/write throttle events가 있음
- ALB unhealthy host가 있음
- collector error가 있음

Cloud fast의 `backend_runtime_warning`, `data_pipeline_warning`, `data_pipeline_lambda_errors`는
90초 안에 서로 다른 snapshot에서 2회 연속 관측되어야 Slack 알림을 보낸다.
ALB unhealthy host, Lambda/DynamoDB throttle, collector error, danger/critical은 즉시 알림을 보낸다.

Cloud fast alert는 Lambda error/throttle, DynamoDB throttle, ALB unhealthy host 같은 specific 원인을 먼저 평가한다.
같은 section에 specific 알림이 있으면 `backend_runtime_warning` 또는 `data_pipeline_warning` generic 알림은 만들지 않는다.
section status가 non-normal이지만 specific rule로 원인을 설명할 수 없을 때만 generic section 알림을 fallback으로 전송한다.

중복 억제 예시:

| 실제 원인 | 생성 alert | 억제 alert |
| --- | --- | --- |
| Lambda error | `data_pipeline_lambda_errors` | `data_pipeline_warning` |
| Lambda throttle | `data_pipeline_lambda_throttles` | `data_pipeline_warning` |
| DynamoDB throttle | `dynamodb_throttles` | `data_pipeline_warning` |
| ALB unhealthy host | `alb_unhealthy_hosts` | `backend_runtime_warning` |
| 원인 미식별 backend warning | `backend_runtime_warning` | 없음 |

### Cloud infra slow snapshot

대상 key:

```text
processed/cloud_infra/slow/**/*.json
```

주요 판단:

- EKS management/storage freshness status가 normal이 아님
- EKS cluster/nodegroup이 `ACTIVE`가 아님
- autoscaling healthy instances가 desired capacity보다 작음
- nodes/pods/argocd status가 normal이 아님
- collector error가 있음

collector error가 있으면 같은 원인에서 파생된 `eks_management_unknown`, `nodes_unknown`, `pods_unknown`, `argocd_unknown` 알림은 억제하고 대표 collector error 알림만 전송한다. 예를 들어 Kubernetes API 401 오류는 `kubernetes_api_unauthorized` 1건으로 전송된다. 단, storage freshness나 EKS cluster inactive처럼 독립적으로 판단 가능한 이상은 별도 알림으로 유지한다.

Pod phase 기준은 Failed pod 1개면 warning, 2개 이상이면 critical이다.
`eks_management_warning`과 `pods_warning`은 450초 안에 2회 연속 관측되어야 Slack 알림을 보낸다.
cluster/nodegroup/ASG 이상과 danger/critical은 즉시 알림을 보낸다.

Cloud slow alert도 EKS cluster/nodegroup/ASG, nodes, pods, argocd specific 원인을 먼저 평가한다.
EKS specific 알림이 있으면 같은 원인을 포괄하는 `eks_management_*` generic 알림은 억제한다.
nodes와 pods처럼 서로 독립적인 specific 문제는 모두 유지하며, specific으로 설명되지 않는 EKS section 이상만 generic fallback으로 전송한다.

중복 억제 예시:

| 실제 원인 | 생성 alert | 억제 alert |
| --- | --- | --- |
| Failed pod 1개 | `pods_warning` | `eks_management_warning` |
| Failed pod 2개 이상 | `pods_critical` -> `danger#pods_critical#slow` | `eks_management_critical` |
| nodes와 pods 동시 warning | `nodes_warning`, `pods_warning` | `eks_management_warning` |
| 원인 미식별 EKS warning | `eks_management_warning` | 없음 |

연속 관측 상태는 기존 alert cooldown item과 분리된
`pk=ALERT#cloud-infra`, `sk=OBSERVATION#{severity}#{reason}#{status}` item에 저장한다.
첫 warning snapshot은 `awaiting_confirmation`으로 skip하고, 확인된 warning부터 기존 cooldown 예약을 수행한다.

---

## Slack 메시지 포맷

Slack 메시지는 한글 운영자용 템플릿을 사용한다.

```text
━━━━━━━━━━━━━━━━━━━━━━
AEGIS Alert | 위험 알림

무엇이 문제인가요?
factory-c에서 위험(DANGER) 조건이 감지되었습니다.

현재 상태
- 심각도: 위험(DANGER)
- 공장/대상: factory-c
- 수집/스냅샷: 공장 상태 스냅샷
- 상태: normal
- 위험 점수: 49

왜 발생했나요?
- 원인: nodes_all_not_ready

주요 원인
1. 항목: node_status
   원인: nodes_all_not_ready
   현재 값: 0/2
   영향도: 50
   등급: 위험(DANGER)

확인할 데이터
processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=02/x.json

중복 알림 제어
동일 조건은 cooldown 동안 재전송되지 않습니다.
━━━━━━━━━━━━━━━━━━━━━━
```

---

## Build

일반 build:

```bash
scripts/build/build-data-pipe.sh [MFA_OTP]
```

build script 동작:

1. `infra/data-pipeline` Terraform init/validate/plan/apply
2. cloud/factory-a/factory-b/factory-c webhook 파일이 있으면 Secrets Manager에 값 주입
3. 파일이 없으면 경고만 출력하고 Terraform apply는 성공 상태로 유지

다른 secret 파일을 쓰는 경우:

```bash
AEGIS_RISK_ALERT_SLACK_WEBHOOK_FILE=/path/to/cloud-webhook \
AEGIS_RISK_ALERT_SLACK_WEBHOOK_FACTORY_A_FILE=/path/to/factory-a-webhook \
AEGIS_RISK_ALERT_SLACK_WEBHOOK_FACTORY_B_FILE=/path/to/factory-b-webhook \
AEGIS_RISK_ALERT_SLACK_WEBHOOK_FACTORY_C_FILE=/path/to/factory-c-webhook \
scripts/build/build-data-pipe.sh [MFA_OTP]
```

---

## Destroy

RiskAlertDispatcher는 data-pipeline 생명주기에 포함된다.

```bash
scripts/destroy/destroy-data-pipe.sh [MFA_OTP]
```

삭제 대상:

- RiskAlertDispatcher Lambda
- Lambda execution IAM role/policy
- CloudWatch Log Group
- S3 processed ObjectCreated notification
- Lambda invoke permission
- Slack webhook Secrets Manager secret metadata

DynamoDB table과 S3 bucket은 foundation 리소스이므로 data-pipeline destroy에서 삭제하지 않는다. DynamoDB alert state item과 S3 processed test object는 foundation 데이터로 남을 수 있다.

---

## 검증 기록

2026-06-04 Cloud alert 중복 억제 배포 검증:

- Cloud generic/specific 중복 억제 구현 완료
- `python -m pytest apps/risk-alert-dispatcher/tests -q`: 28 passed
- `python -m pytest apps/cloud-infra-collector/tests -q`: 14 passed
- 배포 zip 재생성: `/tmp/lambda_risk_alert_dispatcher.zip`
  - 포함: `lambda_function.py`, `alert_dispatcher/*.py`
  - 제외: `tests/`, `__pycache__/`, `*.pyc`
- 배포:
  - 대상: `AEGIS-Lambda-RiskAlertDispatcher`
  - 명령: `aws lambda update-function-code --function-name AEGIS-Lambda-RiskAlertDispatcher --zip-file fileb:///tmp/lambda_risk_alert_dispatcher.zip`
  - 배포 기준 epoch ms: `1780553108921`
  - `LastModified`: `2026-06-04T06:05:39.000+0000`
  - `State`: `Active`
  - `LastUpdateStatus`: `Successful`
  - `CodeSha256`: `/GosrfobqNAMqmWFfeTDPky/ij2LmsPQF8b83e7fDrw=`
- 로컬 zip SHA256과 Lambda `CodeSha256` 일치 확인
- 배포 이후 CloudWatch ERROR 로그 확인:
  - log group: `/aws/lambda/AEGIS-Lambda-RiskAlertDispatcher`
  - start time: `1780553108921`
  - 결과: ERROR event 없음
- 운영 snapshot 재처리는 수행하지 않음
- 로컬 evaluate 대표 검증:
  - fast: `data_pipeline_lambda_errors`, `dynamodb_throttles`, `alb_unhealthy_hosts` 생성, `data_pipeline_warning`/`backend_runtime_warning` 억제
  - slow: `nodes_warning`, `pods_warning` 생성, `eks_management_warning` 억제

2026-06-04 Lambda zip 동기화 후 상태:

- ap-south-1 실제 Lambda zip을 다운로드해 repo 관리 Lambda 12개와 로컬 배포 포함 파일을 비교했다.
- `AEGIS-Lambda-RiskAlertDispatcher` 배포 상태: `State=Active`, `LastUpdateStatus=Successful`, `CodeSha256=/GosrfobqNAMqmWFfeTDPky/ij2LmsPQF8b83e7fDrw=`
- CloudInfraFastCollector/SlowCollector 배포 상태: `CodeSha256=/FapoibjVCVSbJMI8n/LeJx/0K6UrE3U6MazSzCUezE=`
- 로컬 실행 로직은 AWS 배포본 기준으로 동기화했다.
- 검증: `apps/data-processor`, `apps/graph-metrics-aggregator`, `apps/cloud-infra-collector`, `apps/risk-alert-dispatcher` 테스트 80 passed, `apps/daily-report-generator` 테스트 15 passed.

2026-06-02 검증:

- MFA env 확인: `AWS_SESSION_TOKEN` set
- STS identity: account `611058323802`, user `student05`
- MFA context 포함 IAM simulation: 필요한 Lambda/IAM/S3/DynamoDB/Secrets Manager 권한 allowed
- `pytest apps/risk-alert-dispatcher/tests`: 10 passed
- `python -m compileall apps/risk-alert-dispatcher`: 통과
- `terraform validate`: 통과
- RiskAlertDispatcher 관련 Terraform targeted plan: `No changes`
- S3 notification 5개 prefix 확인
- Lambda state: `Active`, update `Successful`
- Secrets Manager factory-a/b/c current version 확인
- E2E factory-c danger sample:
  - S3 key: `processed/factory-c/state_snapshot/yyyy=2026/mm=06/dd=02/hh=06/risk-alert-dispatcher-test-061450.json`
  - DynamoDB item: `pk=ALERT#factory-c`, `sk=danger#nodes_all_not_ready#state_snapshot`
  - `last_slack_status=sent`
  - 같은 event 재호출 시 `cooldown_or_stale_snapshot` skip 확인

검증 중 DynamoDB `UpdateExpression` 예약어(`scope`, `ttl`) 문제가 발견되어 alert state attribute를 ExpressionAttributeNames alias로 처리했다.

---

## 운영 점검 명령

Lambda 상태:

```bash
aws lambda get-function-configuration \
  --function-name AEGIS-Lambda-RiskAlertDispatcher \
  --query '{State:State,LastUpdateStatus:LastUpdateStatus,EnvironmentKeys:keys(Environment.Variables)}'
```

S3 notification:

```bash
aws s3api get-bucket-notification-configuration \
  --bucket aegis-bucket-data
```

Alert dedupe item:

```bash
aws dynamodb get-item \
  --table-name AEGIS-DynamoDB-FactoryStatus \
  --key '{"pk":{"S":"ALERT#factory-c"},"sk":{"S":"danger#nodes_all_not_ready#state_snapshot"}}'
```

Secret metadata 확인:

```bash
aws secretsmanager describe-secret \
  --secret-id AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-a
```

주의: `get-secret-value`는 운영 중 필요한 경우에만 사용하고 출력 로그에 webhook URL이 남지 않도록 한다.
