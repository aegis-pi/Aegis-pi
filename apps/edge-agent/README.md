# Edge Agent Smoke Image

이 디렉터리는 현재 실제 Edge Agent 로직이 아니라 M3 GitHub Actions -> ECR build/push 검증용 HTTP smoke image를 둔다.

2026-05-15 기준 실제 Edge data-plane 로직은 M4에서 아래처럼 분리한다.

```text
factory-a-log-adapter
  raw/log/status -> canonical JSON -> local spool/outbox

edge-iot-publisher
  local spool/outbox canonical JSON -> AWS IoT Core
```

대시보드는 Spoke K3s, ArgoCD, EKS API, Tailscale 관리망을 직접 조회하지 않고 이 데이터가 반영된 DynamoDB LATEST/HISTORY와 S3 processed를 읽는다.

## M3 기준 빌드 대상

M3 Issue 3에서는 실제 Edge data-plane 기능 구현 전에 GitHub Actions -> ECR push 흐름을 검증하기 위한 최소 HTTP smoke image를 이 디렉터리에서 빌드했다.

```text
Dockerfile: apps/edge-agent/Dockerfile
entrypoint: apps/edge-agent/edge_agent.py
port: 8080
health endpoints: /, /healthz, /readyz
target platform: linux/arm64
ECR repository: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/edge-agent
```

GitHub Actions workflow는 `main` 브랜치에 `apps/edge-agent/**` 또는 `.github/workflows/build-push.yaml` 변경이 push될 때 ARM64 image를 빌드하고 ECR에 `sha-<7자리>`, `main`, `latest` 태그로 푸시한다.

이 image tag를 GitOps values에 자동 반영하는 M3 Issue 6~8은 실제 adapter/publisher 로직이 확정될 때까지 보류한다.
