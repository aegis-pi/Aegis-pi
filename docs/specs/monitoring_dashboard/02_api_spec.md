# Monitoring Dashboard API Spec

상태: draft
기준일: 2026-04-28

## 목적

현재 `factory-a` dashboard와 후속 Hub/Risk Twin dashboard의 API 경계를 구분한다.

## 현재 Factory-A 기준

현재 dashboard는 별도 API를 사용하지 않는다.

```text
Grafana -> InfluxDB
Grafana -> Prometheus
```

따라서 현재 운영 기준 API는 없다.

## 현재 Query 기준

환경 센서:

```sql
SELECT mean("temperature") FROM "environment_data" WHERE $timeFilter GROUP BY time($__interval) fill(null)
SELECT mean("humidity") FROM "environment_data" WHERE $timeFilter GROUP BY time($__interval) fill(null)
SELECT mean("pressure") FROM "environment_data" WHERE $timeFilter GROUP BY time($__interval) fill(null)
```

AI/Sound 최근 N개:

```sql
SELECT "fire_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
SELECT "fallen_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
SELECT "bending_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
SELECT "is_danger" FROM "acoustic_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
```

## 후속 Dashboard VPC API 후보

아래 API는 아직 구현 대상이 아니다. AWS Hub/Risk Twin 및 Dashboard VPC 단계에서 다시 검토한다.

Dashboard API는 Spoke K3s, ArgoCD, Processing VPC 내부 서비스를 직접 호출하지 않는다. processed S3와 latest status store를 read-only로 조회한다.

```text
GET /api/factories/summary
GET /api/factories/{factory_id}/sensors
GET /api/systems/abnormal
GET /api/logs/recent
GET /api/pipeline/status
```

예상 접근 경로:

```text
Route53 -> ALB -> WAF/Auth -> Dashboard API -> latest status store / S3 processed
```

목표 반영 지연:

```text
일반 상태 변화: 10~35초
장애 판정: 40~60초
```

## 현재 판단

- `factory-a` 운영 dashboard는 Grafana datasource query로 충분하다.
- API spec은 M6 Risk Twin / Dashboard VPC 구현 시 source of truth로 승격한다.
- 현재는 후속 설계 초안으로만 유지한다.
