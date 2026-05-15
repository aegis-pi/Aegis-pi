# Edge Agent

이 디렉터리는 `factory-a`에서 센서 및 시스템 상태를 수집해 표준 스키마로 변환하고 Hub로 전송하는 Edge Agent 코드를 둔다.

Data / Dashboard VPC 확장 기준에서는 Edge Agent가 센서값뿐 아니라 `system_status`, `device_status`, `workload_status`, `pipeline_heartbeat`도 IoT Core로 전송한다. 대시보드는 Spoke K3s, ArgoCD, EKS API, Tailscale 관리망을 직접 조회하지 않고 이 데이터가 반영된 latest status store를 읽는다.

## M3 기준 빌드 대상

M3 Issue 3에서는 실제 Edge Agent 기능 구현 전에 GitHub Actions -> ECR -> GitOps tag 갱신 흐름을 검증하기 위한 최소 HTTP smoke image를 이 디렉터리에서 빌드한다.

```text
Dockerfile: apps/edge-agent/Dockerfile
entrypoint: apps/edge-agent/edge_agent.py
port: 8080
health endpoints: /, /healthz, /readyz
target platform: linux/arm64
ECR repository: 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/edge-agent
```

GitHub Actions workflow는 `main` 브랜치에 `apps/edge-agent/**` 또는 `.github/workflows/build-push.yaml` 변경이 push될 때 ARM64 image를 빌드하고 ECR에 `sha-<7자리>`, `main`, `latest` 태그로 푸시한다.
