# 테스트 체크리스트

상태: source of truth
기준일: 2026-04-28

## 목적

`factory-a` 운영 시작 시 반복해야 하는 상태 점검과 장애 테스트 기준을 기록한다.

## 시작 시 기본 점검

master에서 실행한다.

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

체크:

```text
[ ] master Ready
[ ] worker1 Ready
[ ] worker2 Ready
[ ] safe-edge-monitoring Synced / Healthy
[ ] safe-edge-ai-apps Synced / Healthy
[ ] monitoring pod Running
[ ] ai-apps target pod 3개 worker2 Running
[ ] image prepull DaemonSet worker1/worker2 Running
[ ] Longhorn volumes healthy
[ ] InfluxDB retention 1d
[ ] Grafana dashboard 갱신
[ ] failback cron이 worker2 대상 Pod 존재로 skip
```

## InfluxDB 최신 데이터 확인

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM environment_data ORDER BY time DESC LIMIT 3'

kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM ai_detection ORDER BY time DESC LIMIT 3'

kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM acoustic_detection ORDER BY time DESC LIMIT 3'
```

## 장애 테스트 공통 원칙

- 사용자가 물리 장애를 시작한다고 말하기 전까지 장애 테스트를 시작하지 않는다.
- 장애 발생 직후 첫 5분은 판정 보류 구간으로 둔다.
- worker2가 일시적으로 Ready처럼 보여도 5분 전에는 failback 성공으로 보지 않는다.
- 최종 성공은 대상 Pod 3개가 worker2에서 Running일 때만 인정한다.
- 테스트 후 InfluxDB 10초 bucket과 1초 bucket을 모두 확인한다.

대상 Pod:

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
```

## LAN 제거 테스트 기준

절차:

```text
1. 시작 전 상태와 InfluxDB 최신 timestamp 기록
2. worker2 LAN 제거
3. 10초 간격으로 node/pod/failback log 확인
4. 첫 5분 판정 보류
5. worker1 failover 완료 시각 기록
6. LAN 재연결
7. worker2 Ready 및 대상 Pod 3개 worker2 Running 확인
8. InfluxDB 10초/1초 bucket 분석
```

검증 완료 결과:

```text
Failover: 성공
Failback: 성공
10초 bucket 기준 실제 전환 구간 공백 없음
전환 구간 중복 write 후보 있음
```

## 전원 제거 테스트 기준

절차:

```text
1. 시작 전 상태와 InfluxDB 최신 timestamp 기록
2. worker2 전원 제거
3. 10초 간격으로 node/pod/failback log 확인
4. 첫 5분 판정 보류
5. worker1 failover 완료 시각 기록
6. worker2 전원 재연결
7. worker2 Ready 및 대상 Pod 3개 worker2 Running 확인
8. Longhorn degraded -> healthy 복귀 확인
9. InfluxDB 10초/1초 bucket 분석
```

검증 완료 결과:

```text
Failover: 성공
Failback: 성공
전원 제거 첫 관찰 -> worker2 NotReady: 약 42초
worker2 NotReady -> worker1 전체 Running: 약 32초
전원 제거 첫 관찰 -> worker1 전체 Running: 약 74초
전원 재연결 첫 관찰 -> worker2 Ready: 약 21초
worker2 Ready -> worker2 전체 Running: 약 1분 50초
전원 재연결 첫 관찰 -> worker2 전체 Running: 약 2분 11초
Longhorn degraded 발생 후 healthy 복귀
```

1초 bucket 연속 공백:

```text
failover environment_data 최대 65초
failover ai_detection 최대 72초
failover acoustic_detection 최대 75초
failback environment_data 최대 2초
failback ai_detection 최대 2초
failback acoustic_detection 최대 2초
```

## 남은 판단 항목

```text
[ ] 전원 장애 시 허용 가능한 데이터 공백 기준 결정
[ ] failback 전환 구간 중복 write 허용 여부 결정
[ ] active writer guard 또는 writer node tag 필요성 검토
[ ] Grafana에서 장애 시간대 공백/스파이크 시각 확인
```
