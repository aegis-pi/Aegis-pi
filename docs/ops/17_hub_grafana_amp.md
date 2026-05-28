# Hub Grafana

상태: source of truth
기준일: 2026-05-27

## 목적

Hub 내부 운영자가 Grafana UI에 접근할 수 있도록 `observability` 네임스페이스에 Grafana OSS를 설치한다. AMP datasource와 SigV4/IRSA query 권한은 비용 최적화 기준에서 제거했다.

본사 관리자용 최종 화면은 Dashboard VPC의 Web/API로 분리한다. Grafana는 사용자용 Risk Twin 대시보드가 아니라 Hub 관리/관측 보조 UI다.

## 현재 상태

- Grafana는 `observability` 네임스페이스에 Helm chart로 설치한다.
- Chart는 `grafana/grafana` `10.5.15`, app version은 `12.3.1`이다.
- Service는 `ClusterIP`로 유지한다.
- 내부 로컬 접근은 `kubectl port-forward`를 사용한다.
- 관리자 HTTPS 접근은 선택적 Admin Ingress가 활성화된 경우에만 Public ALB를 통해 제공한다.
- Grafana admin password는 Git에 저장하지 않고 Kubernetes Secret `observability/grafana-admin`에 최초 1회 생성한다.
- AMP datasource는 provision하지 않는다.

## 관리 파일

| 파일 | 역할 |
| --- | --- |
| `scripts/ansible/templates/grafana-values.yaml.j2` | Grafana Helm values |
| `scripts/ansible/playbooks/hub_grafana_bootstrap.yml` | Grafana admin Secret 생성, Helm install/upgrade, private service 검증 |
| `scripts/ansible/playbooks/hub_grafana_verify.yml` | Deployment, ClusterIP, Grafana health API 검증 |
| `scripts/ops/grafana-port-forward.sh` | 내부 Grafana UI 로컬 접근 |
| `scripts/ansible/templates/admin-ui-ingress.yaml.j2` | Grafana Admin UI HTTPS Ingress |
| `scripts/ansible/playbooks/hub_admin_ingress_bootstrap.yml` | Admin Ingress 적용 |
| `scripts/ansible/playbooks/hub_admin_ingress_verify.yml` | HTTPS endpoint 검증 |
| `scripts/ops/grafana-admin-password.sh` | Grafana admin password 조회 |

## 실행

전체 Hub build에 포함되어 있으므로 기본 실행은 아래 명령만 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

Grafana만 재적용해야 할 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_verify.yml
```

## 접속

내부 로컬 접근:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/ops/grafana-port-forward.sh
```

기본 URL:

```text
http://127.0.0.1:30080
```

admin password가 필요할 때만 아래 명령으로 조회한다. 출력값은 문서나 Git에 기록하지 않는다.

```bash
scripts/ops/grafana-admin-password.sh
```

## 검증 기준

```text
Grafana deployment: availableReplicas >= 1
Grafana service: ClusterIP
Grafana health API: /api/health success
```
