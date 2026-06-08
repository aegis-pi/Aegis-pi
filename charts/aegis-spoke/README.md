# Aegis Spoke Chart

이 Helm chart는 각 공장 Spoke에 Edge data-plane workload를 배포한다.

## factory-a 기준

`envs/factory-a/values.yaml`은 운영형 Raspberry Pi Spoke 기준값이다.

- namespace: `ai-apps`
- adapter: `factory-a-log-adapter`
- publisher: `edge-iot-publisher`
- snapshot uploader: `snapshot-uploader`
- shared outbox: PVC -> `/var/lib/aegis/outbox`
- snapshot source: node-local hostPath -> `/var/lib/safe-edge/snapshots`
- IoT Secret: `aws-iot-factory-a-cert` -> `/etc/aegis/iot`
- placement: `worker2` 우선 고정

초기에는 outbox PVC가 `ReadWriteOnce`이므로 adapter, publisher, snapshot-uploader를 같은 노드에 배치한다. factory-a MVP에서 snapshot-uploader는 worker1/worker2 DaemonSet이 아니라 `worker2` 단일 Deployment다.
이미지 태그는 GitHub Actions/ECR push 후 `sha-<7-char-git-sha>`로 갱신한다.

2026-06-08 배포 기준:

```text
edge-iot-publisher: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/edge-iot-publisher:sha-6d30ef2
snapshot-uploader: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/snapshot-uploader:sha-6d30ef2
```

## Render

```bash
helm template aegis-spoke charts/aegis-spoke \
  --namespace ai-apps \
  -f envs/factory-a/values.yaml
```
