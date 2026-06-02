# 요약 보고서

상태: source of truth
기준일: 2026-06-02

## 한 줄 요약

`factory-a` Raspberry Pi 3-node Safe-Edge 기준선을 시작점으로 Hub, 멀티 factory data-plane, `risk-v0.2.0` Risk 계산, DataProcessor freshness refresh, Cloud infra read model, S3 processed 기반 Slack risk alert, Daily Factory Report MVP 수동 검증까지 완료했다.

## 현재 완료한 것

```text
K3s 3-node cluster
Longhorn storage
ArgoCD Helm 설치
GitHub GitOps repo 연결
monitoring / ai-apps 배포 분리
InfluxDB 1일 retention
Grafana sensor / AI dashboard
Prometheus Node Exporter Full 1860 dashboard
image prepull DaemonSet
AI snapshot hostPath + 24시간 cleanup + 매일 03:00 KST purge
AI inference result InfluxDB PVC 기반 Longhorn 저장
LAN 제거 failover/failback 테스트
k3s-agent 중지 failover/failback 테스트
AWS Hub rebuildable baseline
factory-a/b/c IoT -> S3 raw -> Lambda -> DynamoDB/S3 processed
DataProcessorRefresh1m stale risk refresh
GraphAggregator5m DynamoDB/S3 5분 집계
CloudInfraFast/SlowCollector read model
RiskAlertDispatcher Slack alert pipeline
Daily Factory Report MVP 수동 검증
```

## 주요 성과

- `factory-a`는 단독 Safe-Edge 기준선으로 운영 가능하다.
- worker2 장애 시 worker1로 failover가 가능하다.
- worker2 복구 후 master OS cron 기반 Kubernetes-only failback이 가능하다.
- AI snapshot PVC 제거 후 Longhorn RWO Multi-Attach 없이 AI failover가 가능하다.
- 데이터 공백을 10초 bucket과 1초 bucket으로 측정했다.

## 핵심 수치

```text
LAN 제거 test_09:
worker2 NotReady -> AI/audio/BME worker1 Running 성공
worker2 재연결 -> AI/audio/BME worker2 failback 성공
1초 bucket 최대 공백: AI 87초, audio 90초, BME 83초
10초 bucket 운영 기준 공백: AI 80초, audio 80초, BME 70초
```

## 현재 남은 과제

```text
runtime-config 기반 Risk weight/threshold 적용
Risk Twin read model 계약 고정
factory-a 2026-05-28T07:54Z 이후 data-plane 입력 중단 원인 복구
Daily Factory Report S3 read 성능/비용 관측 개선
RiskAlertDispatcher Slack webhook rotate 및 alert reason 한글 label 보강
Dashboard page/VPC 담당 구현과 조회 필드 계약 정합성 확인
M7 통합 검증과 문서 최종 보정
```

## 후속 방향

1. `runtime-config.yaml`을 Lambda Risk 계산에 연결
2. Risk Twin read model을 DynamoDB/S3 processed 계약으로 고정
3. `factory-a` data-plane Pod/Secret/outbox/publisher를 복구해 실제 입력을 재개
4. Daily Factory Report S3 read 성능과 비용 관측값 개선
5. RiskAlertDispatcher 운영 문구와 Slack webhook rotation 기준 보강
6. Dashboard page/VPC 담당 구현과 조회 필드 계약 맞추기
7. M7 통합 검증 시나리오와 문서 정합성 보정
