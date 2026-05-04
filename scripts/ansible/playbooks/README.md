# Ansible Playbooks

이 디렉터리는 `factory-a` 운영 점검과 Hub EKS bootstrap 자동화를 위한 Ansible playbook을 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `02_start_test.yml` | master에 접속해 K3s, MetalLB, Longhorn, ArgoCD, monitoring, ai-apps 상태를 검증하고 evidence를 생성 |
| `hub_argocd_bootstrap.yml` | Hub EKS kubeconfig 갱신, namespace/LimitRange 적용, ArgoCD Helm 설치/업그레이드, Ready 검증 |
| `hub_argocd_verify.yml` | Hub namespace, ArgoCD pod, Helm release 상태 확인 |

## 기준

- 초기 자동화는 상태 수집과 검증 중심으로 유지한다.
- 물리 LAN 제거, 전원 차단 같은 장애 유발은 수동 절차로 둔다.
- playbook 결과는 `scripts/ansible/evidence/`에 저장한다.
- Hub bootstrap playbook은 SSH가 아니라 `localhost`에서 EKS Kubernetes API를 대상으로 실행한다.
