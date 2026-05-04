# Scripts

이 디렉터리는 구축, 검증, 보조 자동화에 사용하는 스크립트를 둔다.

인프라 자체는 Terraform에서 관리한다. 이 디렉터리의 Ansible/Hub 스크립트는 Terraform 이후 bootstrap, 설정, 소프트웨어 설치, 운영 검증을 담당한다.

현재 운영 스크립트:

Hub 실행 파일별 상세 설명은 `hub/README.md`를 따른다.

| 경로 | 내용 |
| --- | --- |
| `hub/run-hub.sh` | MFA OTP 입력 후 `infra/hub` Terraform apply, Ansible bootstrap, ArgoCD port-forward 순서 실행 |
| `hub/destroy-hub.sh` | MFA OTP 입력 후 `infra/hub` Terraform destroy 실행 |
| `hub/argocd-initial-password.sh` | MFA 세션 확인 후 Hub ArgoCD 초기 admin 비밀번호 조회 |
| `hub/argocd-port-forward.sh` | Hub ArgoCD UI 로컬 접근용 kubeconfig 갱신 및 port-forward 실행 |
| `ansible/inventory/hub_eks_dynamic.sh` | `infra/hub` Terraform output 기반 Hub EKS dynamic inventory |
| `ansible/playbooks/hub_argocd_bootstrap.yml` | Hub namespace, LimitRange, ArgoCD Helm 설치 및 검증 |
| `ansible/playbooks/hub_argocd_verify.yml` | Hub ArgoCD bootstrap 상태 확인 |

반복 점검 자동화는 `ansible/` 아래에 둔다.

이전에 사용한 `safe-edge-agent-watchdog.*` fencing 구성은 AI snapshot PVC 제거 후 폐기했다. 현재 AI failover는 Longhorn RWO snapshot PVC에 의존하지 않으므로 worker2 reboot fencing을 사용하지 않는다.
