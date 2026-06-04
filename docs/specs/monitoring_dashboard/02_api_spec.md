# Monitoring Dashboard API Spec

상태: draft
기준일: 2026-06-04

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

## 후속 Data / Dashboard VPC API 후보

아래 API는 아직 구현 대상이 아니다. AWS Hub/Risk Twin 및 1번 Data / Dashboard VPC 단계에서 다시 검토한다.

Dashboard API는 Spoke K3s, ArgoCD, Control / Management VPC의 EKS API, Tailscale 관리망을 직접 호출하지 않는다. Factory 상태는 DynamoDB LATEST/GRAPH#5M/HISTORY#STATE와 S3 processed/processed_agg를 조회한다. Cloud infra 상태는 CloudWatch/EKS/Kubernetes/S3를 직접 조회하지 않고 DynamoDB `pk=CLOUD#infra`, `sk=LATEST` read model을 조회한다.

```text
GET /api/factories/summary
GET /api/factories/{factory_id}/sensors
GET /api/systems/abnormal
GET /api/logs/recent
GET /api/pipeline/status
GET /api/cloud-infra/status
GET /api/alerts/status
```

예상 접근 경로:

```text
Route53 -> ALB -> WAF/Auth -> Dashboard API -> DynamoDB LATEST/GRAPH#5M/HISTORY#STATE / S3 processed/processed_agg
```

Cloud infra status:

```text
GET /api/cloud-infra/status
  -> DynamoDB GetItem pk=CLOUD#infra sk=LATEST
  -> 초기 구현은 LATEST 구조를 그대로 반환
```

초기 응답 shape:

```json
{
  "schema_version": "cloud-infra-status-v1",
  "updated_at": "2026-06-01T15:30:00Z",
  "fast_updated_at": "2026-06-01T15:30:00Z",
  "slow_updated_at": "2026-06-01T15:25:00Z",
  "overall_status": "normal",
  "fast": {},
  "slow": {}
}
```

UI가 실제로 쓰는 card/summary 필드가 안정화되면 backend에서 compact response를 추가할 수 있지만, collector가 만든 `LATEST`를 source of truth로 둔다.

Alert status:

```text
GET /api/alerts/status
  -> DynamoDB Query/GetItem pk=ALERT#{scope}
  -> RiskAlertDispatcher cooldown/dedupe state 조회
```

이 API는 필수 MVP 화면 API가 아니라 운영 보조 후보이다. 실제 Slack 전송 내역의 장기 이력은 별도 event store가 없으며, `ALERT#` item은 현재 cooldown/dedupe state만 의미한다.

목표 반영 지연:

```text
일반 상태 변화: 10~35초
pipeline warning: 60초 초과
pipeline critical: 120초 초과
```

## 현재 판단

- `factory-a` 운영 dashboard는 Grafana datasource query로 충분하다.
- API spec은 M6 Risk Twin / Data / Dashboard VPC 구현 시 source of truth로 승격한다.
- 현재는 후속 설계 초안으로만 유지한다.
