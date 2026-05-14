# Ansible Automation

Safe-Edge 반복 점검과 Hub EKS bootstrap 자동화를 관리한다.

## Hub ArgoCD bootstrap

Hub EKS의 ArgoCD bootstrap은 SSH를 사용하지 않는다. Ansible은 `localhost`에서 실행되고, `infra/hub` Terraform output을 dynamic inventory로 읽은 뒤 EKS Kubernetes API에 접근한다.

현재 bootstrap은 namespace/LimitRange, ArgoCD Helm release, M1 검증용 `risk/risk-normalizer` IRSA ServiceAccount, `observability/prometheus-agent` AMP remote_write IRSA ServiceAccount, Prometheus Agent remote_write 구성, 내부 Grafana AMP datasource, AWS Load Balancer Controller, 선택적 Admin UI HTTPS Ingress, Hub Tailscale Operator/egress/UI/cluster Secret 구성을 적용한다. 최신 목표에서 IoT Core 이후 정규화, Risk 계산, `pipeline_status` 갱신은 Lambda data processor와 DynamoDB/S3 processed가 담당한다.

선행 조건:

- AWS MFA 세션이 현재 shell에 설정되어 있음
- `infra/hub` Terraform apply가 완료되어 output을 조회할 수 있음
- `infra/foundation` Terraform apply가 완료되어 AMP/S3/IoT Rule output을 조회할 수 있음
- `aws`, `kubectl`, `helm`, `terraform`, `jq`, `ansible-playbook` 사용 가능
- Hub Tailscale 자동화를 실행할 때 `~/Aegis/.aegis/secrets/tailscale/operator.env`에 `TAILSCALE_OAUTH_CLIENT_ID`, `TAILSCALE_OAUTH_CLIENT_SECRET` 존재

실행:

```bash
cd scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aws_load_balancer_controller_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_bootstrap.yml
```

검증:

```bash
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_aws_load_balancer_controller_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_admin_ingress_verify.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_tailscale_verify.yml
```

Admin UI Ingress는 기본값에서 비활성화된다. Gabia에서 `minsoo-tech.cloud`를 Route53 NS로 위임하고 ACM certificate가 `ISSUED`가 된 뒤 전체 build에서는 `scripts/build/build-all.sh --admin-ui`, Hub 단독 적용에서는 `ADMIN_UI_INGRESS_ENABLED=true scripts/build/build-hub.sh`로 활성화한다.

초기 admin 비밀번호를 명시적으로 출력해야 할 때만 아래처럼 실행한다. 비밀번호 값은 문서에 기록하지 않는다.

```bash
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_argocd_bootstrap.yml \
  -e argocd_print_initial_admin_password=true
```

UI 접근:

```bash
../hub/argocd-port-forward.sh
```

Admin UI HTTPS Ingress가 활성화된 현재 상태에서는 아래 주소도 사용할 수 있다.

```text
https://argocd.minsoo-tech.cloud
https://grafana.minsoo-tech.cloud
```

## start_test 실행

비밀번호는 inventory나 파일에 저장하지 않고 실행 시 입력한다.

```bash
cd scripts/ansible
ansible-playbook -i inventory/factory-a.ini playbooks/start_test.yml
```

`start_test.yml`은 `master`에만 SSH 접속하고, worker 상태는 `master`의 `kubectl` 결과로 확인한다. 따라서 현재 start_test 실행 때는 아래 프롬프트 하나만 입력한다.

```text
master SSH/sudo password:
```

`start_test.yml`은 factory-a master의 Tailscale 상태를 검증 대상에 포함한다. 따라서 SSH 접속 경로로 master Tailscale IP `100.117.40.125`를 쓰면 검증 대상과 실행 경로가 겹친다. Tailscale 장애를 검증하거나 관측해야 할 때는 아래 중 하나를 사용한다.

```text
권장 1: 10.10.10.0/24 내부망에 붙어 있는 control host에서 기본 inventory(10.10.10.10)로 실행
권장 2: master wlan0 관리 IP로 실행
비권장: master Tailscale IP(100.117.40.125)로 실행
```

현재 control host가 factory-a 내부망에 직접 붙어 있지 않으면 master `wlan0` IP를 명시한다.

```bash
ansible-playbook -i inventory/factory-a.ini playbooks/start_test.yml \
  -e factory_a_master_ssh_host=<master-wlan-ip>
```

`wlan0` IP는 DHCP로 바뀔 수 있으므로 AP/router에서 master의 wlan0 MAC에 DHCP reservation을 잡거나, 실행 직전에 현재 IP를 확인해서 넘긴다. 2026-05-08 검증 당시 master wlan0 IP는 `192.168.0.45`였다.

playbook 내부에서는 Tailscale 검증 전에 master의 `wlan0` 인터넷 경로를 먼저 확인한다.

```text
wlan0 IPv4
wlan0 default route
controlplane.tailscale.com DNS
controlplane.tailscale.com HTTPS reachability
```

따라서 마지막 Tailscale 검증이 실패했을 때는 `wlan0` 인터넷 경로 문제인지, `tailscaled` 자체 문제인지 분리해서 볼 수 있다.

성공하면 `scripts/ansible/evidence/` 아래에 Markdown evidence 파일이 생성된다.

Factory-A IP, LoadBalancer IP, 워크로드 노드명은 `inventory/group_vars/factory_a.yml`에서 관리한다. 다른 현장이나 IP 대역으로 바꿀 때는 이 파일을 먼저 수정한다.

주요 변수:

```yaml
factory_a_nodes:
  master:
    ip: 10.10.10.10
  worker1:
    ip: 10.10.10.11
  worker2:
    ip: 10.10.10.12

factory_a_services:
  longhorn_frontend:
    ip: 10.10.10.201
```

비밀번호 SSH를 쓰는 경우 control host에 `sshpass`가 필요하다.

```bash
sudo apt-get install -y sshpass
```

SSH key 인증을 설정했다면 `-k`는 빼고 실행한다.

node별 비밀번호 매핑은 `inventory/group_vars/factory_a.yml`의 `password_var`로 관리한다. worker에 직접 접속하는 playbook을 추가할 때는 같은 방식으로 `factory_a_worker1_password`, `factory_a_worker2_password`를 `vars_prompt`에 추가한다.

## 범위

이 playbook은 `safe-edge/start_test.md`의 시작 점검 명령을 `master`에서 실행하고 주요 기대값을 검증한다.

자동화 대상:

- Kubernetes node, service, pod 상태 확인
- MetalLB, Longhorn, Argo CD, Monitoring, AI Apps 상태 확인
- failback cron 로그 확인
- 로컬 evidence Markdown 생성

자동화하지 않는 대상:

- worker2 LAN 제거
- worker2 전원 차단
- 장애 주입 후 최종 성공/실패 해석
