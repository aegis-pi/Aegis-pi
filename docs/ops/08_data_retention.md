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
safe-edge-ai-snapshots
```

보존 정책:

```text
24시간 초과 jpg/jpeg/png 자동 삭제
```

구현 방식:

```text
safe-edge-integrated-ai Pod 안의 snapshot-cleanup sidecar
1시간마다 /app/snapshots를 검사
24시간 초과 이미지 삭제
```

확인:

```bash
kubectl -n ai-apps get pvc safe-edge-ai-snapshots
kubectl -n ai-apps get pod -l app=safe-edge-integrated-ai -o wide
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c ai-processor -- mount | grep snapshots
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c snapshot-cleanup -- ps
```

## 주의

- PVC 적용 전 Pod 내부 `/app/snapshots`에 있던 이미지는 새 PVC로 자동 이관되지 않는다.
- 앞으로 생성되는 이미지만 Longhorn PVC에 저장된다.
- retention 값 변경은 GitOps repo의 `ai-apps/values.yaml`에서 관리한다.
