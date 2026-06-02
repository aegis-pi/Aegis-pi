# 검토 및 발표 요약

상태: source of truth
기준일: 2026-06-02

## 핵심 메시지

`factory-a` Safe-Edge 기준선은 실제 구축과 장애 검증까지 완료됐고, AWS Hub/data-pipeline을 통해 `factory-a/b/c` 멀티 공장 데이터 수집, Risk 계산, Cloud infra read model, Slack risk alert, Daily Factory Report MVP까지 검증했다. 다음 단계는 runtime-config 기반 Risk 계약과 Dashboard read model을 고정하는 것이다.

## 발표 포인트

1. Safe-Edge 기준선 복구 및 장애 테스트 완료
2. Hub EKS/ArgoCD/Grafana/Admin UI rebuild 기준선 확보
3. `factory-a/b/c` IoT -> S3 raw -> Lambda -> DynamoDB/S3 processed 검증
4. DataProcessorRefresh1m, GraphAggregator5m, CloudInfraFast/SlowCollector 검증
5. S3 processed 기반 RiskAlertDispatcher Slack 알림 검증
6. Bedrock 기반 Daily Factory Report MVP 수동 실행 검증

## 수치

```text
worker2 전원 제거 -> worker1 전체 Running: 약 74초
worker2 전원 재연결 -> worker2 전체 Running: 약 2분 11초
failover 1초 bucket 최대 공백: 65-75초
failback 1초 bucket 최대 공백: 2초
```

## 후속 질문 대비

왜 Hub부터 하지 않았나:
- 실제 운영형 기준선이 먼저 안정화되어야 멀티 공장 구조가 의미를 갖는다.

왜 CronJob이 아니라 master OS cron인가:
- 하드웨어 의존 Pod에서 Kubernetes CronJob 방식은 불안정했다.
- 현재는 master에서 Kubernetes API만 사용하는 방식으로 failback한다.

왜 Longhorn retention이 아니라 InfluxDB retention인가:
- Longhorn은 블록 복제 계층이다.
- 실제 시계열 보존 기간은 InfluxDB retention policy가 결정한다.

왜 Container Insights를 기본 OFF로 두는가:
- MVP/개발 단계에서 EKS Container Insights 상시 비용이 크다.
- 현재는 metrics-server, AWS/Kubernetes API, CloudInfra collectors로 Dashboard용 요약 read model만 저장한다.

왜 Slack webhook을 Terraform 변수에 넣지 않는가:
- URL은 민감정보이므로 repo와 Terraform state에 저장하지 않는다.
- Terraform은 Secrets Manager secret metadata만 관리하고, build script가 로컬 secret 파일에서 값을 주입한다.
