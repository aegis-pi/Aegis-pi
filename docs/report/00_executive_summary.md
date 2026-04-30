# 요약 보고서

상태: source of truth
기준일: 2026-04-28

## 한 줄 요약

`factory-a` Raspberry Pi 3-node Safe-Edge 기준선을 구축하고, GitOps 배포, Grafana 관제, Longhorn 저장소, 장애 복구 검증까지 완료했다.

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
중복 write 처리 정책 결정
데이터 공백 허용 범위 결정
writer node tag 또는 active writer guard 검토
M0 문서 전체 정합성 보정
AWS Hub / factory-b / factory-c 확장
```

## 후속 방향

1. `factory-a` 문서 정합성 완료
2. AWS EKS Hub 기준선 설계/구축
3. Hub-Spoke 연결
4. IoT Core / S3 데이터 플레인
5. Dashboard VPC 기반 관리자 관제 화면
6. Risk Twin dashboard
