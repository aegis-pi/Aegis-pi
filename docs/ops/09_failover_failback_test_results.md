# Failover / Failback 테스트 결과

상태: source of truth
기준일: 2026-04-28

## 목적

`factory-a`에서 수행한 worker2 장애 테스트 결과를 공식 운영 기록으로 남긴다.

## 공통 테스트 대상

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
```

정책:

```text
worker2 preferred affinity
tolerationSeconds: 30
worker1 failover
master OS cron 기반 Kubernetes-only failback
```

## LAN 제거 테스트

결과:

```text
Failover: 성공
Failback: 성공
10초 bucket 기준 실제 전환 구간 0-count bucket 없음
전환 구간 중복 write 후보 있음
pre-pull 효과 확인
```

핵심 타임라인:

```text
랜선 제거 후 첫 관찰: 13:34:49 KST
worker2 NotReady: 13:35:23 KST
worker1 전체 Running: 13:35:54 KST
초기 5분 판정 보류 종료: 13:40:10 KST
랜선 재연결 후 첫 관찰: 13:41:17 KST
worker2 Ready: 13:41:17 KST
worker2 전체 Running: 13:43:08 KST
```

## 전원 제거 테스트

결과:

```text
Failover: 성공
Failback: 성공
Longhorn degraded 발생 후 healthy 복귀
10초 bucket 기준 데이터 공백 확인
1초 bucket 기준 짧은 공백 후보 확인
failback 전환 구간 일부 중복 write 후보 확인
```

Failover 시간:

```text
전원 제거 첫 관찰 -> worker2 NotReady: 약 42초
worker2 NotReady -> worker1 전체 Running: 약 32초
전원 제거 첫 관찰 -> worker1 전체 Running: 약 74초
```

Failback 시간:

```text
전원 재연결 첫 관찰 -> worker2 Ready: 약 21초
worker2 Ready -> worker2 전체 Running: 약 1분 50초
전원 재연결 첫 관찰 -> worker2 전체 Running: 약 2분 11초
전원 재연결 첫 관찰 -> Longhorn healthy: 약 2분 22초
```

1초 bucket 연속 공백:

```text
failover environment_data: 최대 65초
failover ai_detection: 최대 72초
failover acoustic_detection: 최대 75초
failback environment_data: 최대 2초
failback ai_detection: 최대 2초
failback acoustic_detection: 최대 2초
```

## 분석 Query

10초 bucket:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(10s) fill(0)
```

1초 bucket:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(1s) fill(0)
```

동일 방식으로 `ai_detection.fire_detected`, `acoustic_detection.is_danger`도 확인한다.

## 남은 리스크

```text
데이터 공백 허용 범위 결정 필요
failback 전환 구간 중복 write 처리 정책 필요
writer node tag 또는 active writer guard 필요성 검토
Grafana에서 장애 시간대 공백/스파이크 시각 확인 필요
```
