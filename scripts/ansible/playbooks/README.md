# Ansible Playbooks

이 디렉터리는 `factory-a` 운영 점검과 Hub EKS bootstrap 자동화를 위한 Ansible playbook을 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `factory_a_os_baseline.yml` | OS만 설치된 factory-a 3노드의 hostname, 필수 패키지, Longhorn 사전 조건, swap/time sync, eth0/wlan0 라우팅 역할, K3s config 사전 배치를 적용 |
| `factory_a_k3s_install.yml` | OS baseline 이후 K3s server/agent 설치, master taint, 3노드 Ready와 flannel public IP 검증 |
| `start_test.yml` | master에 접속해 K3s, MetalLB, Longhorn, ArgoCD, monitoring, ai-apps, master `wlan0` 인터넷 경로, Tailscale 상태를 검증하고 evidence를 생성 |
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
| `hub_tailscale_bootstrap.yml` | Tailscale Operator, factory-a egress Service, ArgoCD/Grafana Tailscale UI Service, ArgoCD factory-a cluster Secret 적용 |
| `hub_tailscale_verify.yml` | Tailscale Operator/proxy readiness, factory-a K3s API TCP, Tailscale UI HTTP, ArgoCD cluster Secret 설정 확인 |

## 기준

- `factory_a_os_baseline.yml`은 K3s 설치 전 OS baseline을 잡는 playbook이다. K3s server/agent 설치, Longhorn/MetalLB/ArgoCD/app 배포는 이후 절차에서 수행한다.
- `factory_a_k3s_install.yml`은 baseline playbook이 배치한 `/etc/rancher/k3s/config.yaml`을 사용한다.
- factory-a 네트워크 기준은 `eth0` = K3s 내부망 no-default route, `wlan0` = 인터넷 default route, `tailscale0` = 원격 관리/Hub-Spoke 제어망이다.
- `start_test.yml`은 Tailscale 자체를 검증하므로 master Tailscale IP를 SSH 실행 경로로 사용하지 않는다.
- control host가 `10.10.10.0/24` 내부망에 붙어 있으면 기본 inventory의 `10.10.10.10`으로 실행한다. 내부망에 없을 때만 `factory_a_master_ssh_host=<master-wlan-ip>`로 master `wlan0` IP를 명시한다.
- master `wlan0` IP는 DHCP 값이므로 AP/router DHCP reservation 또는 실행 직전 현재 IP 확인이 필요하다.
- 초기 자동화는 상태 수집과 검증 중심으로 유지한다.
- 물리 LAN 제거, 전원 차단 같은 장애 유발은 수동 절차로 둔다.
- playbook 결과는 `scripts/ansible/evidence/`에 저장한다.
- Hub bootstrap playbook은 SSH가 아니라 `localhost`에서 EKS Kubernetes API를 대상으로 실행한다.
- Hub ArgoCD Helm release가 이미 `deployed` 상태이고 chart version이 같으면 Helm upgrade를 건너뛴다. 강제 재적용은 `-e argocd_force_upgrade=true`로 실행한다.
- Admin Ingress는 `ADMIN_UI_INGRESS_ENABLED=true`일 때만 적용한다. 기본값은 인증서 발급 전 ALB 비용과 build 실패를 피하기 위해 비활성화다.
- Hub Tailscale bootstrap은 `BUILD_TAILSCALE=true` 기본값으로 `build-hub.sh`에서 실행한다. `~/Aegis/.aegis/secrets/tailscale/operator.env`가 없으면 실패한다.

## factory-a OS baseline 실행

OS만 설치된 `master`, `worker1`, `worker2`의 hostname, 패키지, Longhorn 사전 조건, swap/time sync, NetworkManager 라우팅 기준, K3s config 파일을 준비한다.

실행 전제:

- 세 노드가 `inventory/group_vars/factory_a.yml`의 IP로 SSH 접속 가능
- control host에 `ansible-playbook`과 비밀번호 SSH용 `sshpass` 설치
- Raspberry Pi OS가 NetworkManager/nmcli를 사용하면 `eth0` static no-default와 `wlan0` default route를 자동 적용
- `nmcli`가 없으면 네트워크는 변경하지 않고 경고만 출력하므로 OS별 네트워크 설정을 수동으로 맞춘다

실행:

```bash
cd scripts/ansible
ansible-playbook -i inventory/factory-a.ini playbooks/factory_a_os_baseline.yml
```

주의:

```text
eth0 SSH로 접속 중인 상태에서 eth0 NetworkManager profile을 재적용하므로 순간적으로 SSH가 끊길 수 있다.
playbook은 serial: 1로 한 노드씩 처리한다.
K3s는 이 playbook에서 설치하지 않고 /etc/rancher/k3s/config.yaml만 사전 배치한다.
Tailscale이 이미 설치되어 있으면 accept-routes=false만 적용한다. tailscale login/up은 별도 절차로 진행한다.
```

## factory-a K3s 설치 실행

OS baseline 이후 K3s server와 agent를 설치한다.

```bash
cd scripts/ansible
ansible-playbook -i inventory/factory-a.ini playbooks/factory_a_k3s_install.yml
```

입력하는 `K3s cluster token`은 세 노드에 동일하게 사용한다. 새 구축이면 임의의 충분히 긴 문자열을 넣고, 문서나 Git에는 저장하지 않는다.

이 playbook은 다음을 수행한다.

```text
master: K3s server 설치
worker1/worker2: K3s agent join
master: control-plane/master NoSchedule taint 적용
검증: master/worker1/worker2 Ready
검증: flannel public-ip가 10.10.10.10/11/12인지 확인
```
