# Aegis Spoke Chart

이 Helm chart는 각 공장 Spoke에 Edge data-plane workload를 배포한다.

## factory-a 기준

`envs/factory-a/values.yaml`은 운영형 Raspberry Pi Spoke 기준값이다.

- namespace: `ai-apps`
- adapter: `factory-a-log-adapter`
- publisher: `edge-iot-publisher`
- shared outbox: PVC -> `/var/lib/aegis/outbox`
- IoT Secret: `aws-iot-factory-a-cert` -> `/etc/aegis/iot`
- placement: `worker2` 우선 고정

초기에는 outbox PVC가 `ReadWriteOnce`이므로 adapter와 publisher를 같은 노드에 배치한다.
이미지 태그는 GitHub Actions/ECR push 후 `sha-<7-char-git-sha>`로 갱신한다.

## Render

```bash
helm template aegis-spoke charts/aegis-spoke \
  --namespace ai-apps \
  -f envs/factory-a/values.yaml
```
