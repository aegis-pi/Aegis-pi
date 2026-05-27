# Scripts

이 디렉터리는 구축, 검증, 보조 자동화에 사용하는 스크립트를 둔다.

인프라 자체는 Terraform에서 관리한다. 이 디렉터리의 Ansible/Hub 스크립트는 Terraform 이후 bootstrap, 설정, 소프트웨어 설치, 운영 검증을 담당한다.

현재 운영 스크립트:

Hub 실행 파일별 상세 설명은 `hub/README.md`를 따른다.
전체 생성 진입점은 `build/README.md`, 전체 삭제 진입점은 `destroy/README.md`를 따른다.
새 리소스를 추가하거나 기존 리소스 생명주기를 바꾸면 `build/`와 `destroy/`를 함께 업데이트한다.

| 경로 | 내용 |
| --- | --- |
| `build/build-all.sh` | 기본 Hub 생성 실행. `--foundation`, `--admin-ui-after-ns`, `--iot`로 4단계 선택 실행 |
| `build/build-admin-ui-after-ns.sh` | Gabia NS 입력 후 ACM 발급 대기와 Admin UI HTTPS Ingress 활성화 |
| `build/connect-hub-tailscale-ui.sh` | Hub ArgoCD/Grafana Tailscale UI Service 연결 및 검증. ALB/Admin UI HTTPS를 쓰면 선택 실행 |
| `build/register-spoke-factory-a.sh` | 기존 IoT Secret을 유지하고 `factory-a` Hub ArgoCD cluster 등록, GitOps ApplicationSet 적용, app sync 수행 |
| `build/register-spoke-factory-b.sh` | 기존 IoT Secret을 유지하고 `factory-b` Hub ArgoCD cluster 등록, GitOps ApplicationSet 적용, app sync 수행 |
| `build/register-spoke-factory-c.sh` | 기존 IoT Secret을 유지하고 `factory-c` Hub ArgoCD cluster 등록, GitOps ApplicationSet 적용, app sync 수행 |
| `build/build-reporting.sh` | `apps/daily-report-generator` Lambda package를 만들고 `infra/reporting` Terraform apply를 실행 |
| `destroy/stop-dummy-generators.sh` | Hub 삭제 전 factory-b/c VM worker dummy generator systemd service 정지. legacy local publisher unit이 있으면 함께 정지 |
| `destroy/destroy-reporting.sh` | daily factory report Scheduler/Step Functions/Lambda/IAM/Log Group 제거 |
| `destroy/destroy-all.sh` | 기본 Hub 삭제 실행. `DESTROY_IOT=true`, `DESTROY_FOUNDATION=true`로 삭제 범위 확장 |
| `hub/run-hub.sh` | `build/build-hub.sh` 실행 후 ArgoCD port-forward까지 연결하는 호환 wrapper |
| `hub/destroy-hub.sh` | `destroy/destroy-hub.sh`를 호출하는 호환 wrapper |
| `ops/argocd-initial-password.sh` | MFA 세션 확인 후 Hub ArgoCD 초기 admin 비밀번호 조회 |
| `ops/argocd-port-forward.sh` | Hub ArgoCD UI 로컬 접근용 kubeconfig 갱신 및 port-forward 실행 |
| `ops/grafana-admin-password.sh` | MFA 세션 확인 후 Hub 내부 Grafana admin 비밀번호 조회 |
| `ops/grafana-port-forward.sh` | Hub 내부 Grafana UI 로컬 접근용 kubeconfig 갱신 및 port-forward 실행 |
| `ops/export-hub-ui-credentials.sh` | Hub ArgoCD/Grafana 초기 접속 정보를 `secret/hub-ui-credentials.txt`에 저장 |
| `ops/copy-public-image-to-ecr.py` | Docker Hub public image의 단일 platform manifest/blob을 ECR repository로 복사 |
| `ops/refresh-factory-a-ecr-pull-secret.sh` | factory-a K3s namespace에 ECR pull용 `docker-registry` Secret 생성/갱신 |
| `ops/admin-ui-nameservers.sh` | Terraform output 기준 Gabia 위임용 Route53 NS 파일 생성 |
| `ops/manage-dummy-generators.sh` | factory-b/c VM worker의 local dummy generator systemd service start/stop/status 보조. `ops/dummy-generators.env`에서 접속 정보를 읽고 master를 ProxyJump로 사용 |
| `lib/aws-mfa.sh` | AWS MFA session 공통 함수 |
| `lib/terraform.sh` | Terraform apply/destroy 공통 함수 |
| `config/defaults.sh` | scripts 기본값 source |
| `iot/register-thing.sh` | IoT Thing, Policy, certificate/key 발급 템플릿. 출력은 `secret/`에 저장 |
| `iot/register-k3s-secret.sh` | IoT 인증서 파일을 K3s master에 전송하고 Kubernetes Secret 생성/갱신 |
| `iot/cleanup-thing.sh` | CLI로 만든 IoT Thing, Policy, certificate 정리 템플릿 |
| `ansible/inventory/hub_eks_dynamic.sh` | `infra/hub` Terraform output 기반 Hub EKS dynamic inventory |
| `ansible/playbooks/hub_argocd_bootstrap.yml` | Hub namespace, LimitRange, ArgoCD Helm 설치 및 검증 |
| `ansible/playbooks/hub_argocd_verify.yml` | Hub ArgoCD bootstrap 상태 확인 |
| `ansible/playbooks/hub_prometheus_agent_bootstrap.yml` | Hub Prometheus Agent와 AMP remote_write 설정 |
| `ansible/playbooks/hub_prometheus_agent_verify.yml` | Hub Prometheus Agent와 AMP remote_write 상태 확인 |
| `ansible/playbooks/hub_grafana_bootstrap.yml` | Hub 내부 Grafana와 AMP datasource 설정 |
| `ansible/playbooks/hub_grafana_verify.yml` | Hub 내부 Grafana와 AMP datasource query 상태 확인 |
| `ansible/playbooks/hub_aws_load_balancer_controller_bootstrap.yml` | AWS Load Balancer Controller 설치 |
| `ansible/playbooks/hub_aws_load_balancer_controller_verify.yml` | AWS Load Balancer Controller와 IRSA 검증 |
| `ansible/playbooks/hub_admin_ingress_bootstrap.yml` | Admin UI HTTPS Ingress 선택 적용 |
| `ansible/playbooks/hub_admin_ingress_verify.yml` | Admin UI HTTPS Ingress 검증 |
| `ansible/playbooks/hub_admin_ingress_cleanup.yml` | Hub destroy 전 Admin Ingress/ALB 정리 |
| `ansible/playbooks/hub_tailscale_bootstrap.yml` | Hub Tailscale Operator, 선택된 factory egress, Tailscale UI Service, ArgoCD cluster Secret 복구. env로 UI와 Spoke 등록을 분리 실행 가능 |
| `ansible/playbooks/hub_tailscale_verify.yml` | Hub Tailscale Operator/proxy, UI, 선택된 factory K3s API, ArgoCD cluster Secret 검증 |
| `ansible/playbooks/hub_aegis_spoke_applicationset_bootstrap.yml` | GitOps repo URL 기준 AEGIS Spoke ApplicationSet 적용 |
| `ansible/playbooks/hub_aegis_spoke_applicationset_verify.yml` | AEGIS Spoke ApplicationSet과 factory-a Application 대상 검증 |

반복 점검 자동화는 `ansible/` 아래에 둔다.

이전에 사용한 `safe-edge-agent-watchdog.*` fencing 구성은 AI snapshot PVC 제거 후 폐기했다. 현재 AI failover는 Longhorn RWO snapshot PVC에 의존하지 않으므로 worker2 reboot fencing을 사용하지 않는다.
