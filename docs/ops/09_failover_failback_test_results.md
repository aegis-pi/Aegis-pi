# Failover / Failback 테스트 결과

상태: source of truth
기준일: 2026-04-29

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

## Longhorn PVC 적용 후 재검증

2026-04-29에 AI snapshot 저장을 Longhorn RWO PVC `safe-edge-ai-snapshots`로 유지한 상태에서 추가 검증했다.

### test_03 k3s-agent 중지

```text
Failover: 부분 성공
Failback: 성공
bme280/audio: worker1 Running
AI: worker1 ContainerCreating, Multi-Attach 발생
원인: 기존 worker2 AI Pod가 RWO PVC를 사용 중인 것으로 남음
```

### test_04 랜선 제거

```text
Failover: 부분 성공
Failback: 성공
bme280/audio: worker1 Running
AI: 5분 이상 worker1 Running 실패
Longhorn: safe-edge-ai-snapshots unknown/attaching 관찰
최종: 랜선 재연결 후 worker2 Running, Longhorn healthy 복귀
```

### test_05 watchdog reboot fencing

```text
watchdog 설치: 성공
master API unreachable 감지: 성공
worker2 reboot fencing: 성공
bme280/audio worker1 failover: 성공
AI worker1 장기 failover: 미확인
worker2 자기 복구/failback: 성공
Longhorn 최종 healthy: 성공
worker1 최대 관찰: 1033m CPU, 5492Mi memory, 68%
```

해석:

```text
현재 watchdog reboot는 worker2 stale writer를 제거하고 self-healing을 빠르게 만드는 데 효과가 있다.
하지만 장기 worker1 AI failover를 보장하려면 worker2를 계속 격리하는 외부 power fencing 또는 전원 차단 상황을 별도로 검증해야 한다.
AI failover 실패 원인은 CPU/메모리가 아니라 Longhorn RWO PVC attach 제약이다.
```

### test_06 worker2 장기 격리 중 AI worker1 failover

```text
worker2 reboot 후 master API 차단 유지: 성공
worker2 NotReady 유지: 성공
bme280/audio worker1 failover: 성공
AI worker1 자동 failover: 실패
AI worker1 수동 stale Pod 정리 후 Running: 성공
worker2 복구/failback: 성공
Longhorn 최종 healthy: 성공
```

핵심 관찰:

```text
15:27:22 KST
safe-edge-integrated-ai: worker1 ContainerCreating
safe-edge-ai-snapshots: attaching/unknown
VolumeAttachment: worker2 attached=true
worker1 memory: 5472Mi, 67%

15:29:03 KST
기존 worker2 AI Pod 강제 삭제 후
safe-edge-integrated-ai: worker1 2/2 Running
safe-edge-ai-snapshots: attached/degraded, worker1
worker1 memory: 5472Mi, 67%

15:34:18 KST
worker2 복구 후
AI/audio/BME: worker2 Running
safe-edge-ai-snapshots: attached/healthy, worker2
worker2 memory: 3715Mi, 46%
```

해석:

```text
현재 구성에서 AI Longhorn RWO PVC는 worker2 장애 시 자동으로 worker1에 안정 attach되지 않는다.
실패 원인은 worker1 리소스 부족이 아니라 기존 worker2 AI Pod/VolumeAttachment가 stale 상태로 남는 것이다.
기존 writer가 fencing으로 확실히 종료됐음을 보장한 뒤 stale Pod/VolumeAttachment 정리를 수행하면 worker1 AI Running은 가능하다.
```
