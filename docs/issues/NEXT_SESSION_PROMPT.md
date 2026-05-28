# Next Session Prompt

아래 프롬프트를 다음 Codex 세션 시작 시 그대로 사용한다.

```text
작업 디렉터리는 /home/vicbear/Aegis/git_clone/Aegis-pi 입니다.

현재 목표는 Daily Factory Report 작업을 계속하는 것입니다. Hub 비용 최적화 변경은 AWS 반영과 검증까지 완료된 상태입니다.

먼저 현재 상태를 확인하세요.

1. git status --short
2. docs/issues/SESSION_STATE.md 확인
3. docs/ops/15_aws_cost_baseline.md 확인
4. apps/daily-report-generator/ 확인
5. infra/reporting/ 확인

완료된 Hub 비용 최적화:

- AMP는 사용자가 EKS 상태 확인에 직접 쓰지 않으므로 active 구성에서 제거한다.
- infra/foundation/amp.tf, AMP output, Prometheus remote_write IRSA, Grafana AMP query IRSA, Prometheus Agent template/playbook은 삭제됐다.
- 기존 클러스터에 남은 observability/prometheus-agent 리소스는 hub_prometheus_agent_cleanup.yml로 정리한다.
- Hub NAT Gateway는 조건 없이 1개만 유지한다.
- Azone NAT/EIP를 보존하기 위해 infra/hub/moved.tf에 aws_eip.nat["Azone"] -> aws_eip.nat, aws_nat_gateway.public["Azone"] -> aws_nat_gateway.public moved block을 추가했다.
- Czone private route table은 Azone NAT Gateway를 바라보도록 변경됐다.
- 데이터 수집/처리 경로는 IoT Core -> Lambda data processor -> DynamoDB LATEST/HISTORY + S3 processed이며, Hub EKS/AMP/Grafana 변경과 직접 연결되지 않는다.

실제 AWS 반영 결과:

- infra/foundation apply 완료: AMP workspace ws-60897fc1-019b-417e-acb7-60fbcad61a2b 삭제
- infra/hub apply 완료: Czone NAT nat-0c31e93d9cdf730f1 및 EIP 삭제, Azone NAT nat-0db2f6d136046bcb8 유지
- 두 private route table 모두 nat-0db2f6d136046bcb8 사용
- Grafana AMP query IRSA와 Prometheus remote_write IRSA 삭제
- observability/prometheus-agent Kubernetes resources cleanup 완료
- Grafana Helm 재적용 완료, /api/health database ok
- terraform plan: infra/foundation, infra/hub 모두 No changes
- 데이터 파이프라인 확인: DynamoDB LATEST factory-a/b/c normal/safe, S3 raw/processed 최신 object 확인, Lambda Active/Successful

이미 통과한 검증:

- terraform -chdir=infra/foundation fmt
- terraform -chdir=infra/hub fmt
- bash -n scripts/build/build-hub-platform.sh scripts/build/verify-complete.sh scripts/destroy/destroy-all.sh scripts/destroy/destroy-hub-infra.sh scripts/destroy/destroy-foundation.sh scripts/ansible/inventory/hub_eks_dynamic.sh
- terraform -chdir=infra/foundation validate
- terraform -chdir=infra/hub validate
- python -m pytest -q apps/daily-report-generator
- python -m compileall -q apps/daily-report-generator

주의:

- root에서 python -m pytest -q를 실행하면 apps/data-processor/tests import 경로 문제로 기존 테스트 collection이 실패한다. 이번 변경과 직접 관련 없는 기존 상태다.

다음 작업 순서:

1. Daily Factory Report enriched v2 Bedrock 실호출을 진행한다.
2. factory-a/b/c 24시간 daily merge 검증을 수행한다.
3. infra/reporting Terraform validate/plan/apply를 진행한다.
4. Step Functions 수동 실행으로 reports/daily 산출물을 확인한다.
5. 결과를 docs/ops/24_daily_factory_report.md와 docs/issues/SESSION_STATE.md에 반영한다.
```
