# Monitoring Dashboard Data Model

상태: source of truth
기준일: 2026-04-28

## 목적

현재 `factory-a` Grafana dashboard가 읽는 InfluxDB measurement와 field를 정의한다.

## InfluxDB

Database:

```text
safe_edge_db
```

Retention:

```text
1d
```

## Measurement

### environment_data

용도:
- BME280 환경 센서 데이터

Fields:

```text
temperature
humidity
pressure
```

Grafana 표시:

```text
Time series
```

### ai_detection

용도:
- 영상 기반 AI 감지 결과

Fields:

```text
fire_detected
fallen_detected
bending_detected
```

값:

```text
0 또는 1
```

Grafana 표시:

```text
최근 N개 평균 -> 안전 / 주의 / 위험 레이블
```

### acoustic_detection

용도:
- 소리 기반 이상 감지 결과

Fields:

```text
is_danger
```

값:

```text
0 또는 1
```

Grafana 표시:

```text
최근 N개 평균 -> 안전 / 주의 / 이상 소음
```

## 상태 매핑

```text
0.0-0.2: 안전
0.3-0.7: 주의
0.8-1.0: 위험 레이블
```

## Prometheus

Prometheus는 Node Exporter Full dashboard `1860`에서 사용한다.

용도:

```text
CPU
Memory
Disk
Network
Node up/down
```

## 후속 모델

AWS Hub/Risk Twin 단계에서는 아래 모델을 별도로 정의한다.

```text
FactorySummary
SensorObservation
DeviceStatus
PipelineStatus
RiskState
RecentLog
```

현재 `factory-a` dashboard에서는 위 후속 모델을 사용하지 않는다.
