# Ansible Playbooks

이 디렉터리는 `factory-a` 운영 점검과 Hub EKS bootstrap 자동화를 위한 Ansible playbook을 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `02_start_test.yml` | master에 접속해 K3s, MetalLB, Longhorn, ArgoCD, monitoring, ai-apps 상태를 검증하고 evidence를 생성 |
| `hub_argocd_bootstrap.yml` | Hub EKS kubeconfig 갱신, namespace/LimitRange 적용, IRSA ServiceAccount 적용, ArgoCD Helm 설치/업그레이드, Ready 검증 |
| `hub_argocd_verify.yml` | Hub namespace, ArgoCD pod, Helm release, IRSA ServiceAccount annotation 상태 확인 |
| `hub_prometheus_agent_bootstrap.yml` | `observability/prometheus-agent`로 Prometheus Agent와 AMP remote_write 설정 적용 |
| `hub_prometheus_agent_verify.yml` | Prometheus Agent pod, IRSA annotation, remote_write 로그 상태 확인 |
| `hub_grafana_bootstrap.yml` | 내부 Grafana Helm release, AMP datasource, admin Secret, ClusterIP 설정 적용 |
| `hub_grafana_verify.yml` | Grafana pod, IRSA annotation, ClusterIP, Grafana API 경유 AMP query 확인 |
| `hub_aws_load_balancer_controller_bootstrap.yml` | AWS Load Balancer Controller ServiceAccount/CRD/Helm release 적용 |
| `hub_aws_load_balancer_controller_verify.yml` | AWS Load Balancer Controller Deployment, IRSA annotation, subnet discovery, recent log 확인 |
| `hub_admin_ingress_bootstrap.yml` | ACM 발급 상태 확인 후 선택적으로 ArgoCD/Grafana HTTPS Ingress와 Route53 CNAME 적용 |
| `hub_admin_ingress_verify.yml` | Admin Ingress 활성화 시 shared ALB, ClusterIP 유지, HTTPS endpoint 확인 |
| `hub_admin_ingress_cleanup.yml` | Hub destroy 전 Admin Ingress, Route53 CNAME, controller 생성 ALB 정리 |

## 기준

- 초기 자동화는 상태 수집과 검증 중심으로 유지한다.
- 물리 LAN 제거, 전원 차단 같은 장애 유발은 수동 절차로 둔다.
- playbook 결과는 `scripts/ansible/evidence/`에 저장한다.
- Hub bootstrap playbook은 SSH가 아니라 `localhost`에서 EKS Kubernetes API를 대상으로 실행한다.
- Hub ArgoCD Helm release가 이미 `deployed` 상태이고 chart version이 같으면 Helm upgrade를 건너뛴다. 강제 재적용은 `-e argocd_force_upgrade=true`로 실행한다.
- Admin Ingress는 `ADMIN_UI_INGRESS_ENABLED=true`일 때만 적용한다. 기본값은 인증서 발급 전 ALB 비용과 build 실패를 피하기 위해 비활성화다.
