# M4. 데이터 플레인 - `factory-a` 단일 Spoke 기준

> **마일스톤 목표**: `factory-a` Spoke의 실제 raw/log/status 데이터가 표준 JSON으로 변환되고, IoT Core를 거쳐 S3 raw까지 실제로 적재되는 것을 검증한다.
> M2(Hub-Spoke 연결) 완료 후 M3(배포 파이프라인)과 병렬로 진행 가능하다.  
> 이 마일스톤이 완료되어야 M6(Risk Twin)에서 실데이터 기반 Risk Score 계산이 가능해진다.
> Dashboard VPC가 Spoke에 직접 붙지 않으므로 노드, 장치, 워크로드 상태도 Edge 데이터 플레인이 송신한다.

---

## 2026-05-13 멘토링 반영: S3 raw와 latest status 역할 분리

### 기존 초안

기존 M4 초안은 `factory-a` 데이터가 Edge 송신 컴포넌트 -> IoT Core -> S3까지 실제로 흐르는 것을 먼저 검증하는 구조였다. 이 초안은 IoT Core와 S3 raw 적재를 검증하는 기준으로 유지한다.

```text
입력 모듈
  -> adapter/publisher
  -> IoT Core
  -> S3 raw
```

### 변경 이유

멘토링에서는 Dashboard의 "실시간성"을 수치로 정의해야 하고, S3 raw만으로 latest status를 설명하면 준실시간 관제 근거가 약하다는 피드백이 있었다. 또한 factory별 메시지 주기, payload 크기, 수신 성공률, 지연시간을 검증 기준으로 잡아야 한다.

### 보강 방향

S3 raw 적재 흐름은 유지하되, Dashboard가 조회할 최신 상태는 DynamoDB LATEST/HISTORY#STATE와 S3 processed 경로로 반영한다.

```text
factory-a-log-adapter / edge-iot-publisher
  -> IoT Core
  -> Lambda data processor
  -> DynamoDB LATEST/HISTORY#STATE
  -> S3 processed
  -> Dashboard API/Web

동시에:

IoT Core
  -> S3 raw
  -> 재처리 / 감사 / 일일 리포트
```

M4 문서의 기존 이슈들은 삭제하지 않고, 구현 시 아래 항목을 추가 검증 대상으로 둔다.

- source_type별 payload 크기 예상값
- factory별 전송 주기
- 초당 메시지 수
- IoT Core 수신 후 DynamoDB LATEST/HISTORY#STATE 반영 지연
- 10분 이상 연속 송신 기준 수신 성공률/실패율
- S3 raw와 DynamoDB/S3 processed 양쪽 경로 검증

---

## 2026-05-15 수정 방향: Edge 변환/전송 분리

M3에서는 아직 실제 Edge data-plane 로직이 확정되지 않아 manifest tag 자동 갱신과 end-to-end 자동 배포 검증을 보류했다. 따라서 M4에서 실제 데이터 플레인 컴포넌트를 먼저 확정한다.

M4의 Edge side는 기존 단일 Edge Agent 구상이 아니라 두 기능으로 분리한다.

```text
factory-a K3s에서 실행:
  factory-a-log-adapter
    실제 raw/log/status data
    -> canonical JSON
    -> local spool/outbox

  edge-iot-publisher
    local spool/outbox canonical JSON
    -> AWS IoT Core MQTT publish
    -> IoT Rule
    -> S3 raw

배포 제어:
  Hub EKS ArgoCD
    -> aegis-pi-gitops
    -> factory-a K3s Application sync
```

핵심 경계:

- 실행 위치는 각 factory K3s다.
- 배포 제어는 Hub EKS의 ArgoCD가 담당한다.
- `factory-a-log-adapter`는 factory-a 실제 데이터를 표준 JSON으로 바꾸는 역할만 담당한다.
- `edge-iot-publisher`는 표준 JSON을 IoT Core로 전달하는 역할만 담당한다.
- M5의 `factory-b/c`는 실제 로그 adapter 대신 dummy generator가 같은 표준 JSON을 생성하고, `edge-iot-publisher`는 공통으로 재사용한다.
- M4 완료 판정에는 S3 raw object 실제 적재와 body schema 검증이 반드시 포함된다.

## 2026-05-18 수정 방향: Issue 1 데이터 계약 확정

M4 Issue 1에서는 현재 문서 구조를 유지하되 구현자가 바로 사용할 수 있도록 계약을 명확히 닫는다.

- canonical JSON source of truth는 `docs/specs/iot_data_format.md`로 둔다.
- 저장 계약 source of truth는 `docs/specs/data_storage_pipeline.md`로 둔다.
- Edge data-plane 인스턴스 식별 필드는 legacy `agent_instance_id`가 아니라 `data_plane_instance_id`를 사용한다.
- S3 raw object body는 canonical JSON과 같은 계약을 따른다.
- Dashboard current state는 S3 `latest/`가 아니라 DynamoDB LATEST/HISTORY#STATE를 기준으로 한다.
- 정식 JSON Schema 기반 기계 검증은 adapter/publisher 샘플 payload가 안정화된 뒤 추가한다.

---

## Issue 1 - [데이터/Schema] Raw/Processed 데이터 계약 확정

### 🎯 목표 (What & Why)

`입력 모듈 또는 raw/log adapter -> canonical JSON -> IoT publisher -> IoT Core/S3/Lambda` 사이의 데이터 구조를 고정한다.
이 스키마가 확정되어야 `factory-a-log-adapter`, `dummy-data-generator`, `edge-iot-publisher`, Lambda data processor가 모두 같은 포맷을 기준으로 구현된다.
라즈베리파이와 VM의 입력 차이는 이 스키마 안에서 `input_module_type`으로만 구분한다.

2026-05-18 기준 표준 입력 스키마 source of truth는 `docs/specs/iot_data_format.md`다.
최종 source type은 `factory_state`, `infra_state` 두 개로 단순화한다.

### ✅ 완료 조건 (Definition of Done)

- [x] 필수 공통 필드 확정
  - `factory_id` (string)
  - `node_id` (string: `master` / `worker1` / `worker2` / `cluster`)
  - `source_timestamp` (ISO 8601 UTC)
  - `published_at` (ISO 8601 UTC)
  - `message_id` (idempotency key)
  - `source_type` (`factory_state` / `infra_state`)
  - `environment_type` (`physical-rpi` / `vm-mac` / `vm-windows`)
- [x] source_type별 payload 구조 확정 및 샘플 작성
  - `factory_state`: 3초 주기, 온도/습도/기압 평균과 AI score 평균
  - `infra_state`: 20초 주기, heartbeat, cluster, nodes, workloads, devices
  - `pipeline_status`: Hub derived 상태 (Edge가 직접 보내지 않음)
- [x] 선택 필드 `null` 허용 원칙 명시
- [x] 스키마 예시 JSON 작성 및 관련 입력/데이터 모델 문서에 반영
- [x] local spool/outbox file 계약 확정
  - file content는 canonical JSON 한 건
  - 파일명은 `message_id` 기반
  - publisher 성공 시 ack/delete 원칙 정의
- [x] S3 raw object body가 canonical JSON과 동일한지 여부 확정
- [x] S3 processed/latest 계약 초안 작성

```json
{
  "schema_version": "0.1.0",
  "message_id": "factory-a:factory_state:worker2:2026-05-14T01:00:00Z",
  "factory_id": "factory-a",
  "node_id": "worker2",
  "environment_type": "physical-rpi",
  "input_module_type": "sensor",
  "source_type": "factory_state",
  "source_timestamp": "2026-05-14T01:00:00Z",
  "published_at": "2026-05-14T01:00:01Z",
  "data_plane_instance_id": "edge-iot-publisher-7f8c9d",
  "payload": {
    "aggregation_window_seconds": 3,
    "sensor": {
      "sample_count": 5,
      "temperature_celsius_avg": 24.6,
      "humidity_percent_avg": 58.1,
      "pressure_hpa_avg": 1012.7
    },
    "ai_result": {
      "sample_count": 3,
      "fire_score": 0.0,
      "fall_score": 0.6667,
      "bend_score": 0.3333,
      "abnormal_sound": "none"
    }
  }
}
```

### 🔍 Acceptance Criteria

- 스키마 JSON 예시가 관련 입력/데이터 모델 문서에 source_type별로 작성됨
- adapter/generator/publisher/Lambda 구현 시 이 스키마를 기준으로 바로 개발 가능한 수준
- `pipeline_status`가 Hub derived임이 명확히 구분됨
- S3 raw key와 object body의 추적 기준이 `message_id`로 연결됨

### 확정 결과

- `factory_state`, `infra_state` 두 source type만 Edge에서 publish한다.
- envelope 필드는 모두 필수이며, payload 하위 수집 실패는 명시적 `null`, `false`, `unknown`, 빈 배열로 표현한다.
- local spool/outbox 기본 경로는 `/var/lib/aegis/outbox`이며 파일명은 `{message_id}.json`이다.
- adapter/generator는 임시 파일 작성 후 atomic rename으로 outbox에 넣고, publisher는 IoT Core publish 성공 후 파일을 삭제한다.
- publish 실패 시 파일은 유지하며 재시도한다. schema validation 실패 파일은 `quarantine/`으로 이동한다.
- S3 raw object body는 canonical JSON과 같은 계약을 따른다.
- Lambda data processor는 DynamoDB LATEST/HISTORY#STATE와 S3 processed를 갱신한다.
- Dashboard current state는 DynamoDB LATEST/HISTORY#STATE를 기준으로 조회한다.

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: `factory_state`/`infra_state` canonical JSON 계약, null 처리, local spool/outbox handoff, S3 raw body, DynamoDB LATEST/HISTORY#STATE와 S3 processed 저장 계약을 확정했다.
- 변경/확인: `docs/specs/iot_data_format.md`, `docs/specs/data_storage_pipeline.md`, `infra/foundation/iot_rule.tf`, `infra/foundation/README.md`, `docs/issues/M4_data-plane.md`
- 검증: `terraform fmt -check`, `terraform validate`. 실제 adapter/publisher/Lambda 동작 검증은 M4 Issue 2~8에서 진행한다.
- 후속: M4 Issue 2에서 `factory-a-log-adapter` 구현을 시작하고, canonical JSON 파일을 outbox에 생성하는 로컬 검증을 진행한다.

---

## Issue 2 - [데이터/Adapter] `factory-a` raw/log -> JSON 변환 로직 구현

### 🎯 목표 (What & Why)

`factory-a` 라즈베리파이 환경에서 실제 raw/log/status 데이터를 읽고 표준 JSON으로 변환하는 adapter를 구현한다.
이 이슈는 IoT Core 전송을 하지 않는다. 변환 결과는 local spool/outbox에 canonical JSON 파일로 남긴다.

### ✅ 완료 조건 (Definition of Done)

- [x] adapter 구현 언어/프레임워크 결정 (Python 표준 라이브러리 기반, 라즈베리파이 ARM64 호환)
- [x] factory-a 실제 입력 source 확정
  - `factory_state`: InfluxDB `safe_edge_db` query
  - `infra_state`: Kubernetes API status query
  - InfluxDB 접근: `http://influxdb-svc.monitoring.svc.cluster.local:8086`
  - database: `safe_edge_db`
- [x] 수집 대상 구현
  - BME280 온도/습도/기압 평균 (`factory_state`)
  - AI fire/fall/bend 최근 window 평균 score (`factory_state`)
  - 이상소음 대표 라벨 (`factory_state`)
  - 노드 상태, CPU/memory/disk usage (`infra_state`)
  - BME280, 카메라, 마이크 장치 상태 (`infra_state`)
  - AI/audio/BME Pod 상태와 restart count (`infra_state`)
  - adapter heartbeat와 마지막 spool write 결과 (`infra_state`)
- [x] 수집 데이터 → 표준 입력 스키마 변환 로직
- [x] canonical JSON file을 local spool/outbox에 쓰는 로직
- [x] 수집 주기 설정
  - 확정 초기값: `factory_state` 3초, `infra_state` 20초

### 🔍 Acceptance Criteria

- 로컬 실행 또는 개발 환경 기준으로 수집/변환 로직 동작 확인
- 표준 스키마 형식의 JSON file 생성 확인
- 센서값/시스템 상태가 source_type별로 올바르게 분리됨 확인
- IoT Core 연결 없이도 spool/outbox에 publish 후보 JSON이 쌓임 확인

### 입력 Source 확정

M4 Issue 2의 adapter는 기존 Safe-Edge workload를 대체하지 않고 읽기 전용으로 동작한다.

```text
factory_state:
  InfluxDB Service DNS -> safe_edge_db
  environment_data 최근 3초 평균
  ai_detection 최근 3초 평균
  acoustic_detection 최근 3초 요약

infra_state:
  Kubernetes API
  node Ready 상태
  monitoring/ai-apps workload Running/Ready/restart_count/node_id
  device summary는 관련 workload 상태와 최근 InfluxDB write timestamp로 추론
```

adapter Pod 환경변수 기본값:

```text
AEGIS_FACTORY_ID=factory-a
AEGIS_ENVIRONMENT_TYPE=physical-rpi
AEGIS_INPUT_MODULE_TYPE=sensor
AEGIS_INFLUXDB_URL=http://influxdb-svc.monitoring.svc.cluster.local:8086
AEGIS_INFLUXDB_DATABASE=safe_edge_db
AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox
```

`acoustic_detection`은 2026-05-18 실제 `factory-a` InfluxDB 확인 기준으로 아래 구조를 사용한다.

```text
measurement: acoustic_detection
fields:
  confidence: float
  is_danger: integer
tags:
  event_type
  location
  node
```

M4 Issue 2에서는 스키마 호환성을 위해 `payload.ai_result.abnormal_sound` 문자열 필드를 유지한다. adapter는 최근 3초 window에서 `acoustic_detection`을 집계하고, `sum(is_danger) > 0`이면 대표 `event_type`을 `abnormal_sound`에 넣는다. 대표 `event_type`이 비어 있거나 `None`이면 `"abnormal_sound"`를 넣는다. `sum(is_danger) == 0`이거나 샘플이 없으면 `"none"`을 넣는다. `confidence` 평균/최댓값은 초기 canonical JSON에는 별도 필드로 싣지 않고, 후속 스키마 보정에서 `audio_result` 확장 후보로 둔다.

초기 구현에서는 `/dev/i2c-1`, camera, microphone 장치에 직접 접근하지 않는다. 장치 직접 접근은 기존 `bme280-sensor`, `safe-edge-integrated-ai`, `safe-edge-audio`와 충돌할 수 있으므로 M4 MVP 범위에서 제외한다.

CPU, memory, disk usage는 Kubernetes metrics API 또는 Prometheus 연동이 확인되기 전까지 `null` 허용 정책을 따른다.

### 보조/후속 Source 기준

M4 Issue 2의 primary source는 InfluxDB + Kubernetes API다. 다른 방식은 아래처럼 범위를 제한한다.

| 방식 | M4 기준 | 이유 |
| --- | --- | --- |
| Pod logs | fallback/debug only | 로그 포맷 변경에 취약하므로 canonical JSON의 primary source로 쓰지 않는다. 수집 실패 원인 진단에만 사용한다. |
| 기존 workload shared output | future candidate | 앱이 structured JSON file, shared volume, HTTP endpoint를 제공하도록 바꾸는 방식은 좋지만 기존 Safe-Edge workload 변경이 필요하므로 M4 초기 구현에서는 제외한다. |
| direct device access | out of scope | `/dev/i2c-1`, camera, microphone을 adapter가 직접 잡으면 기존 BME/AI/audio Pod와 충돌할 수 있다. |

따라서 adapter 구현은 먼저 InfluxDB query, Kubernetes API query, outbox write에 집중한다. fallback log parsing이나 기존 workload 수정은 M4 Issue 2 완료 조건에 포함하지 않는다.

### 2026-05-18 구현 메모

- 구현 위치: `apps/factory-a-log-adapter/`
- entrypoint: `factory_a_log_adapter.py`
- 실행 형태: `--once factory_state`, `--once infra_state`, `--once all`, `--loop`
- InfluxDB 접근: HTTP `/query` API 직접 호출
- Kubernetes 접근: in-cluster ServiceAccount API 우선, 로컬 개발 시 `kubectl` fallback
- outbox write: `outbox/tmp` 임시 파일 작성 후 `{message_id}.json`으로 atomic rename
- `--loop` 기본 주기: `factory_state` 3초, `infra_state` 20초
- master host 직접 검증 시 InfluxDB Service DNS 대신 NodePort `AEGIS_INFLUXDB_URL=http://127.0.0.1:30086` 사용
- 실제 검증 결과:
  - `factory_state` JSON 생성 확인
  - `abnormal_sound`가 현재 acoustic 정상 상태에서 `"none"`으로 생성됨 확인
  - `infra_state` JSON 생성 확인
  - `/tmp/aegis-outbox-test`에 `factory_state`, `infra_state` outbox 파일 생성 확인

남은 작업:

- 실제 K3s 배포용 RBAC/Config/volume 요구사항을 M4 Issue 4에서 chart에 반영

검증:

- `python3 -m unittest discover -s apps/factory-a-log-adapter/tests`

---

## Issue 3 - [데이터/Publisher] JSON -> IoT Core 전송 로직 구현

### 🎯 목표 (What & Why)

Issue 2의 adapter가 만든 canonical JSON을 local spool/outbox에서 읽어 AWS IoT Core로 publish하는 공통 publisher를 구현한다.
이 publisher는 `factory-a`뿐 아니라 M5의 `factory-b/c` dummy generator와도 재사용한다.

### ✅ 완료 조건 (Definition of Done)

- [x] local spool/outbox scan 로직 구현
- [x] AWS IoT Core MQTT publish 구현
  - topic: `aegis/{factory_id}/{source_type}`
  - mTLS certificate/key/CA file 사용
- [x] publish 성공 시 ack/delete 처리
- [x] publish 실패 시 retry/backoff 처리
- [x] 중복 publish 가능성 및 `message_id` idempotency 기준 문서화
- [x] publisher heartbeat/logging 구현

### 🔍 Acceptance Criteria

- sample canonical JSON file을 spool에 넣으면 IoT Core topic으로 publish됨
- publish 성공 후 spool file이 ack/delete됨
- IoT Core 장애 또는 인증 실패 시 file이 삭제되지 않고 재시도 대상으로 남음
- publisher는 factory별 인증서 Secret만 바꾸면 재사용 가능

### 2026-05-18 구현 메모

- 구현 위치: `apps/edge-iot-publisher/`
- entrypoint: `edge_iot_publisher.py`
- MQTT 구현: Python 표준 라이브러리 기반 MQTT 3.1.1 QoS0 over TLS/mTLS
- topic: `aegis/{factory_id}/{source_type}`
- outbox scan: outbox root의 `*.json`만 대상으로 하며 `tmp/`, `quarantine/` 하위 파일은 무시
- publish 직전 `published_at`, `data_plane_instance_id`는 publisher가 덮어씀
- 성공 시 local outbox file 삭제
- publish 실패 시 파일 유지 후 loop mode에서 backoff 재시도
- invalid JSON/schema file은 `outbox/quarantine/`으로 이동
- idempotency 기준은 canonical JSON의 `message_id`; publish 실패와 프로세스 재시작 사이에는 QoS0 특성상 중복 publish 가능성이 있으므로 cloud-side Lambda/DynamoDB/S3 처리에서 `message_id` 기준 중복 처리를 유지한다.
- logging/heartbeat: loop 실행 중 publish 성공/실패 로그를 stdout/stderr에 출력한다. 별도 heartbeat message는 `infra_state.payload.heartbeat`에 포함하는 계약을 유지한다.

검증:

- `python3 -m unittest discover -s apps/edge-iot-publisher/tests`

남은 실제 환경 검증:

- factory-a IoT 인증서 Secret 마운트 후 실제 AWS IoT Core topic publish 확인
- publish 성공 후 S3 raw object 적재 확인은 Issue 5에서 수행

---

## Issue 4 - [데이터/Container/GitOps] adapter/publisher 이미지화 및 K3s 배포

### 🎯 목표 (What & Why)

`factory-a-log-adapter`와 `edge-iot-publisher`를 ARM64 이미지로 만들고, Hub EKS ArgoCD가 factory-a K3s에 배포할 수 있게 GitOps chart/values를 확장한다.

### ✅ 완료 조건 (Definition of Done)

- [x] `factory-a-log-adapter` ARM64 Docker image 빌드 가능
- [x] `edge-iot-publisher` ARM64 Docker image 빌드 가능
- [x] ECR repository/tag 전략 확정
  - `aegis/factory-a-log-adapter`, `aegis/edge-iot-publisher`
- [x] GitOps chart/values 확장
  - factory-a: adapter enabled, publisher enabled
  - shared spool volume mount
  - IoT certificate Secret mount
- [ ] Hub EKS ArgoCD ApplicationSet이 factory-a K3s에 두 파드를 배포
- [x] `worker-2` 또는 대상 node 배치 기준 정리
- [x] 필요한 Secret / Config / volume / device mount 요구사항 정리

### 🔍 Acceptance Criteria

- ECR에 두 이미지가 push됨
- ArgoCD `aegis-spoke-factory-a` Application이 두 workload를 관리함
- factory-a K3s에서 adapter/publisher Pod가 `Running`
- shared spool/outbox volume을 통해 adapter -> publisher handoff가 가능

### 2026-05-18 구현 메모

- Helm chart: `charts/aegis-spoke`
- factory-a values: `envs/factory-a/values.yaml`
- 배포 namespace: 기존 IoT Secret 재사용을 위해 `ai-apps`
- workload:
  - `aegis-spoke-factory-a-log-adapter`
  - `aegis-spoke-edge-iot-publisher`
- shared outbox: Longhorn PVC `aegis-spoke-outbox`, mount path `/var/lib/aegis/outbox`
- placement: `kubernetes.io/hostname=worker2`
- IoT Secret: `aws-iot-factory-a-cert`
  - files: `certificate.pem.crt`, `private.pem.key`, `AmazonRootCA1.pem`
  - endpoint: `endpoint.txt`
- RBAC: adapter가 Kubernetes node/pod status를 읽을 수 있도록 ServiceAccount + ClusterRole/ClusterRoleBinding 추가
- Docker/CI:
  - `apps/factory-a-log-adapter/Dockerfile`
  - `apps/edge-iot-publisher/Dockerfile`
  - `.github/workflows/build-push.yaml` matrix로 ARM64 image build/push
- ECR:
  - `aegis/factory-a-log-adapter`
  - `aegis/edge-iot-publisher`
  - deployment tag는 `sha-<7-char-git-sha>`, `main`/`latest`는 moving debug tag

검증:

- `helm lint charts/aegis-spoke -f envs/factory-a/values.yaml`
- `helm template aegis-spoke charts/aegis-spoke --namespace ai-apps -f envs/factory-a/values.yaml`
- `terraform -chdir=infra/foundation fmt -check`

제약:

- 현재 로컬 Docker Desktop WSL integration이 비활성화되어 있어 실제 `docker buildx build`는 실행하지 못했다.
- `terraform validate`는 로컬 AWS provider plugin handshake 실패로 완료하지 못했다. 수정한 Terraform 파일은 `fmt -check`까지 확인했다.
- `kubectl apply --dry-run=client`는 현재 kubeconfig의 EKS API DNS 조회가 sandbox에서 차단되어 완료하지 못했다. Helm lint/template은 통과했다.

남은 실제 환경 검증:

- foundation Terraform apply로 신규 ECR repository 생성
- GitHub Actions로 두 image push
- values의 `sha-placeholder`를 실제 `sha-...` tag로 갱신
- Hub ArgoCD ApplicationSet sync 후 factory-a K3s에서 두 Pod `Running` 확인

---

## Issue 5 - [데이터/S3] IoT Core → S3 적재 확인 (경로 파티셔닝 포함)

### 🎯 목표 (What & Why)

`factory-a` K3s에서 생성된 canonical JSON이 `edge-iot-publisher`를 통해 IoT Core로 전송되고, IoT Rule에 의해 S3 raw 경로에 실제 적재되는지 확인한다.
`factory_id` / `source_type` / 날짜 기반 파티셔닝과 object body schema를 모두 검증한다. 이 검증 없이는 M4를 완료로 보지 않는다.

### ✅ 완료 조건 (Definition of Done)

- [x] factory-a K3s publisher가 IoT Core topic으로 메시지 publish
- [x] IoT Rule Action이 S3에 메시지 적재하는 것 확인
- [x] 경로 파티셔닝 규칙 적용 확인
  - `s3://aegis-bucket-data/raw/factory-a/factory_state/yyyy=2026/mm=05/dd=18/<message_id>.json`
  - `s3://aegis-bucket-data/raw/factory-a/infra_state/yyyy=2026/mm=05/dd=18/<message_id>.json`
  - 현재 Terraform IoT Rule은 MQTT topic `aegis/factory-a/{source_type}`의 세 번째 segment를 `source_type`으로 사용한다.
- [x] `source_type`별 경로가 올바르게 분리되어 적재되는지 확인
- [x] S3 object body가 canonical JSON schema와 일치하는지 확인
- [x] `message_id`로 spool file, MQTT publish, S3 object를 추적할 수 있는지 확인
- [x] S3 적재 실패 시 IoT Rule 오류 로그 확인 방법 정의

### 🔍 Acceptance Criteria

- S3 콘솔에서 `raw/factory-a/factory_state/`, `raw/factory-a/infra_state/` 경로에 파일 적재 확인
- 적재된 파일 내용이 표준 스키마와 일치
- 두 `source_type` 경로에 파일이 분리 적재됨
- `aws s3api get-object` 또는 동등한 명령으로 object body JSON 필수 필드를 확인
- 최소 1건 이상의 실제 factory-a generated message가 S3 raw에 적재됨

### 2026-05-18 검증 결과

- 검증 날짜: 2026-05-18
- image: `sha-f71a104`
- 배포: 초기 검증은 `helm template | kubectl apply`로 수행했고, 2026-05-19 기준 정식 경로는 Hub ArgoCD ApplicationSet(`aegis-spoke-factory-a`) 배포다.
- 결과:
  - `factory_state`, `infra_state` 양쪽 S3 경로에 파일 적재 확인
  - canonical JSON 필수 필드 전부 확인 (envelope + payload.ai_result 포함)
  - `ai_result`는 실제 InfluxDB 데이터 기반 (fire/fall/bend 모두 0.0, abnormal_sound: "none")
  - IoT Rule 경로 파티셔닝: `yyyy=2026/mm=05/dd=18` 정상 적용

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: factory-a K3s에서 `factory-a-log-adapter`와 `edge-iot-publisher`를 배포하고 S3 raw 경로에 `factory_state`, `infra_state` 데이터가 실제 적재되는 것을 검증했다.
- 변경/확인: `apps/factory-a-log-adapter/`, `apps/edge-iot-publisher/`, `charts/aegis-spoke/`, `envs/factory-a/values.yaml`, `infra/foundation/ecr.tf`, `.github/workflows/build-push.yaml`
- 검증: S3 object body canonical JSON 필드 일치, 경로 파티셔닝 정상
- 후속: M4 Issue 6 Lambda data processor 구현 및 검증 완료. 다음은 M6 Risk Twin/Dashboard 구현

---

## Issue 6 - [데이터/Lambda] IoT Core Lambda data processor 구현

### 🎯 목표 (What & Why)

IoT Core 수신 메시지를 Lambda data processor로 처리해 정규화, Risk 계산, `pipeline_status` 계산, DynamoDB/S3 processed 저장까지 수행한다.
S3 raw는 IoT Rule로 원본 보존을 유지하고, Dashboard 현재 상태 조회는 DynamoDB LATEST/HISTORY#STATE를 기준으로 한다.

### ✅ 완료 조건 (Definition of Done)

- [x] Lambda data processor 구현
  - [x] IoT Core Rule 또는 메시지 라우팅으로 Lambda 호출
  - [x] 필드 정규화 (타입 변환, null 처리, 단위 통일)
  - [x] Risk Score 계산
  - [x] `pipeline_status` 계산
  - [x] DynamoDB LATEST overwrite/update
  - [x] DynamoDB HISTORY#STATE TTL item 저장
  - [x] S3 processed 처리 결과 저장
- [x] Lambda IAM 권한 설정
  - [x] DynamoDB read/write
  - [x] S3 processed write
  - [x] 필요 시 S3 raw read
- [x] 정규화 실패 데이터 처리 원칙 정의 (스킵 또는 오류 로그)
- [ ] Dashboard VPC 조회용 DynamoDB/S3 processed 계약 반영 (Dashboard VPC 후속 단계)

### 🔍 Acceptance Criteria

- [x] IoT Core 메시지 수신 후 Lambda가 자동 실행됨
- [x] `factory_state` 처리 후 DynamoDB LATEST의 `factory_state`, `risk`가 갱신됨
- [x] `infra_state` 처리 후 DynamoDB LATEST의 `infra_state`, `pipeline_status`가 갱신됨
- [x] DynamoDB HISTORY#STATE와 S3 processed에 처리 결과가 저장됨
- [x] Lambda CloudWatch Logs에서 최신 이벤트 수신을 확인할 수 있음

### 2026-05-21 구현 메모

- 구현 위치: `apps/data-processor/`
- entrypoint: `lambda_function.py`
- Terraform 인프라: `infra/data-pipeline/` (IoT Rule × 3, Lambda, IAM, CloudWatch)
- DynamoDB 테이블: `AEGIS-DynamoDB-FactoryStatus` (infra/foundation 영구 리소스, data-pipeline에서 data source로 참조)

DynamoDB 저장 계약:
- LATEST 아이템: `pk=FACTORY#factory-a`, `sk=LATEST` — 최신 전체 상태, TTL 없음
- HISTORY#STATE 아이템: `pk=FACTORY#factory-a`, `sk=HISTORY#STATE#{updated_at}` — `LATEST`와 같은 구조 + `HISTORY_TTL_HOURS` 기준 TTL
- `factory_state`와 `infra_state`는 `LATEST`를 부분 갱신한 뒤, 갱신된 전체 `LATEST`를 history snapshot으로 저장

Risk Score 계산:
- `factory_state` 수신 시 fire/fall/bend score 기반 Risk 계산
- LATEST `risk` 부분 갱신 + HISTORY#STATE snapshot 저장

pipeline_status 계산:
- `infra_state` 수신 시 마지막 수신 시각 기준으로 pipeline 상태 계산
- LATEST `pipeline_status` 부분 갱신 + HISTORY#STATE snapshot 저장

S3 processed 저장:
- `s3://aegis-bucket-data/processed/factory-a/{source_type}/{yyyy}/{mm}/{dd}/{message_id}.json`
- `s3://aegis-bucket-data/processed/factory-a/state_snapshot/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{updated_at}.json`
- `state_snapshot`은 DynamoDB `HISTORY#STATE`와 같은 구조를 저장하되, DynamoDB TTL 정책 필드인 `ttl`은 제외

정규화 실패 처리:
- schema 검증 실패 시 CloudWatch Logs에 오류 기록 후 스킵 (Lambda 실패로 처리하지 않음)

2026-05-27 검증 결과:
- Lambda `AEGIS-Lambda-DataProcessor` Active, LastUpdateStatus Successful 확인
- IoT Rule `AEGIS_IoTRule_factory_a/b/c_raw_s3` 모두 `disabled=false`, Lambda action + S3 raw action 연결 확인
- S3 `raw/factory-a,b,c/`와 `processed/factory-a,b,c/state_snapshot/`에 2026-05-27 데이터 적재 확인
- DynamoDB `AEGIS-DynamoDB-FactoryStatus`의 `FACTORY#factory-a/b/c` LATEST 갱신 확인
- DynamoDB TTL `ttl` ENABLED 확인

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: Lambda data processor(`apps/data-processor/`) 구현 및 AWS 배포 검증 완료. DynamoDB는 `LATEST`와 `HISTORY#STATE#{updated_at}` 단일 snapshot 이력 구조로 정리했고, history는 `LATEST`와 같은 구조에 `ttl`만 추가한다. Terraform 인프라(`infra/data-pipeline/`) 배포 완료. IoT Rule 3개는 S3 raw와 Lambda action을 동시에 수행한다.
- 변경/확인: `apps/data-processor/`, `infra/data-pipeline/`, `infra/foundation/dynamodb.tf`
- 검증: 2026-05-27 AWS 실제 리소스 기준 IoT → Lambda → DynamoDB LATEST/HISTORY#STATE + S3 processed end-to-end 확인
- 후속: M6 Risk Twin/Dashboard 구현

---

## Issue 7 - [데이터/Pipeline] `pipeline_status` Lambda 처리 검증

### 🎯 목표 (What & Why)

IoT Core 수신 상태와 S3 적재 상태를 기준으로 `pipeline_status`가 Lambda data processor에서 계산되고 DynamoDB LATEST/HISTORY#STATE에 반영되는지 검증한다.
`pipeline_status`는 Edge가 직접 보내는 값이 아니라 cloud-side에서 계산하는 관제용 상태다.

### ✅ 완료 조건 (Definition of Done)

- [x] Lambda data processor의 `pipeline_status` 계산 구현
  - [x] IoT Core `infra_state` 수신 여부 확인 로직
  - [x] S3 최신 적재 시각 기준 지연 판단 로직
  - [x] DynamoDB LATEST/HISTORY#STATE 업데이트 로직
  - [x] `infra_state` 20초 주기 기준 warning/critical 판단
- [x] DynamoDB LATEST/HISTORY#STATE 저장 확인
- [ ] Dashboard VPC 조회용 latest/status 저장소 반영 (Dashboard VPC 후속 단계)
- [x] `pipeline_status` 판단 기준을 데이터 플레인 관련 문서에 반영

### 🔍 Acceptance Criteria

- [x] Lambda 처리 결과에서 `factory-a`의 pipeline 상태 확인 가능
- [x] DynamoDB LATEST에서 `factory-a`의 pipeline 상태 조회 가능
- [ ] IoT Core 메시지가 일정 시간 이상 없을 때 `pipeline_status` 이상으로 판정

### 2026-05-21 구현 메모

pipeline_status 계산 로직 (`apps/data-processor/lambda_function.py`):
- `infra_state` 수신 시 현재 시각과 source_timestamp 차이로 지연 판단
- `infra_state` 20초 주기 기준: age > 40초이면 `warning`, age > 60초이면 `critical`, 정상이면 `normal`
- DynamoDB LATEST `pk=FACTORY#factory-a`, `sk=LATEST`의 `pipeline_status`를 부분 갱신
- DynamoDB HISTORY#STATE: `pk=FACTORY#factory-a`, `sk=HISTORY#STATE#{updated_at}`, `LATEST`와 같은 구조 + `HISTORY_TTL_HOURS` 기준 TTL

검증 시나리오 (build-data-pipe.sh 실행 후):
1. `edge-iot-publisher` 정상 동작 중: DynamoDB LATEST pipeline_status = `normal`
2. `edge-iot-publisher` 강제 중지 후 40초 초과: DynamoDB LATEST pipeline_status = `warning`
3. `edge-iot-publisher` 강제 중지 후 60초 초과: DynamoDB LATEST pipeline_status = `critical`
4. `edge-iot-publisher` 재시작 후: DynamoDB LATEST pipeline_status = `normal` 복구 확인

2026-05-27 검증 결과:
- `factory-a`, `factory-b`, `factory-c` DynamoDB LATEST에서 `pipeline_status.status=normal` 확인
- `factory-a` latest_infra_state_age_seconds=17, `factory-b`=10, `factory-c`=3 확인
- `factory-a/b/c` 모두 S3 processed state_snapshot과 DynamoDB LATEST 갱신 확인
- publisher 중지/시작 기반 warning/critical 상태 전이 검증은 M7 장애/통합 검증에서 수행. 2026-05-29에는 DataProcessorRefresh1m 배포 후 `factory-a` 입력 중단 상태가 `pipeline_status=critical`, `risk.level=danger`, `risk.score=0`으로 stale 보정됨을 별도 확인했다.

### GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: pipeline_status 계산 로직은 Issue 6의 Lambda data processor에 통합 구현됨. infra_state 수신 주기(20초) 기준 normal/warning/critical 판단 로직 구현. DynamoDB LATEST 부분 갱신 + HISTORY#STATE snapshot TTL 아이템 저장 로직 구현 및 AWS 실제 리소스 검증 완료.
- 검증: 2026-05-27 `factory-a/b/c` LATEST pipeline_status normal 확인. 2026-05-29 DataProcessorRefresh1m 배포 후 `factory-a` 입력 중단 상태의 warning/critical stale 보정도 확인.
- 후속: M6 Risk Twin/Dashboard 구현

---

## Issue 8 - [검증/데이터] `factory-a` 데이터 플레인 end-to-end 검증

### 🎯 목표 (What & Why)

`factory-a` 데이터가 `factory-a-log-adapter`와 `edge-iot-publisher`를 거쳐 IoT Core와 S3 raw까지 실제로 흐르는 raw 데이터 플레인을 검증한다.
Lambda, DynamoDB/S3 processed, `pipeline_status`는 Issue 6~7에서 별도 검증한다.
이 raw 검증이 완료되어야 M5(VM Spoke 확장)를 진행할 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [x] `raw/log/status -> factory-a-log-adapter -> edge-iot-publisher -> IoT Core -> S3 raw` 흐름 end-to-end 확인
- [x] source_type별 경로 분리 적재 확인 (`factory_state`, `infra_state`)
- [x] raw object body가 canonical JSON 계약을 만족하는지 확인
- [x] 검증 결과를 데이터 플레인 관련 문서와 `docs/ops/03_test_checklist.md`에 반영
- [x] `IoT Core → Lambda data processor → DynamoDB/S3 processed` 흐름 확인 (Issue 6)
- [x] Lambda 정규화/Risk 계산 처리 확인 (Issue 6, M6에서 보강)
- [x] `pipeline_status` Lambda 계산 동작 확인 (Issue 7)
- [x] DynamoDB LATEST/HISTORY#STATE에 Dashboard 조회용 최신 상태 반영 확인 (Issue 6~7)
- [ ] 데이터 지연/누락 발생 시 `pipeline_status` 이상 판정 확인 (Issue 7)

### 🔍 Acceptance Criteria

- S3에서 `factory-a` 데이터 주기적 적재 확인 (최소 10분 이상 연속)
- `factory_state`, `infra_state` 두 경로에 데이터 분리 적재 확인
- Lambda/DynamoDB/S3 processed와 `pipeline_status`는 Issue 6~7에서 확인 완료
- `edge-iot-publisher` 강제 중지 후 이상 판정 검증은 Issue 7과 M7에서 수행

## 2026-05-14 수정 방향

이 문서의 이전 `정규화 서비스`, `Risk Score Engine`, `pipeline-status-aggregator`, `ops-support` 표현은 최신 MVP 기준에서 별도 컨테이너 서비스/파드가 아니다.

최신 기준은 아래 흐름이다.

```text
factory-a-log-adapter / dummy-data-generator
  -> edge-iot-publisher
  -> IoT Core
      -> IoT Rule -> S3 raw
          -> Lambda data processor
              -> DynamoDB LATEST
              -> DynamoDB HISTORY#STATE
              -> S3 processed

Dashboard API/Web
  -> DynamoDB LATEST/HISTORY#STATE
  -> S3 processed
```

M4의 cloud-side 구현 대상은 Lambda data processor와 DynamoDB/S3 저장 계약 검증으로 정리한다.
