# Hub Prometheus Agent / AMP

상태: retired
기준일: 2026-05-27

## 결정

AMP(Amazon Managed Service for Prometheus)와 Hub Prometheus Agent는 active 구성에서 제거한다.

이유:

- 현재 사용자는 AMP로 EKS 상태를 직접 확인하지 않는다.
- EKS Hub 관측은 비용 대비 필요성이 낮다.
- 데이터 수집/처리의 source of truth는 AMP가 아니라 IoT Core -> Lambda data processor -> DynamoDB LATEST/HISTORY#STATE + S3 processed, GraphAggregator5m -> DynamoDB GRAPH#5M + S3 processed_agg이다.
- Hub Grafana는 내부 관리 UI로만 유지하고 AMP datasource는 제거한다.

## 제거 대상

| 대상 | 상태 |
| --- | --- |
| `infra/foundation/amp.tf` | 삭제 |
| `infra/hub/irsa_prometheus_remote_write.tf` | 삭제 |
| `scripts/ansible/playbooks/hub_prometheus_agent_bootstrap.yml` | 삭제 |
| `scripts/ansible/playbooks/hub_prometheus_agent_verify.yml` | 삭제 |
| `scripts/ansible/templates/prometheus-agent.yaml.j2` | 삭제 |
| `observability/prometheus-agent` Kubernetes 리소스 | `hub_prometheus_agent_cleanup.yml`에서 정리 |

## 운영 영향

AMP 제거는 EKS 메트릭 remote_write만 중단한다. IoT Core 수신, Lambda data processor 실행, DynamoDB/S3 processed 적재는 `infra/data-pipeline`과 `infra/foundation`에 속하므로 Hub EKS의 Prometheus Agent 제거와 직접 연결되지 않는다.

단, Hub EKS 내부 Grafana에서 AMP Prometheus query를 실행하는 기능은 사라진다. EKS 상태 확인은 `kubectl`, EKS 콘솔, CloudWatch Logs/Metrics 또는 필요 시 별도 경량 Prometheus를 검토한다.

## Cleanup 실행

전체 Hub platform build에 cleanup이 포함된다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

cleanup만 실행해야 할 때:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ansible
ansible-playbook -i inventory/hub_eks_dynamic.sh playbooks/hub_prometheus_agent_cleanup.yml
```
