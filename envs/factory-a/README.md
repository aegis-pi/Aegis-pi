# Factory A Environment

이 디렉터리는 운영형 Spoke인 `factory-a`에 적용할 환경별 values와 배포 설정을 둔다.

`values.yaml`은 Hub ArgoCD ApplicationSet이 `charts/aegis-spoke`를 렌더링할 때 사용하는 factory-a override다.

현재 기준:

- data-plane namespace는 기존 IoT Secret을 재사용하기 위해 `ai-apps`다.
- `factory-a-log-adapter`, `edge-iot-publisher`, `snapshot-uploader`는 `worker2`에 배치한다.
- 세 workload는 같은 Longhorn PVC를 `/var/lib/aegis/outbox`로 마운트한다.
- `snapshot-uploader`는 Safe-Edge snapshot hostPath `/var/lib/safe-edge/snapshots`를 read-only로 마운트한다.
- `snapshot-uploader`는 worker2 단일 Deployment다. Longhorn RWO outbox PVC 때문에 worker1/worker2 DaemonSet 배포는 MVP 범위에서 제외한다.
- IoT endpoint와 인증서 파일은 `aws-iot-factory-a-cert` Secret의 `endpoint.txt`, `certificate.pem.crt`, `private.pem.key`, `AmazonRootCA1.pem`에서 읽는다.
- snapshot presigner endpoint는 `snapshot-uploader-presign` Secret의 `endpoint` key에서 읽는다. `token` key는 optional이다.

2026-06-08 배포 이미지:

```text
edge-iot-publisher: sha-6d30ef2
snapshot-uploader: sha-6d30ef2
```
