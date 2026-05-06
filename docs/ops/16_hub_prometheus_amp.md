# Hub Prometheus Agent / AMP

상태: source of truth
기준일: 2026-05-06

## 목적

Hub EKS의 `observability` 네임스페이스에서 Prometheus Agent를 실행하고, Amazon Managed Service for Prometheus(AMP) Workspace로 `remote_write`하는 기준을 기록한다.

## 현재 상태

- `scripts/build/build-all.sh`를 실행하면 Hub ArgoCD 검증 뒤 Prometheus Agent bootstrap과 verify가 함께 실행된다.
- Prometheus Agent는 `observability/prometheus-agent` ServiceAccount를 사용한다.
- ServiceAccount는 AMP remote_write용 IRSA role `AEGIS-IAMRole-IRSA-prometheus-remote-write`와 연결되어 있다.
- AMP Workspace는 `AEGIS-AMP-hub`이다.
- AMP Workspace ID는 `ws-6a8853dc-0eb4-43e7-9b97-efade5b75765`이다.
- AMP remote_write endpoint는 `https://aps-workspaces.ap-south-1.amazonaws.com/workspaces/ws-6a8853dc-0eb4-43e7-9b97-efade5b75765/api/v1/remote_write`이다.

## 관리 파일

| 파일 | 역할 |
| --- | --- |
| `scripts/ansible/playbooks/hub_prometheus_agent_bootstrap.yml` | kubeconfig 갱신, namespace baseline 적용, IRSA ServiceAccount annotation, Prometheus Agent manifest 적용 |
| `scripts/ansible/playbooks/hub_prometheus_agent_verify.yml` | Deployment available replica, IRSA annotation, Pod 상태, 최근 로그의 remote_write 오류 여부 검증 |
| `scripts/ansible/templates/prometheus-agent.yaml.j2` | RBAC, ConfigMap, Deployment, Service manifest template |
| `scripts/build/build-hub.sh` | Hub build 흐름에서 bootstrap/verify playbook 호출 |

## 수집 대상

현재 Prometheus Agent는 아래 기본 대상을 수집한다.

| job | 대상 |
| --- | --- |
| `prometheus-agent` | Agent 자체 `/metrics` |
| `kubernetes-apiservers` | Kubernetes API server metrics |
| `kubernetes-nodes` | EKS node metrics |
| `kubernetes-pods` | `prometheus.io/scrape: "true"` annotation이 있는 Pod |

공통 external label:

```text
project     = AEGIS
cluster     = AEGIS-EKS
environment = hub-mvp
```

## 실행

전체 Hub build에 포함되어 있으므로 기본 실행은 아래 명령만 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-all.sh
```

Prometheus Agent만 재적용해야 할 때는 아래 playbook을 실행한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_bootstrap.yml
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_verify.yml
```

## 검증 결과

2026-05-06 검증 결과:

```text
prometheus-agent pod: Running, 1/1 Ready, restarts 0
IRSA role annotation: arn:aws:iam::611058323802:role/AEGIS-IAMRole-IRSA-prometheus-remote-write
recent logs: remote_write error pattern 없음
AMP query: up{cluster="AEGIS-EKS"} success
```

AMP Query API에서 확인된 `up{cluster="AEGIS-EKS"}` 수신 대상:

```text
job=prometheus-agent, instance=127.0.0.1:9090, value=1
job=kubernetes-apiservers, instances=10.0.10.129:443 and 10.0.11.53:443, value=1
job=kubernetes-nodes, nodes=ip-10-0-10-207 and ip-10-0-11-46, value=1
job=kubernetes-pods, pod=prometheus-agent-7ffb8d885d-vdtn7, value=1
```

## 비용 기준

Prometheus Agent 자체는 EKS worker node 안에서 동작하므로 별도 고정 시간 비용을 만들지는 않는다. 다만 AMP는 ingest, storage, query 사용량 기반 비용이 발생할 수 있다. 수집 job, scrape interval, Pod annotation 대상이 늘어나면 `docs/ops/15_aws_cost_baseline.md`를 함께 갱신한다.

현재 scrape interval은 30초이며, 수집 대상은 Hub 기본 메트릭으로 제한한다.

## 장애 확인

verify playbook이 실패하면 아래 순서로 확인한다.

```bash
kubectl -n observability get pod -l app.kubernetes.io/name=prometheus-agent -o wide
kubectl -n observability get serviceaccount prometheus-agent -o yaml
kubectl -n observability logs deployment/prometheus-agent --since=10m --tail=200
kubectl get clusterrole prometheus-agent -o yaml
```

대표 원인:

- ServiceAccount annotation이 `AEGIS-IAMRole-IRSA-prometheus-remote-write`와 다름
- `remote_write` endpoint가 foundation Terraform output과 다름
- ClusterRole에 Kubernetes discovery 또는 `/metrics` 권한이 빠짐
- AMP Workspace가 삭제되었거나 다른 리전에 있음
- Node가 `NotReady`라 Agent Pod가 스케줄링되지 않음
