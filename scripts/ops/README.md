# scripts/ops

상태: source of truth
기준일: 2026-06-08

## 목적

일상 운영에서 자주 사용하는 보조 스크립트를 모아둔 디렉터리다.
Hub 재생성/삭제 진입점은 `scripts/build/`, `scripts/destroy/`이며, 이 디렉터리는 UI 접근, 자격증명 확인, dummy generator 관리 등 운영 편의 목적만 다룬다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `manage-dummy-generators.sh` | factory-b/c VM dummy generator systemd service 시작/정지 |
| `argocd-port-forward.sh` | Hub EKS ArgoCD UI 포트포워드 (Public ALB 없을 때 로컬 접근용) |
| `grafana-port-forward.sh` | Hub EKS Grafana UI 포트포워드 (Public ALB 없을 때 로컬 접근용) |
| `argocd-initial-password.sh` | ArgoCD admin 초기 비밀번호 출력 |
| `grafana-admin-password.sh` | Grafana admin 비밀번호 출력 |
| `export-hub-ui-credentials.sh` | ArgoCD/Grafana 자격증명을 환경변수 형식으로 출력 |
| `admin-ui-nameservers.sh` | Route53 Hosted Zone NS 레코드 출력 (도메인 NS 위임 확인용) |
| `refresh-factory-a-ecr-pull-secret.sh` | factory-a K3s `imagePullSecret` 갱신 |
| `register-snapshot-presigner-secret.sh` | factory-a K3s `snapshot-uploader-presign` Secret 등록 |
| `check-spoke-publisher-safety.sh` | Hub-only reconnect 전후 Spoke `edge-iot-publisher` 중복 pod/rollout strategy 점검 |
| `copy-public-image-to-ecr.py` | Public Docker 이미지를 ECR로 복사 (smoke image 준비용) |
| `dummy-generators.env` | factory-b/c dummy generator SSH 접속 기본 설정 (`AEGIS_DUMMY_GENERATORS_ENV`로 경로 재지정 가능) |

## 주요 사용 예시

```bash
# 데이터 수집을 별도로 중단했던 경우 factory-b/c dummy generator 시작
scripts/ops/manage-dummy-generators.sh start factory-b
scripts/ops/manage-dummy-generators.sh start factory-c

# 양쪽 동시 시작
scripts/ops/manage-dummy-generators.sh start

# ArgoCD UI 포트포워드 (ALB 없을 때)
scripts/ops/argocd-port-forward.sh

# Grafana UI 포트포워드 (ALB 없을 때)
scripts/ops/grafana-port-forward.sh

# Route53 NS 확인 (ACM 검증 전 도메인 위임 확인)
scripts/ops/admin-ui-nameservers.sh

# Hub-only reconnect 전후 publisher 안전성 확인
scripts/ops/check-spoke-publisher-safety.sh
scripts/ops/check-spoke-publisher-safety.sh factory-b factory-c

# snapshot-uploader presign endpoint Secret 등록
PRESIGN_ENDPOINT="https://example.execute-api.ap-south-1.amazonaws.com/image-snapshot/presign" \
PRESIGN_TOKEN="optional-shared-token" \
scripts/ops/register-snapshot-presigner-secret.sh

# 2026-06-08 factory-a 배포 endpoint
PRESIGN_ENDPOINT="https://pp604cwuk8.execute-api.ap-south-1.amazonaws.com/image-snapshot/presign" \
PRESIGN_TOKEN="" \
scripts/ops/register-snapshot-presigner-secret.sh
```

`register-snapshot-presigner-secret.sh`는 factory-a master SSH를 사용한다. SSH 인증이 불가능하고 로컬 kubeconfig가 있으면 다음 방식으로 같은 Secret을 직접 적용할 수 있다.

```bash
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n ai-apps create secret generic snapshot-uploader-presign \
  --from-literal=endpoint=https://pp604cwuk8.execute-api.ap-south-1.amazonaws.com/image-snapshot/presign \
  --from-literal=token= \
  --dry-run=client -o yaml | \
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig apply -f -
```

## 참고

- Hub-only 데이터 수집 유지 모드에서는 dummy generator를 정지하거나 다시 시작하지 않는다.
- 데이터 수집까지 중단할 때는 `scripts/destroy/stop-dummy-generators.sh`를 사용한다.
- dummy generator 설정 파일은 `dummy-generators.env`이며, `scripts/destroy/stop-dummy-generators.sh`와 이 디렉터리의 `manage-dummy-generators.sh`가 공유한다.
