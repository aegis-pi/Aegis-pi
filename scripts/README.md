# Scripts

이 디렉터리는 구축, 검증, 보조 자동화에 사용하는 스크립트를 둔다.

인프라 자체는 Terraform에서 관리한다. 이 디렉터리의 Ansible/Hub 스크립트는 Terraform 이후 bootstrap, 설정, 소프트웨어 설치, 운영 검증을 담당한다.

현재 운영 스크립트:

Hub 실행 파일별 상세 설명은 `hub/README.md`를 따른다.
전체 생성 진입점은 `build/README.md`, 전체 삭제 진입점은 `destroy/README.md`를 따른다.
새 리소스를 추가하거나 기존 리소스 생명주기를 바꾸면 `build/`와 `destroy/`를 함께 업데이트한다.

| 경로 | 내용 |
| --- | --- |
| `build/build-all.sh` | foundation, hub, IoT/K3s Secret 생성 순서 실행 |
| `destroy/destroy-all.sh` | IoT/K3s Secret, hub, foundation 전체 삭제 순서 실행 |
| `hub/run-hub.sh` | `build/build-hub.sh` 실행 후 ArgoCD port-forward까지 연결하는 호환 wrapper |
| `hub/destroy-hub.sh` | `destroy/destroy-hub.sh`를 호출하는 호환 wrapper |
| `ops/argocd-initial-password.sh` | MFA 세션 확인 후 Hub ArgoCD 초기 admin 비밀번호 조회 |
| `ops/argocd-port-forward.sh` | Hub ArgoCD UI 로컬 접근용 kubeconfig 갱신 및 port-forward 실행 |
| `lib/aws-mfa.sh` | AWS MFA session 공통 함수 |
| `lib/terraform.sh` | Terraform apply/destroy 공통 함수 |
| `config/defaults.sh` | scripts 기본값 source |
| `iot/register-thing.sh` | IoT Thing, Policy, certificate/key 발급 템플릿. 출력은 `secret/`에 저장 |
| `iot/register-k3s-secret.sh` | IoT 인증서 파일을 K3s master에 전송하고 Kubernetes Secret 생성/갱신 |
| `iot/cleanup-thing.sh` | CLI로 만든 IoT Thing, Policy, certificate 정리 템플릿 |
| `ansible/inventory/hub_eks_dynamic.sh` | `infra/hub` Terraform output 기반 Hub EKS dynamic inventory |
| `ansible/playbooks/hub_argocd_bootstrap.yml` | Hub namespace, LimitRange, ArgoCD Helm 설치 및 검증 |
| `ansible/playbooks/hub_argocd_verify.yml` | Hub ArgoCD bootstrap 상태 확인 |

반복 점검 자동화는 `ansible/` 아래에 둔다.

이전에 사용한 `safe-edge-agent-watchdog.*` fencing 구성은 AI snapshot PVC 제거 후 폐기했다. 현재 AI failover는 Longhorn RWO snapshot PVC에 의존하지 않으므로 worker2 reboot fencing을 사용하지 않는다.
