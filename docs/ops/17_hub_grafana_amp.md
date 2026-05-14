# Hub Grafana / AMP Datasource

상태: source of truth
기준일: 2026-05-08

## 목적

Hub 내부 운영자가 AMP 메트릭을 탐색할 수 있도록 `observability` 네임스페이스에 Grafana OSS를 설치하고, AMP datasource를 SigV4 + IRSA로 연결하는 기준을 기록한다.

본사 관리자용 최종 화면은 Dashboard VPC의 Web/API로 분리한다. 다만 MVP 단계에서는 관리자들이 실제 HTTPS 경로로 Grafana UI에 접근할 수 있는지 확인하기 위해 M1 Issue 10에서 별도 Admin Ingress를 구성했고 검증을 완료했다.

## 현재 상태

- Grafana는 `observability` 네임스페이스에 Helm chart로 설치한다.
- Chart는 `grafana/grafana` `10.5.15`, app version은 `12.3.1`이다.
- Service는 `ClusterIP`로 유지한다.
- Grafana Service는 `ClusterIP`로 유지한다.
- 내부 로컬 접근은 `kubectl port-forward`를 계속 사용할 수 있다.
- 관리자 HTTPS 접근은 Public ALB 1개와 host 기반 Admin Ingress로 제공한다.
- Admin UI URL은 `https://grafana.minsoo-tech.cloud`이다.
- Grafana admin password는 Git에 저장하지 않고 Kubernetes Secret `observability/grafana-admin`에 최초 1회 생성한다.
- AMP datasource 이름은 `AEGIS-AMP`, uid는 `aegis-amp`이다.
- Datasource는 `sigV4Auth=true`, `sigV4AuthType=default`, `sigV4Region=ap-south-1`로 provision한다.

## 관리 파일

| 파일 | 역할 |
| --- | --- |
| `infra/hub/irsa_grafana_amp_query.tf` | Grafana AMP query용 IRSA role/policy |
| `scripts/ansible/templates/grafana-values.yaml.j2` | Grafana Helm values, AMP datasource, 기본 dashboard |
| `scripts/ansible/playbooks/hub_grafana_bootstrap.yml` | Grafana admin Secret 생성, Helm install/upgrade, private service 검증 |
| `scripts/ansible/playbooks/hub_grafana_verify.yml` | Deployment, IRSA annotation, ClusterIP, Grafana API 경유 AMP query 검증 |
| `scripts/ops/grafana-port-forward.sh` | 내부 Grafana UI 로컬 접근 |
| `scripts/ansible/templates/admin-ui-ingress.yaml.j2` | Grafana Admin UI HTTPS Ingress |
| `scripts/ansible/playbooks/hub_admin_ingress_bootstrap.yml` | Admin Ingress 적용 |
| `scripts/ansible/playbooks/hub_admin_ingress_verify.yml` | HTTPS endpoint 검증 |
| `scripts/ops/grafana-admin-password.sh` | Grafana admin password 조회 |

## IAM 권한

Grafana는 `observability/grafana` ServiceAccount로 실행되고 아래 IRSA role을 assume한다.

```text
arn:aws:iam::611058323802:role/AEGIS-IAMRole-IRSA-grafana-amp-query
```

허용 action은 AMP 조회용 read-only 권한으로 제한한다.

```text
aps:QueryMetrics
aps:GetSeries
aps:GetMetricMetadata
aps:GetLabels
```

대상 resource는 `AEGIS-AMP-hub` workspace ARN 하나로 제한한다.

## 실행

전체 Hub build에 포함되어 있으므로 기본 실행은 아래 명령만 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-all.sh
```

Grafana만 재적용해야 할 때는 아래 playbook을 실행한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_grafana_verify.yml
```

## 접속

관리자 HTTPS 접근:

```text
https://grafana.minsoo-tech.cloud
```

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

## 검증 결과

2026-05-06 검증 결과:

```text
Grafana deployment: 1/1 available
Grafana service: ClusterIP
Grafana pod: Running, restarts 0
Grafana IRSA: AEGIS-IAMRole-IRSA-grafana-amp-query
Grafana datasource: AEGIS-AMP / aegis-amp
Grafana API proxy query: up{cluster="AEGIS-EKS"} success
Admin UI: https://grafana.minsoo-tech.cloud HTTP 200
```

Grafana API를 통해 확인된 AMP query 결과:

```text
kubernetes-apiservers=1
kubernetes-apiservers=1
kubernetes-nodes=1
kubernetes-nodes=1
kubernetes-pods=1
prometheus-agent=1
```

## 역할 분리

| 화면 | 대상 사용자 | 접근 방식 | 데이터 |
| --- | --- | --- | --- |
| 내부 Grafana | 운영자/개발자 | EKS kubeconfig + port-forward 또는 Admin UI HTTPS Ingress | AMP 메트릭 |
| Dashboard VPC Web/API | 본사 관리자 | Route53 -> ALB -> WAF/Auth -> Web/API | DynamoDB LATEST/HISTORY, S3 processed |

MVP Admin Ingress는 ArgoCD/Grafana 운영 UI 접근 검증용이다. Dashboard VPC는 Grafana나 ArgoCD에 직접 접근하지 않고, DynamoDB LATEST/HISTORY와 S3 processed를 read-only로 조회하는 최종 관리자 화면 방향을 유지한다.

최신 상태 저장소의 최신 기준은 DynamoDB LATEST/HISTORY다. M1 당시 `latest/` S3 prefix 후보는 과거 검토안이며, S3는 raw/processed 이력 보존과 재처리 입력을 담당한다.

## 비용 기준

Grafana Pod 자체는 기존 EKS worker node 위에서 실행되므로 별도 AWS 고정 시간 비용을 추가하지 않는다. 현재 Hub와 Admin UI HTTPS Ingress는 삭제된 상태라 공유 Public ALB, ALB LCU, public IPv4, Route53 hosted zone 비용은 발생하지 않는다. rebuild 후 Admin UI HTTPS Ingress를 다시 활성화하면 해당 비용이 다시 발생한다. 최신 비용 기준은 `docs/ops/15_aws_cost_baseline.md`를 따른다.

추가될 수 있는 비용은 아래 정도다.

- Grafana chart/image pull과 plugin download 시 NAT Gateway data processing
- Grafana가 AMP를 조회할 때 발생하는 AMP query usage
- Grafana Pod 로그가 늘어날 경우 CloudWatch/EKS 로그 사용량

수집량, query 빈도, dashboard 수가 늘어나면 `docs/ops/15_aws_cost_baseline.md`를 함께 갱신한다.
