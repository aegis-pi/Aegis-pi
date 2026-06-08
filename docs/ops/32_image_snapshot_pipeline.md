# Image Snapshot Pipeline

상태: source of truth
기준일: 2026-06-08

## 목적

factory-a Safe-Edge AI event snapshot 이미지를 S3에 저장하고, IoT Core와 DataProcessor에는 이미지 바이너리가 아니라 S3 참조 metadata만 전달한다.

## 현재 배포 상태

factory-a MVP 기준:

```text
snapshot-uploader: worker2 단일 Deployment
edge-iot-publisher: worker2 Deployment
outbox: Longhorn RWO PVC /var/lib/aegis/outbox
snapshot source: worker2 hostPath /var/lib/safe-edge/snapshots
presigner endpoint: https://pp604cwuk8.execute-api.ap-south-1.amazonaws.com/image-snapshot/presign
```

배포 이미지:

```text
edge-iot-publisher: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/edge-iot-publisher:sha-6d30ef2
snapshot-uploader: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/snapshot-uploader:sha-6d30ef2
```

Presigner Lambda:

```text
Lambda: AEGIS-Lambda-SnapshotPresigner
Allowed factory: factory-a
Max file size: 5242880 bytes
URL expiry: 300 seconds
PRESIGN_SHARED_TOKEN: empty, auth disabled
```

## 동작 흐름

```text
Safe-Edge AI event
  -> /var/lib/safe-edge/snapshots/{timestamp}_event_{EVENT}.jpg
  -> snapshot-uploader polling scan
  -> SnapshotPresigner API 호출
  -> AEGIS-Lambda-SnapshotPresigner가 presigned S3 PUT URL 생성
  -> snapshot-uploader가 이미지 bytes를 S3 image_snapshot/ prefix에 PUT
  -> snapshot-uploader가 outbox에 image_snapshot metadata JSON 기록
  -> edge-iot-publisher가 aegis/factory-a/image_snapshot 으로 metadata publish
  -> IoT Rule이 raw metadata S3 저장 + DataProcessor 호출
  -> DataProcessor가 processed metadata S3 저장 + DynamoDB latest_image_snapshot 갱신
```

`image_snapshot`은 `factory_state` 안의 optional field가 아니라 별도 source type이다. 이벤트가 없으면 `image_snapshot` 메시지도 생성되지 않는다.

## Snapshot 감지 방식

현재는 filesystem event trigger가 아니라 polling 방식이다.

```text
scan dir: /var/lib/safe-edge/snapshots
scan interval: 10 seconds
extensions: .jpg, .jpeg, .png
state file: /var/lib/aegis/outbox/.snapshot-uploader-state.json
```

업로드 완료 파일은 state에 path, size, mtime, sha256, s3_key를 기록한다. 다음 scan에서 동일 파일은 skip한다.

`snapshot-uploader`는 snapshot hostPath를 read-only로 mount한다. worker2 로컬 원본 파일은 삭제하지 않는다. 로컬 파일 정리는 Safe-Edge snapshot cleanup/retention 정책이 담당한다.

## S3 경로

원본 이미지:

```text
s3://aegis-bucket-data/image_snapshot/factory_id=factory-a/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{filename}
```

raw metadata:

```text
s3://aegis-bucket-data/raw/factory-a/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json
```

raw 경로에는 factory-a MVP에서 `hh` 파티션을 추가하지 않는다.

processed metadata:

```text
s3://aegis-bucket-data/processed/factory-a/image_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json
```

DynamoDB:

```text
pk=FACTORY#factory-a
sk=LATEST
latest_image_snapshot
last_image_snapshot_at
```

## 확인 명령

K3s 배포 상태:

```bash
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n ai-apps get deploy,pod -l app.kubernetes.io/instance=aegis-spoke -o wide
```

snapshot-uploader 로그:

```bash
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n ai-apps logs deploy/aegis-spoke-snapshot-uploader --tail=100
```

publisher 로그:

```bash
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n ai-apps logs deploy/aegis-spoke-edge-iot-publisher --tail=100
```

Presigner Lambda 상태:

```bash
aws lambda get-function-configuration \
  --region ap-south-1 \
  --function-name AEGIS-Lambda-SnapshotPresigner
```

DataProcessor 상태:

```bash
aws lambda get-function-configuration \
  --region ap-south-1 \
  --function-name AEGIS-Lambda-DataProcessor
```

IoT Rule:

```bash
aws iot get-topic-rule \
  --region ap-south-1 \
  --rule-name AEGIS_IoTRule_factory_a_raw_s3
```

DynamoDB latest:

```bash
aws dynamodb get-item \
  --region ap-south-1 \
  --table-name AEGIS-DynamoDB-FactoryStatus \
  --key '{"pk":{"S":"FACTORY#factory-a"},"sk":{"S":"LATEST"}}' \
  --projection-expression 'updated_at,last_image_snapshot_at,latest_image_snapshot,last_factory_state_at,last_infra_state_at'
```

최근 raw metadata:

```bash
aws s3api list-objects-v2 \
  --bucket aegis-bucket-data \
  --prefix raw/factory-a/image_snapshot/yyyy=2026/mm=06/dd=08/ \
  --max-items 5
```

최근 processed metadata:

```bash
aws s3api list-objects-v2 \
  --bucket aegis-bucket-data \
  --prefix processed/factory-a/image_snapshot/yyyy=2026/mm=06/dd=08/ \
  --max-items 5
```

원본 이미지 ACL 확인:

```bash
aws s3api get-object-acl \
  --bucket aegis-bucket-data \
  --key image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=11/260608114226_event_FIRE.jpg
```

정상 기준은 owner `FULL_CONTROL` grant만 있고 public-read grant가 없는 것이다.

## 최근 검증 결과

2026-06-08 배포 후 확인:

```text
snapshot-uploader rollout: success
edge-iot-publisher rollout: success
original image S3: exists, image/jpeg, SSE AES256
raw image_snapshot metadata: exists, no hh partition
processed image_snapshot metadata: exists, hh partition
DynamoDB LATEST.latest_image_snapshot: updated
DataProcessor Lambda recent Errors: 0
SnapshotPresigner Lambda recent Errors: 0
```

예시 최신 DynamoDB image reference:

```text
event_type=FIRE
source_timestamp=2026-06-08T11:42:26Z
s3_key=image_snapshot/factory_id=factory-a/yyyy=2026/mm=06/dd=08/hh=11/260608114226_event_FIRE.jpg
```

## 운영 주의사항

- Raspberry Pi에는 장기 AWS access key를 저장하지 않는다.
- S3 object는 public-read로 만들지 않는다.
- Presigner API는 현재 token 없이 동작한다. 운영 보안을 강화하려면 `PRESIGN_SHARED_TOKEN`을 설정하고 K3s `snapshot-uploader-presign` Secret의 `token` 값을 맞춘다.
- worker1 failover snapshot upload는 MVP 범위가 아니다. Longhorn RWO outbox PVC 때문에 snapshot-uploader는 worker2 단일 Deployment로 운영한다.
- 기존 worker2 snapshot backlog는 state에 없으면 최초 배포 시 업로드된다. state에 기록된 파일은 재업로드하지 않는다.
- snapshot-uploader는 원본 로컬 파일을 삭제하지 않는다.
