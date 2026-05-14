# Hub Namespace Baseline

상태: Ansible bootstrap 기준 전환 완료, 현재 Hub EKS deleted
기준일: 2026-05-08

## 목적

Hub EKS 내부 기능을 namespace 단위로 분리해 ArgoCD, 운영 관측, 임시 검증용 workload, 운영 보조 기능의 배포 경계를 명확히 한다. 최신 목표에서 Risk 계산과 정규화는 별도 Hub 파드가 아니라 Lambda data processor와 DynamoDB/S3 processed로 분리한다.

## Namespace

| Namespace | 역할 |
| --- | --- |
| `argocd` | Hub에서 Spoke 배포 제어 |
| `observability` | Grafana, AMP 연동 메트릭 관제 |
| `risk` | M1 검증용 또는 임시 risk workload. 최신 MVP에서는 별도 Risk 계산 파드를 두지 않음 |
| `ops-support` | legacy `pipeline_status` 집계 보조 기능 후보. 최신 MVP에서는 Lambda data processor가 `pipeline_status`를 계산 |

## Ansible bootstrap 관리

Namespace와 LimitRange는 Ansible bootstrap manifest에서 관리한다. IRSA ServiceAccount annotation은 bootstrap playbook에서 Terraform output을 읽어 적용한다.

```text
scripts/ansible/files/hub-bootstrap.yaml
scripts/ansible/playbooks/hub_argocd_bootstrap.yml
```

각 namespace에는 `default-limits` LimitRange를 적용한다.

| 항목 | 값 |
| --- | --- |
| default request CPU | `100m` |
| default request memory | `128Mi` |
| default limit CPU | `500m` |
| default limit memory | `512Mi` |

## 검증

```bash
kubectl get namespaces argocd observability risk ops-support
kubectl get limitrange -A
```

2026-05-04 확인 결과:

```text
argocd          Active
observability   Active
risk            Active
ops-support     Active
```

각 namespace에 `default-limits` LimitRange가 생성되어 있다.

2026-05-06 기준 Hub EKS는 `build-all --admin-ui`와 `build-hub`로 재생성/검증했고, 2026-05-08 비용 정리를 위해 destroy 완료 상태다. rebuild 시 M1 검증용 `risk/risk-normalizer`와 `observability/prometheus-agent` ServiceAccount는 각각 S3 처리 검증과 AMP remote_write용 IRSA role로 annotation된다. 단, `risk/risk-normalizer`는 과거 IRSA 검증용 workload이며 최신 데이터 처리 구현 대상은 Lambda data processor다.

나중에 Hub EKS를 destroy/recreate하면 `scripts/build/build-hub.sh` 실행 시 Ansible bootstrap playbook이 `argocd`, `observability`, `risk`, `ops-support` namespace, `default-limits` LimitRange, IRSA ServiceAccount, Hub ArgoCD Helm release를 다시 생성한다.

## Rebuild 후 ArgoCD 기준

```text
Helm release: argocd
Namespace: argocd
Chart: argo-cd-9.5.11
App version: v3.3.9
Service type: ClusterIP
UI access: https://argocd.minsoo-tech.cloud, or kubectl port-forward for local fallback
CLI path: /home/vicbear/Aegis/.tools/bin/argocd
```

검증:

```bash
helm list -n argocd
kubectl -n argocd get pods,svc -o wide
kubectl -n argocd get secret argocd-initial-admin-secret
kubectl -n argocd port-forward service/argocd-server 8080:443
```

2026-05-06 검증에서는 `https://argocd.minsoo-tech.cloud`와 `https://127.0.0.1:8080`에서 HTTP 200 응답을 확인했다. 현재 Hub는 삭제된 상태이므로 rebuild 후 다시 확인한다. 초기 admin 비밀번호 값은 문서에 기록하지 않는다.

## ArgoCD 접근 전략

현재 MVP 관리자 접근은 Admin UI HTTPS Ingress를 기본 경로로 사용한다.

```text
https://argocd.minsoo-tech.cloud
```

로컬 fallback이 필요하면 사용자 PC에 EKS kubeconfig를 설정하고 `kubectl port-forward`로 ArgoCD UI에 접근한다.

```bash
aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS
kubectl -n argocd port-forward service/argocd-server 8080:443
```

브라우저 접근:

```text
https://127.0.0.1:8080
```

운영 기준:

- `argocd-server`는 `ClusterIP`로 유지한다.
- public `LoadBalancer`는 만들지 않는다.
- MVP 관리자 외부 접근은 shared Public ALB와 HTTPS Ingress로 제공한다.
- 운영 보안 강화가 필요하면 M1 Issue 11에서 WAF/Cognito/OIDC 또는 IP 제한을 적용한다.
- Tailscale 적용 후 EKS API endpoint public CIDR `0.0.0.0/0`를 축소한다.
- ArgoCD 설정은 UI 클릭보다 Git/YAML/ApplicationSet으로 코드화한다.

## ArgoCD 재생성 기준

EKS를 destroy/recreate하면 EKS 내부의 ArgoCD도 함께 사라진다. 따라서 ArgoCD를 수동 Helm install로만 유지하지 않고 Ansible local bootstrap으로 관리한다.

구성:

```text
scripts/ansible/inventory/hub_eks_dynamic.sh
scripts/ansible/inventory/group_vars/hub_eks.yml
scripts/ansible/files/argocd-values.yaml
scripts/ansible/playbooks/hub_argocd_bootstrap.yml
scripts/ansible/playbooks/hub_argocd_verify.yml
```

기준:

- Dynamic inventory는 `infra/hub`의 `terraform output -json`을 읽어 `cluster_name`, `aws_region`, kubeconfig 명령을 가져온다.
- Ansible은 EC2 SSH가 아니라 `localhost`에서 EKS Kubernetes API를 대상으로 실행한다.
- ArgoCD 설치는 `helm upgrade --install`로 idempotent하게 수행한다.
- chart는 `argo/argo-cd`, version은 `9.5.11`을 사용한다.
- release name은 `argocd`, namespace는 `argocd`다.
- `argocd-server` service type은 `ClusterIP`다.
- public `LoadBalancer`는 만들지 않는다.
- repo, Project, Application, ApplicationSet은 UI 클릭만으로 만들지 않고 후속 코드화 대상으로 둔다.

포트포워딩은 Ansible bootstrap에 넣지 않는다. 포트포워딩은 사용자가 UI에 접근할 때 실행하는 로컬 장기 실행 프로세스이므로 운영 스크립트로 관리한다.

스크립트:

```text
scripts/ops/argocd-port-forward.sh
```

## 종료 순서

장시간 사용하지 않을 때는 비용 방지를 위해 Hub 인프라를 내린다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-hub.sh
```

2026-05-06 검증 당시 active 확인:

```text
kubectl get nodes: 2 Ready
kubectl -n argocd get pods: all Running / Ready
```
