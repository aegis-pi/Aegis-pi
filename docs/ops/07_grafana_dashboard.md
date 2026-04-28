# Grafana Dashboard 운영

상태: source of truth
기준일: 2026-04-28

## 목적

`factory-a` Grafana dashboard 구성 기준을 정리한다.

## 현재 주소

```text
Grafana UI: http://10.10.10.202
```

Dashboard 등록은 사용자가 Grafana UI에서 진행한다.

## Datasource

### InfluxDB

```text
URL: http://influxdb-svc.monitoring.svc.cluster.local:8086
Database: safe_edge_db
```

사용 목적:

```text
온도
습도
기압
화재 감지
넘어짐 감지
굽힘 감지
이상 소음 감지
```

### Prometheus

사용 목적:

```text
Node Exporter Full dashboard 1860
노드 CPU / Memory / Disk / Network 상태
```

## InfluxDB Panel 기준

| Panel | Measurement / Field | 표시 방식 |
| --- | --- | --- |
| 현장 온도 | `environment_data.temperature` | Time series |
| 현장 습도 | `environment_data.humidity` | Time series |
| 현장 기압 | `environment_data.pressure` | Time series |
| 화재 감지 | `ai_detection.fire_detected` | Stat |
| 넘어짐 감지 | `ai_detection.fallen_detected` | Stat |
| 굽힘 감지 | `ai_detection.bending_detected` | Stat |
| 이상 소음 감지 | `acoustic_detection.is_danger` | Stat |

## 환경 센서 Query

```sql
SELECT mean("temperature") FROM "environment_data" WHERE $timeFilter GROUP BY time($__interval) fill(null)
SELECT mean("humidity") FROM "environment_data" WHERE $timeFilter GROUP BY time($__interval) fill(null)
SELECT mean("pressure") FROM "environment_data" WHERE $timeFilter GROUP BY time($__interval) fill(null)
```

## AI / Sound 최근 N개 Query

기본 N은 10이다. 개수를 바꾸려면 `LIMIT 10`의 숫자를 수정한다.

```sql
SELECT "fire_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
SELECT "fallen_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
SELECT "bending_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
SELECT "is_danger" FROM "acoustic_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
```

Grafana에서 평균을 표시할 때는 panel Transform 또는 Reduce calculation에서 mean을 선택한다.

## Value Mapping

최근 N개 평균값을 아래 기준으로 매핑한다.

```text
0.0-0.2: 안전
0.3-0.7: 주의
0.8-1.0: 위험 레이블
```

Panel별 위험 레이블:

```text
fire_detected: 화재
fallen_detected: 넘어짐
bending_detected: 굽힘
is_danger: 감지된 소리 레이블 또는 이상 소음
```

## Prometheus 1860 Dashboard

Grafana UI에서 Import dashboard를 사용한다.

```text
Dashboard ID: 1860
Datasource: Prometheus
```

## 검증

```bash
kubectl -n monitoring get pod -o wide
kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SHOW MEASUREMENTS'
```

Grafana에서 확인:

```text
센서 time series 갱신
AI Stat 상태 변경
Node Exporter Full 1860 dashboard 표시
```
