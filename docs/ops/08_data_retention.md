# 데이터 보존 정책

상태: source of truth
기준일: 2026-04-28

## 목적

클라우드 마이그레이션 전까지 `factory-a` 로컬 저장소가 무한히 증가하지 않도록 데이터 보존 정책을 정리한다.

## InfluxDB

Database:

```text
safe_edge_db
```

Retention:

```text
1d
```

의미:

- 1일이 지난 InfluxDB 시계열 데이터는 DB 정책에 의해 삭제된다.
- Longhorn은 InfluxDB PVC의 현재 블록 상태를 복제한다.
- 따라서 InfluxDB에서 삭제된 데이터는 Longhorn replica에도 장기 보존되지 않는다.

확인:

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -execute 'SHOW RETENTION POLICIES ON safe_edge_db'
```

설정:

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -execute "ALTER RETENTION POLICY autogen ON safe_edge_db DURATION 1d REPLICATION 1 SHARD DURATION 1h DEFAULT"
```

## AI Event Snapshot

저장 위치:

```text
/app/snapshots
```

PVC:

```text
사용하지 않음
```

보존 정책:

```text
1시간마다 24시간 초과 jpg/jpeg/png 자동 삭제
매일 03:00 KST에 worker1/worker2 local snapshot directory 전체 비우기
```

구현 방식:

```text
safe-edge-integrated-ai Pod 안의 snapshot-cleanup sidecar
/app/snapshots는 node-local /var/lib/safe-edge/snapshots hostPath
1시간마다 /app/snapshots를 검사
24시간 초과 이미지 삭제

safe-edge-snapshot-daily-purge-worker1 / worker2 CronJob
매일 03:00 KST에 각 노드의 /var/lib/safe-edge/snapshots 하위 항목 전체 삭제
```

확인:

```bash
kubectl -n ai-apps get pvc
kubectl -n ai-apps get cronjob safe-edge-snapshot-daily-purge-worker1 safe-edge-snapshot-daily-purge-worker2
kubectl -n ai-apps get pod -l app=safe-edge-integrated-ai -o wide
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c ai-processor -- mount | grep snapshots
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c snapshot-cleanup -- ps
```

## 주의

- AI snapshot 이미지는 Longhorn에 직접 저장하지 않고 각 노드 local path에 임시 저장한다.
- AI 추론 결과는 InfluxDB에 기록되며, InfluxDB PVC를 통해 Longhorn에 저장된다.
- worker2에서 생성된 snapshot과 worker1 failover 중 생성된 snapshot은 서로 다른 노드 local path에 남는다.
- retention 값 변경은 GitOps repo의 `ai-apps/values.yaml`에서 관리한다.
