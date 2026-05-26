# Monitoring / DB Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - Grafana PVC 권한 문제

### 📌 현상 요약

Grafana Pod가 Longhorn PVC에 쓰지 못해 Service endpoint가 비어 있었다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker 노드
- 네임스페이스: monitoring
- 관련 컴포넌트/버전: Grafana, Longhorn PVC, Kubernetes SecurityContext
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. Grafana를 Longhorn PVC와 함께 배포한다.
2. Grafana Service endpoint와 Pod log를 확인한다.
3. `/var/lib/grafana` 쓰기 권한을 확인한다.

### ✅ 기대 동작

Grafana가 PVC에 데이터를 쓰고 `/login`으로 정상 응답해야 한다.

### ❌ 실제 동작

```text
GF_PATHS_DATA='/var/lib/grafana' is not writable.
mkdir: can't create directory '/var/lib/grafana/plugins': Permission denied
```

### 🔍 시도한 것들

- [x] Grafana 기본 UID/GID 확인
- [x] Pod `securityContext`에 `fsGroup`, `runAsUser`, `runAsGroup` 추가
- [x] 새 ReplicaSet 재생성 확인
- [x] HTTP 302 `/login` 응답 확인

### 🚨 심각도

상

### 🗂️ 영역

Monitoring / Grafana / InfluxDB, Storage / Longhorn, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

Grafana 컨테이너 UID/GID와 Longhorn PVC 파일 권한이 맞지 않았다.

**해결 방법:**

Grafana Pod spec에 `fsGroup: 472`, `runAsUser: 472`, `runAsGroup: 472`를 추가한다.

**재발 방지:**

PVC를 사용하는 애플리케이션은 이미지의 실행 UID/GID와 `securityContext`를 함께 문서화한다.

## 🐛 트러블슈팅 리포트 - InfluxDB retention policy 1일 설정 중 shard duration 오류

### 📌 현상 요약

InfluxDB retention policy를 1일로 줄이는 과정에서 shard duration 제약 오류가 발생했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker 노드
- 네임스페이스: monitoring
- 관련 컴포넌트/버전: InfluxDB 1.x
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. `safe_edge_db`의 `autogen` retention policy를 1일로 변경한다.
2. InfluxDB query 결과를 확인한다.
3. shard group duration을 확인한다.

### ✅ 기대 동작

Retention duration이 1일로 변경되어 오래된 데이터가 정책에 따라 정리되어야 한다.

### ❌ 실제 동작

```text
retention policy duration must be greater than the shard duration
```

### 🔍 시도한 것들

- [x] 기존 shard group duration 확인
- [x] retention duration과 shard duration을 함께 지정
- [x] `autogen` duration과 shardGroupDuration 재확인

### 🚨 심각도

중

### 🗂️ 영역

Monitoring / Grafana / InfluxDB

### 💡 해결 방법

**근본 원인:**

기존 shard group duration이 `168h`였고, retention duration `1d`보다 커서 InfluxDB가 정책 변경을 거부했다.

**해결 방법:**

`ALTER RETENTION POLICY` 실행 시 `DURATION 1d`와 `SHARD DURATION 1h`를 함께 지정한다.

**재발 방지:**

InfluxDB retention 변경 절차에 shard duration 제약을 명시한다.

## 🐛 트러블슈팅 리포트 - AI 이벤트 스냅샷 보존 기간 혼동

### 📌 현상 요약

AI 이벤트 스냅샷 파일이 일정 시간이 지나면 `/app/snapshots`에서 사라진다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1, worker2
- 네임스페이스: ai-apps
- 관련 컴포넌트/버전: safe-edge-integrated-ai, hostPath, snapshot-cleanup sidecar
- 발생 시각: 2026-04-29

### 🔁 재현 순서

1. AI 이벤트를 발생시켜 snapshot 파일을 생성한다.
2. `/app/snapshots`와 hostPath 경로를 확인한다.
3. 24시간 초과 후 cleanup sidecar log를 확인한다.

### ✅ 기대 동작

운영 정책에 맞게 snapshot이 임시 저장되고 보관 기간 이후 삭제되어야 한다.

### ❌ 실제 동작

사용자가 장기 보관을 기대하면 24시간 후 snapshot이 사라진 것처럼 보일 수 있다.

### 🔍 시도한 것들

- [x] `/app/snapshots` mount 확인
- [x] `ai-apps` PVC가 없는 현재 기준 확인
- [x] snapshot-cleanup sidecar log 확인
- [x] retentionHours 설정 위치 확인

### 🚨 심각도

중

### 🗂️ 영역

Monitoring / Grafana / InfluxDB, AI / Hardware, Operations / DR

### 💡 해결 방법

**근본 원인:**

현재 운영 기준에서 snapshot은 Longhorn PVC가 아니라 node-local hostPath에 임시 저장되며, cleanup sidecar가 24시간 초과 파일을 삭제한다.

**해결 방법:**

`snapshotStorage.retentionHours` 값을 정책에 맞게 조정한다. 장기 보관은 node-local hostPath가 아니라 별도 비동기 전송 계층으로 처리한다.

**재발 방지:**

snapshot 보존 기간, 삭제 기준, 장기 보관 경로를 데이터 보존 문서에 명시한다.

