# 검토 및 발표 요약

상태: source of truth
기준일: 2026-04-28

## 핵심 메시지

`factory-a` Safe-Edge 기준선은 실제 구축과 장애 검증까지 완료됐다. Aegis-Pi의 다음 단계는 이 기준선을 AWS Hub/Risk Twin 구조로 확장하는 것이다.

## 발표 포인트

1. Safe-Edge 기준선 복구 완료
2. ArgoCD GitOps 배포 확인
3. Grafana 관제 확인
4. Longhorn 저장소 확인
5. LAN/전원 장애 테스트 완료
6. 데이터 공백과 중복 write 후보까지 측정

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
