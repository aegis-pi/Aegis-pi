# Image Snapshot S3 Upload Plan

상태: deployed and verified
기준일: 2026-06-08

## 목적

factory-a Safe-Edge에서 생성되는 AI snapshot 이미지를 S3에 저장하고, IoT Core에는 이미지 바이너리가 아니라 S3 참조 metadata JSON만 전송한다.

현재 Safe-Edge snapshot은 `safe-edge-integrated-ai` Pod 내부 `/app/snapshots`에 보이며, 실제 저장 위치는 Pod가 실행 중인 노드의 node-local hostPath다.

```text
Pod path:  /app/snapshots
Host path: /var/lib/safe-edge/snapshots
Current node: worker2
```

확인된 현재 상태:

```text
safe-edge-integrated-ai Pod: worker2 Running
worker2:/var/lib/safe-edge/snapshots 이미지 65개 확인
최신 파일 예시: 260608094235_event_FALLEN.jpg
파일 형식: JPEG 640x480
```

이 경로는 Longhorn PVC가 아니다. 따라서 snapshot을 읽는 workload는 EKS Hub가 아니라 factory-a K3s에서 실행되어야 한다. factory-a MVP에서는 Longhorn RWO outbox PVC 리스크를 피하기 위해 worker2 단일 Deployment로 배포했다.

2026-06-08 배포 결과:

```text
snapshot-uploader: aegis-spoke-snapshot-uploader, worker2 Running
edge-iot-publisher: aegis-spoke-edge-iot-publisher, sha-6d30ef2 Running
snapshot-uploader image: sha-6d30ef2
presigner endpoint: https://pp604cwuk8.execute-api.ap-south-1.amazonaws.com/image-snapshot/presign
DataProcessor Lambda: image_snapshot 처리 배포 완료
```

## 결정

이미지 원본 S3 경로는 아래 형태로 고정한다.

```text
s3://aegis-bucket-data/image_snapshot/factory_id={factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{filename}
```

예시:

```text
s3://aegis-bucket-data/image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg
```

선택 이유:

- 이미지 원본은 기존 JSON telemetry와 성격이 다르므로 top-level prefix를 분리한다.
- `factory_id=factory-a` 형태는 파티션 의미가 명확하다.
- 이미지 lifecycle, 접근 권한, 비용 분석을 JSON raw/processed와 별도로 관리하기 쉽다.
- Dashboard/API가 최근 snapshot 목록을 조회할 때 prefix가 단순하다.

IoT Core로 전송하는 metadata JSON은 기존 raw/processed 데이터 흐름을 따른다.

```text
raw/{factory_id}/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
processed/{factory_id}/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

## 목표 아키텍처

```text
factory-a worker2
  /var/lib/safe-edge/snapshots/*.jpg
    -> snapshot-uploader Deployment
       1. 새 이미지 감지
       2. Hub API/Lambda에 presigned PUT URL 요청
       3. S3 image_snapshot/factory_id=... 경로에 이미지 업로드
       4. metadata JSON을 /var/lib/aegis/outbox 에 atomic write
    -> edge-iot-publisher
       5. image_snapshot metadata JSON을 IoT Core로 publish
    -> IoT Rule
       6. metadata raw JSON 저장
       7. Lambda DataProcessor 호출
    -> DataProcessor
       8. processed image_snapshot metadata 저장
       9. DynamoDB LATEST에 최신 snapshot 참조 반영
```

Hub EKS의 역할:

```text
GitHub Actions -> ECR image build/push
Hub ArgoCD/ApplicationSet -> factory-a K3s에 snapshot-uploader 배포
Hub API/Lambda -> presigned PUT URL 발급
```

factory-a K3s의 역할:

```text
snapshot-uploader Deployment 실행
edge-iot-publisher 실행
node-local snapshot 파일 접근
IoT Core MQTT publish
```

## Metadata 계약

`snapshot-uploader`가 S3 이미지 업로드에 성공한 뒤 아래 JSON을 `/var/lib/aegis/outbox`에 기록한다. 이후 `edge-iot-publisher`가 이 파일을 IoT Core로 publish한다.

```json
{
  "schema_version": "0.1.0",
  "message_id": "factory-a:image_snapshot:worker2:2026-06-08T09:42:35Z",
  "factory_id": "factory-a",
  "node_id": "worker2",
  "environment_type": "physical-rpi",
  "input_module_type": "camera",
  "source_type": "image_snapshot",
  "source_timestamp": "2026-06-08T09:42:35Z",
  "published_at": null,
  "data_plane_instance_id": "snapshot-uploader-worker2",
  "payload": {
    "event_type": "FALLEN",
    "content_type": "image/jpeg",
    "size_bytes": 60345,
    "sha256": "hex-encoded-sha256",
    "s3_bucket": "aegis-bucket-data",
    "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
    "local_path": "/var/lib/safe-edge/snapshots/260608094235_event_FALLEN.jpg",
    "upload_status": "uploaded"
  }
}
```

필수 필드:

| 필드 | 설명 |
| --- | --- |
| `schema_version` | 기존 canonical JSON과 같은 schema version |
| `message_id` | `{factory_id}:image_snapshot:{node_id}:{source_timestamp}` |
| `factory_id` | `factory-a` |
| `node_id` | snapshot 파일이 발견된 노드 |
| `source_type` | `image_snapshot` |
| `source_timestamp` | 파일 mtime 또는 파일명에서 파싱한 캡처 시각 |
| `payload.event_type` | 파일명에서 파싱한 이벤트 타입. 예: `FALLEN` |
| `payload.content_type` | `image/jpeg` 또는 `image/png` |
| `payload.size_bytes` | 업로드한 파일 크기 |
| `payload.sha256` | 업로드 무결성 확인용 SHA-256 |
| `payload.s3_bucket` | `aegis-bucket-data` |
| `payload.s3_key` | 이미지 원본 S3 key |

## Presigned URL 발급 API

### 요청

`snapshot-uploader`는 이미지를 업로드하기 전 Hub API/Lambda에 presigned URL을 요청한다.

```json
{
  "factory_id": "factory-a",
  "node_id": "worker2",
  "filename": "260608094235_event_FALLEN.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 60345,
  "sha256": "hex-encoded-sha256",
  "source_timestamp": "2026-06-08T09:42:35Z",
  "event_type": "FALLEN"
}
```

### 응답

```json
{
  "method": "PUT",
  "upload_url": "https://...",
  "expires_in": 300,
  "s3_bucket": "aegis-bucket-data",
  "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
  "required_headers": {
    "Content-Type": "image/jpeg"
  }
}
```

### API 검증 기준

- `factory_id`는 허용 목록에 있어야 한다.
- `filename`은 basename만 허용하고 `/`, `..`를 거부한다.
- content type은 `image/jpeg`, `image/png`만 허용한다.
- 파일 크기는 상한을 둔다. MVP 기본값은 5MiB.
- S3 key는 API 서버가 생성한다. 디바이스가 임의 S3 key를 지정하지 않는다.
- presigned URL 만료는 300초를 기본값으로 둔다.

## 구현 범위

### 1. edge-iot-publisher 확장

파일:

```text
apps/edge-iot-publisher/edge_iot_publisher.py
apps/edge-iot-publisher/tests/test_edge_iot_publisher.py
```

현재:

```python
VALID_SOURCE_TYPES = {"factory_state", "infra_state"}
```

변경:

```python
VALID_SOURCE_TYPES = {"factory_state", "infra_state", "image_snapshot"}
```

기대 동작:

```text
source_type=image_snapshot
topic=aegis/{factory_id}/image_snapshot
```

기존 required field 구조는 유지한다. image metadata도 canonical envelope 형식을 따른다.

### 2. snapshot-uploader 앱 추가

신규 경로:

```text
apps/snapshot-uploader/
  Dockerfile
  README.md
  snapshot_uploader.py
  tests/
    test_snapshot_uploader.py
```

역할:

- `/var/lib/safe-edge/snapshots`에서 `*.jpg`, `*.jpeg`, `*.png` scan
- 파일명 또는 mtime 기준으로 `source_timestamp` 결정
- 파일명에서 이벤트 타입 파싱
- SHA-256 계산
- presigned URL 발급 API 호출
- presigned PUT URL로 S3 업로드
- 업로드 성공 후 metadata JSON을 `/var/lib/aegis/outbox`에 atomic write
- 이미 업로드한 파일은 local state로 skip

환경 변수:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `AEGIS_FACTORY_ID` | `factory-a` | factory id |
| `AEGIS_ENVIRONMENT_TYPE` | `physical-rpi` | environment type |
| `AEGIS_INPUT_MODULE_TYPE` | `camera` | input module type |
| `AEGIS_SNAPSHOT_DIR` | `/var/lib/safe-edge/snapshots` | hostPath snapshot mount |
| `AEGIS_OUTBOX_DIR` | `/var/lib/aegis/outbox` | 기존 publisher outbox |
| `AEGIS_PRESIGN_ENDPOINT` | required | presigned URL 발급 endpoint |
| `AEGIS_UPLOAD_STATE_PATH` | `/var/lib/aegis/outbox/.snapshot-uploader-state.json` | upload marker |
| `AEGIS_SCAN_INTERVAL_SECONDS` | `10` | scan interval |
| `AEGIS_MAX_FILE_BYTES` | `5242880` | 업로드 최대 크기 |
| `AEGIS_DATA_PLANE_INSTANCE_ID` | `snapshot-uploader-{hostname}` | metadata field |

atomic write 기준:

```text
/var/lib/aegis/outbox/tmp/{message_id}.json.tmp
  -> fsync/write close
  -> /var/lib/aegis/outbox/{message_id}.json
```

state 파일에는 최소한 아래 정보를 저장한다.

```json
{
  "/var/lib/safe-edge/snapshots/260608094235_event_FALLEN.jpg": {
    "size_bytes": 60345,
    "mtime_ns": 1780882955270612976,
    "sha256": "...",
    "s3_key": "image_snapshot/factory_id=factory-a/...",
    "uploaded_at": "2026-06-08T00:45:00Z"
  }
}
```

### 3. ECR repository 추가

파일:

```text
infra/foundation/ecr.tf
infra/foundation/variables.tf
infra/foundation/outputs.tf
infra/foundation/github_actions_ecr_push.tf
infra/foundation/terraform.tfvars.example
```

추가 repository:

```text
aegis/snapshot-uploader
```

ECR 설정은 기존 repository와 같은 기준을 따른다.

```text
scan_on_push: 기존 변수 기준
encryption: AES256
untagged expire: 기존 기준
sha-tagged keep: 기존 기준
GitHub Actions role push 권한 포함
```

### 4. GitHub Actions build matrix 추가

파일:

```text
.github/workflows/build-push.yaml
```

trigger path 추가:

```yaml
- apps/snapshot-uploader/**
```

matrix 추가:

```yaml
- name: snapshot-uploader
  context: apps/snapshot-uploader
  dockerfile: apps/snapshot-uploader/Dockerfile
  repository: aegis/snapshot-uploader
```

태그 기준은 기존과 동일하다.

```text
sha-<7-char>
main
latest
```

### 5. Helm chart Deployment 추가

파일:

```text
charts/aegis-spoke/templates/snapshot-uploader-deployment.yaml
charts/aegis-spoke/values.yaml
envs/factory-a/values.yaml
```

factory-a MVP 형태:

```text
kind: Deployment
namespace: ai-apps
replicas: 1
node: worker2
```

mount:

```text
snapshot hostPath:
  host: /var/lib/safe-edge/snapshots
  container: /var/lib/safe-edge/snapshots
  readOnly: true

outbox PVC:
  claim: aegis-spoke-outbox
  container: /var/lib/aegis/outbox
  readWrite
```

node selection:

```yaml
nodeSelector:
  kubernetes.io/hostname: worker2
```

주의:

- snapshot은 node-local hostPath이므로 Deployment 1개는 worker2 파일만 본다.
- 이번 배포는 factory-a MVP로 worker2 단일 uploader만 운영한다.
- outbox는 기존 Longhorn RWO PVC를 공유한다. DaemonSet 다중 노드 mount는 이번 범위에서 제외한다.

RWO outbox 이슈 대안:

1. MVP: snapshot-uploader를 worker2 Deployment로 먼저 배포한다.
2. Failover까지 포함: outbox도 hostPath로 전환하거나 노드별 outbox와 publisher DaemonSet 구조로 변경한다.
3. 장기: RWX storage 또는 NFS-like shared path를 도입한다.

현재 `aegis-spoke-outbox`는 Longhorn RWO PVC다. MVP는 `worker2` 단일 Deployment로 시작하고, failover 대응은 후속 이슈로 분리한다.

### 6. DataProcessor 확장

파일:

```text
apps/data-processor/lambda_function.py
apps/data-processor/processor/envelope.py
apps/data-processor/processor/normalizer.py
apps/data-processor/processor/dynamo.py
apps/data-processor/processor/s3_writer.py
apps/data-processor/tests/
```

처리 추가:

- `image_snapshot` envelope parse 허용
- payload 정규화
- S3 processed metadata 저장
- DynamoDB `LATEST.latest_image_snapshot` 갱신
- `HISTORY#STATE` snapshot에 최신 image snapshot 참조 포함

권장 DynamoDB LATEST 필드:

```json
{
  "latest_image_snapshot": {
    "event_type": "FALLEN",
    "source_timestamp": "2026-06-08T09:42:35Z",
    "processed_at": "2026-06-08T09:42:40Z",
    "s3_bucket": "aegis-bucket-data",
    "s3_key": "image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=09/260608094235_event_FALLEN.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 60345,
    "sha256": "..."
  }
}
```

S3 processed key:

```text
processed/{factory_id}/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

### 7. IoT Rule 확인

파일:

```text
infra/data-pipeline/iot_rule.tf
```

확인 사항:

- topic SQL이 `aegis/factory-a/+`, `aegis/factory-b/+`, `aegis/factory-c/+` 형태면 `image_snapshot`은 자동 포함된다.
- SQL 또는 Lambda code에 source type whitelist가 있으면 `image_snapshot`을 추가한다.
- raw S3 metadata 저장 경로가 source type을 포함하는지 확인한다.

## 검증 계획

### 1. Unit Tests

snapshot-uploader:

```text
파일명 event_type 파싱
mtime/source_timestamp 결정
S3 key 생성
sha256 계산
presigned URL 요청 payload 생성
presigned PUT 성공/실패 처리
metadata envelope 생성
atomic outbox write
upload state skip
max size 초과 skip
unsupported extension skip
```

edge-iot-publisher:

```text
image_snapshot source_type validation 통과
topic_for -> aegis/factory-a/image_snapshot
required fields 누락 시 quarantine
```

data-processor:

```text
image_snapshot envelope parse
payload normalization
DynamoDB update expression 검증
S3 processed body/key 검증
```

### 2. Local Rendering

```bash
helm template aegis-spoke charts/aegis-spoke \
  --namespace ai-apps \
  -f envs/factory-a/values.yaml
```

확인:

```text
snapshot-uploader manifest render 성공
worker2 nodeSelector 반영
snapshot hostPath readOnly mount 반영
outbox mount 반영
image repository/tag 반영
```

### 3. ECR Build

GitHub Actions `Build and Push Edge Images` workflow를 수동 실행하거나 main push로 실행한다.

확인:

```text
611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/snapshot-uploader:sha-xxxxxxx
611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/snapshot-uploader:main
```

### 4. Presigned URL API

로컬 또는 AWS Lambda에서 테스트한다.

```text
valid request -> 200 + upload_url + s3_key
invalid factory_id -> 403/400
invalid filename path traversal -> 400
invalid content_type -> 400
too large -> 400
expired URL upload -> S3 reject
```

### 5. Factory-A Deployment

Hub ArgoCD sync 후 factory-a master에서 확인한다.

```bash
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get deploy -o wide
kubectl -n ai-apps logs -l app.kubernetes.io/component=snapshot-uploader --tail=100
```

현재 snapshot 확인:

```bash
ssh minsoo@10.10.10.12
find /var/lib/safe-edge/snapshots -maxdepth 1 -type f -name '*.jpg' | tail
```

### 6. S3 Image Upload

확인 경로:

```text
s3://aegis-bucket-data/image_snapshot/factory_id=factory-a/yyyy=YYYY/mm=MM/dd=DD/hh=HH/
```

검증:

```text
object exists
content-type=image/jpeg
size matches local file
sha256 metadata 또는 metadata JSON의 sha256과 일치
```

### 7. Outbox Metadata

```bash
kubectl -n ai-apps exec deploy/aegis-spoke-edge-iot-publisher -- \
  find /var/lib/aegis/outbox -maxdepth 1 -type f -name '*.json' | head
```

publisher가 빠르게 처리하면 outbox에 남지 않을 수 있으므로 publisher log도 확인한다.

```bash
kubectl -n ai-apps logs deploy/aegis-spoke-edge-iot-publisher --tail=100
```

기대 로그:

```text
published ... -> aegis/factory-a/image_snapshot
```

### 8. IoT Raw Metadata

S3 raw metadata 경로:

```text
raw/factory-a/image_snapshot/yyyy=YYYY/mm=MM/dd=DD/{message_id}.json
```

확인:

```text
source_type=image_snapshot
payload.s3_key=image_snapshot/factory_id=factory-a/...
```

### 9. DataProcessor Processed Metadata

S3 processed 경로:

```text
processed/factory-a/image_snapshot/yyyy=YYYY/mm=MM/dd=DD/hh=HH/{message_id}.json
```

DynamoDB:

```text
pk=FACTORY#factory-a
sk=LATEST
latest_image_snapshot.s3_key exists
```

### 10. Failover Scenario

목표:

```text
worker2 정상: worker2 snapshot upload
worker1 failover: worker1 snapshot upload
```

절차:

1. worker2 정상 상태에서 snapshot 업로드 확인
2. 기존 failover runbook으로 AI Pod를 worker1에 이동하는 경우 snapshot upload는 MVP 범위에서 보류
3. failback 후 worker2 파일 업로드가 다시 정상인지 확인

주의:

- MVP는 worker2 단일 uploader로 운영하고, failover snapshot upload는 별도 storage 재설계 후 진행한다.

## 구현 및 배포 결과

완료:

1. `edge-iot-publisher`에 `image_snapshot` source type 허용
2. `edge-iot-publisher` unit test 추가
3. `snapshot-uploader` 앱 구현 및 ECR build-push
4. `snapshot-presigner` Lambda 구현 및 API Gateway 배포
5. `infra/foundation`에 `aegis/snapshot-uploader` ECR repository 추가/apply
6. `infra/data-pipeline`에 SnapshotPresigner API/Lambda 추가/apply
7. Helm chart에 worker2 단일 `snapshot-uploader` Deployment 추가
8. DataProcessor image_snapshot metadata 처리 추가 및 Lambda 업데이트
9. factory-a K3s `snapshot-uploader-presign` Secret 생성
10. factory-a에 `edge-iot-publisher:sha-6d30ef2`, `snapshot-uploader:sha-6d30ef2` 배포
11. factory-a end-to-end 검증 완료
12. `docs/ops/32_image_snapshot_pipeline.md` 운영 runbook 추가

검증 완료:

```text
Python unit tests: edge-iot-publisher, snapshot-uploader, snapshot-presigner, data-processor OK
Terraform validate: infra/foundation, infra/data-pipeline OK
Helm template: OK
ECR image tags: sha-6d30ef2/main/latest 확인
K3s rollout: snapshot-uploader, edge-iot-publisher success
S3 original image: image_snapshot/ prefix 존재, image/jpeg, SSE AES256
S3 raw metadata: raw/factory-a/image_snapshot/yyyy=.../mm=.../dd=.../{message_id}.json
S3 processed metadata: processed/factory-a/image_snapshot/yyyy=.../mm=.../dd=.../hh=.../{message_id}.json
DynamoDB: LATEST.latest_image_snapshot 갱신
Lambda metrics: DataProcessor/SnapshotPresigner recent Errors = 0
```

## Open Questions

1. failover까지 지원하려면 `aegis-spoke-outbox` Longhorn RWO PVC를 대체하거나 노드별 outbox/publisher 구조를 재설계해야 한다.
2. worker1 snapshot upload support는 후속 과제로 분리한다.
3. Dashboard에서 이미지를 보여줄 때 S3 object를 직접 public으로 열지, backend에서 presigned GET URL을 발급할지 결정해야 한다. 기본 방침은 presigned GET이다.
4. 이미지 cloud lifecycle은 별도 정책이 필요하다. MVP 이후 7일 또는 30일 중 비용 기준으로 결정한다.
5. 운영 보안을 강화하려면 SnapshotPresigner `PRESIGN_SHARED_TOKEN`과 K3s Secret `snapshot-uploader-presign/token`을 설정한다.

## Non-Goals

- 이미지 바이너리를 IoT Core JSON payload에 base64로 넣지 않는다.
- S3 object를 public-read로 만들지 않는다.
- Raspberry Pi에 장기 AWS access key를 저장하지 않는다.
- EKS Hub에서 snapshot-uploader Pod를 실행하지 않는다. EKS Hub는 배포 제어 plane이고, uploader는 factory-a K3s에서 실행한다.
- 기존 Safe-Edge AI 앱 이미지를 수정하지 않는다. snapshot 파일을 읽는 별도 uploader로 확장한다.
