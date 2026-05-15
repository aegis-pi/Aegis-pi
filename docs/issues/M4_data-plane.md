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

S3 raw 적재 흐름은 유지하되, Dashboard가 조회할 최신 상태는 DynamoDB LATEST/HISTORY와 S3 processed 경로로 반영한다.

```text
factory-a-log-adapter / edge-iot-publisher
  -> IoT Core
  -> Lambda data processor
  -> DynamoDB LATEST/HISTORY
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
- IoT Core 수신 후 DynamoDB LATEST/HISTORY 반영 지연
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

---

## Issue 1 - [데이터/Schema] Raw/Processed 데이터 계약 확정

### 🎯 목표 (What & Why)

`입력 모듈 또는 raw/log adapter -> canonical JSON -> IoT publisher -> IoT Core/S3/Lambda` 사이의 데이터 구조를 고정한다.
이 스키마가 확정되어야 `factory-a-log-adapter`, `dummy-data-generator`, `edge-iot-publisher`, Lambda data processor가 모두 같은 포맷을 기준으로 구현된다.
라즈베리파이와 VM의 입력 차이는 이 스키마 안에서 `input_module_type`으로만 구분한다.

2026-05-14 기준 표준 입력 스키마 source of truth는 `docs/specs/iot_data_format.md`다.
최종 source type은 `factory_state`, `infra_state` 두 개로 단순화한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 필수 공통 필드 확정
  - `factory_id` (string)
  - `node_id` (string: `master` / `worker1` / `worker2` / `cluster`)
  - `source_timestamp` (ISO 8601 UTC)
  - `published_at` (ISO 8601 UTC)
  - `message_id` (idempotency key)
  - `source_type` (`factory_state` / `infra_state`)
  - `environment_type` (`physical-rpi` / `vm-mac` / `vm-windows`)
- [ ] source_type별 payload 구조 확정 및 샘플 작성
  - `factory_state`: 3초 주기, 온도/습도/기압 평균과 AI score 평균
  - `infra_state`: 20초 주기, heartbeat, cluster, nodes, workloads, devices
  - `pipeline_status`: Hub derived 상태 (Edge가 직접 보내지 않음)
- [ ] 선택 필드 `null` 허용 원칙 명시
- [ ] 스키마 예시 JSON 작성 및 관련 입력/데이터 모델 문서에 반영
- [ ] local spool/outbox file 계약 확정
  - file content는 canonical JSON 한 건
  - 파일명은 `message_id` 기반
  - publisher 성공 시 ack/delete 원칙 정의
- [ ] S3 raw object body가 canonical JSON과 동일한지 여부 확정
- [ ] S3 processed/latest 계약 초안 작성

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
  "agent_instance_id": "edge-iot-publisher-7f8c9d",
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
      "abnormal_sound": "intermittent impact sound"
    }
  }
}
```

### 🔍 Acceptance Criteria

- 스키마 JSON 예시가 관련 입력/데이터 모델 문서에 source_type별로 작성됨
- adapter/generator/publisher/Lambda 구현 시 이 스키마를 기준으로 바로 개발 가능한 수준
- `pipeline_status`가 Hub derived임이 명확히 구분됨
- S3 raw key와 object body의 추적 기준이 `message_id`로 연결됨

---

## Issue 2 - [데이터/Adapter] `factory-a` raw/log -> JSON 변환 로직 구현

### 🎯 목표 (What & Why)

`factory-a` 라즈베리파이 환경에서 실제 raw/log/status 데이터를 읽고 표준 JSON으로 변환하는 adapter를 구현한다.
이 이슈는 IoT Core 전송을 하지 않는다. 변환 결과는 local spool/outbox에 canonical JSON 파일로 남긴다.

### ✅ 완료 조건 (Definition of Done)

- [ ] adapter 구현 언어/프레임워크 결정 (Python 권장, 라즈베리파이 ARM64 호환)
- [ ] factory-a 실제 입력 source 확정
  - 센서 raw/log 파일 또는 기존 AI/audio/BME output 위치
  - 시스템/워크로드 상태 조회 방식
- [ ] 수집 대상 구현
  - BME280 온도/습도/기압 평균 (`factory_state`)
  - AI fire/fall/bend 최근 window 평균 score (`factory_state`)
  - 이상소음 대표 텍스트 (`factory_state`)
  - 노드 상태, CPU/memory/disk usage (`infra_state`)
  - BME280, 카메라, 마이크 장치 상태 (`infra_state`)
  - AI/audio/BME Pod 상태와 restart count (`infra_state`)
  - adapter heartbeat와 마지막 spool write 결과 (`infra_state`)
- [ ] 수집 데이터 → 표준 입력 스키마 변환 로직
- [ ] canonical JSON file을 local spool/outbox에 쓰는 로직
- [ ] 수집 주기 설정 (주기값은 `docs/ops/03_test_checklist.md` 기반 테스트 후 확정)
  - 확정 초기값: `factory_state` 3초, `infra_state` 20초

### 🔍 Acceptance Criteria

- 로컬 실행 또는 개발 환경 기준으로 수집/변환 로직 동작 확인
- 표준 스키마 형식의 JSON file 생성 확인
- 센서값/시스템 상태가 source_type별로 올바르게 분리됨 확인
- IoT Core 연결 없이도 spool/outbox에 publish 후보 JSON이 쌓임 확인

---

## Issue 3 - [데이터/Publisher] JSON -> IoT Core 전송 로직 구현

### 🎯 목표 (What & Why)

Issue 2의 adapter가 만든 canonical JSON을 local spool/outbox에서 읽어 AWS IoT Core로 publish하는 공통 publisher를 구현한다.
이 publisher는 `factory-a`뿐 아니라 M5의 `factory-b/c` dummy generator와도 재사용한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] local spool/outbox scan 로직 구현
- [ ] AWS IoT Core MQTT publish 구현
  - topic: `aegis/{factory_id}/{source_type}`
  - mTLS certificate/key/CA file 사용
- [ ] publish 성공 시 ack/delete 처리
- [ ] publish 실패 시 retry/backoff 처리
- [ ] 중복 publish 가능성 및 `message_id` idempotency 기준 문서화
- [ ] publisher heartbeat/logging 구현

### 🔍 Acceptance Criteria

- sample canonical JSON file을 spool에 넣으면 IoT Core topic으로 publish됨
- publish 성공 후 spool file이 ack/delete됨
- IoT Core 장애 또는 인증 실패 시 file이 삭제되지 않고 재시도 대상으로 남음
- publisher는 factory별 인증서 Secret만 바꾸면 재사용 가능

---

## Issue 4 - [데이터/Container/GitOps] adapter/publisher 이미지화 및 K3s 배포

### 🎯 목표 (What & Why)

`factory-a-log-adapter`와 `edge-iot-publisher`를 ARM64 이미지로 만들고, Hub EKS ArgoCD가 factory-a K3s에 배포할 수 있게 GitOps chart/values를 확장한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `factory-a-log-adapter` ARM64 Docker image 빌드 가능
- [ ] `edge-iot-publisher` ARM64 Docker image 빌드 가능
- [ ] ECR repository/tag 전략 확정
  - 후보: `aegis/factory-a-log-adapter`, `aegis/edge-iot-publisher`
- [ ] GitOps chart/values 확장
  - factory-a: adapter enabled, publisher enabled
  - shared spool volume mount
  - IoT certificate Secret mount
- [ ] Hub EKS ArgoCD ApplicationSet이 factory-a K3s에 두 파드를 배포
- [ ] `worker-2` 또는 대상 node 배치 기준 정리
- [ ] 필요한 Secret / Config / volume / device mount 요구사항 정리

### 🔍 Acceptance Criteria

- ECR에 두 이미지가 push됨
- ArgoCD `aegis-spoke-factory-a` Application이 두 workload를 관리함
- factory-a K3s에서 adapter/publisher Pod가 `Running`
- shared spool/outbox volume을 통해 adapter -> publisher handoff가 가능

---

## Issue 5 - [데이터/S3] IoT Core → S3 적재 확인 (경로 파티셔닝 포함)

### 🎯 목표 (What & Why)

`factory-a` K3s에서 생성된 canonical JSON이 `edge-iot-publisher`를 통해 IoT Core로 전송되고, IoT Rule에 의해 S3 raw 경로에 실제 적재되는지 확인한다.
`factory_id` / `source_type` / 날짜 기반 파티셔닝과 object body schema를 모두 검증한다. 이 검증 없이는 M4를 완료로 보지 않는다.

### ✅ 완료 조건 (Definition of Done)

- [ ] factory-a K3s publisher가 IoT Core topic으로 메시지 publish
- [ ] IoT Rule Action이 S3에 메시지 적재하는 것 확인
- [ ] 경로 파티셔닝 규칙 적용 확인
  - `s3://bucket/raw/factory-a/factory_state/yyyy=2026/mm=05/dd=14/<message_id>.json`
  - `s3://bucket/raw/factory-a/infra_state/yyyy=2026/mm=05/dd=14/<message_id>.json`
  - 현재 Terraform IoT Rule은 MQTT topic `aegis/factory-a/{source_type}`의 세 번째 segment를 `source_type`으로 사용한다.
- [ ] `source_type`별 경로가 올바르게 분리되어 적재되는지 확인
- [ ] S3 object body가 canonical JSON schema와 일치하는지 확인
- [ ] `message_id`로 spool file, MQTT publish, S3 object를 추적할 수 있는지 확인
- [ ] S3 적재 실패 시 IoT Rule 오류 로그 확인 방법 정의

### 🔍 Acceptance Criteria

- S3 콘솔에서 `raw/factory-a/factory_state/`, `raw/factory-a/infra_state/` 경로에 파일 적재 확인
- 적재된 파일 내용이 표준 스키마와 일치
- 두 `source_type` 경로에 파일이 분리 적재됨
- `aws s3api get-object` 또는 동등한 명령으로 object body JSON 필수 필드를 확인
- 최소 1건 이상의 실제 factory-a generated message가 S3 raw에 적재됨

---

## Issue 6 - [데이터/Lambda] IoT Core Lambda data processor 구현

### 🎯 목표 (What & Why)

IoT Core 수신 메시지를 Lambda data processor로 처리해 정규화, Risk 계산, `pipeline_status` 계산, DynamoDB/S3 processed 저장까지 수행한다.
S3 raw는 IoT Rule로 원본 보존을 유지하고, Dashboard 현재 상태 조회는 DynamoDB LATEST/HISTORY를 기준으로 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Lambda data processor 구현
  - IoT Core Rule 또는 메시지 라우팅으로 Lambda 호출
  - 필드 정규화 (타입 변환, null 처리, 단위 통일)
  - Risk Score 계산
  - `pipeline_status` 계산
  - DynamoDB LATEST overwrite/update
  - DynamoDB HISTORY TTL item 저장
  - S3 processed 처리 결과 저장
- [ ] Lambda IAM 권한 설정
  - DynamoDB read/write
  - S3 processed write
  - 필요 시 S3 raw read
- [ ] 정규화 실패 데이터 처리 원칙 정의 (스킵 또는 오류 로그)
- [ ] Dashboard VPC 조회용 DynamoDB/S3 processed 계약 반영

### 🔍 Acceptance Criteria

- IoT Core 메시지 수신 후 Lambda가 자동 실행됨
- `factory_state` 처리 후 DynamoDB LATEST의 `factory_state`, `risk`가 갱신됨
- `infra_state` 처리 후 DynamoDB LATEST의 `infra_state`, `pipeline_status`가 갱신됨
- DynamoDB HISTORY와 S3 processed에 처리 결과가 저장됨
- Lambda CloudWatch Logs에서 정상 처리와 실패 로그를 확인할 수 있음

---

## Issue 7 - [데이터/Pipeline] `pipeline_status` Lambda 처리 검증

### 🎯 목표 (What & Why)

IoT Core 수신 상태와 S3 적재 상태를 기준으로 `pipeline_status`가 Lambda data processor에서 계산되고 DynamoDB LATEST/HISTORY에 반영되는지 검증한다.
`pipeline_status`는 Edge가 직접 보내는 값이 아니라 cloud-side에서 계산하는 관제용 상태다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Lambda data processor의 `pipeline_status` 계산 구현
  - IoT Core `infra_state` 수신 여부 확인 로직
  - S3 최신 적재 시각 기준 지연 판단 로직
  - DynamoDB LATEST/HISTORY 업데이트 로직
  - `infra_state` 20초 주기 기준 warning/critical 판단
- [ ] DynamoDB LATEST/HISTORY 저장 확인
- [ ] Dashboard VPC 조회용 latest/status 저장소 반영
- [ ] `pipeline_status` 판단 기준을 데이터 플레인 관련 문서에 반영

### 🔍 Acceptance Criteria

- Lambda 처리 결과에서 `factory-a`의 pipeline 상태 확인 가능
- DynamoDB LATEST에서 `factory-a`의 pipeline 상태 조회 가능
- IoT Core 메시지가 일정 시간 이상 없을 때 `pipeline_status` 이상으로 판정

---

## Issue 8 - [검증/데이터] `factory-a` 데이터 플레인 end-to-end 검증

### 🎯 목표 (What & Why)

`factory-a` 데이터가 `factory-a-log-adapter`와 `edge-iot-publisher`를 거쳐 IoT Core, S3 raw, Lambda, DynamoDB/S3 processed까지 실제로 흐르는 전체 파이프라인을 검증한다.
이 검증이 완료되어야 M4 마일스톤이 완료되고 M5(VM Spoke 확장)와 M6(Risk Twin)으로 넘어갈 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `raw/log/status -> factory-a-log-adapter -> edge-iot-publisher -> IoT Core -> S3 raw` 흐름 end-to-end 확인
- [ ] `IoT Core → Lambda data processor → DynamoDB/S3 processed` 흐름 확인
- [ ] source_type별 경로 분리 적재 확인 (`factory_state`, `infra_state`)
- [ ] Lambda 정규화/Risk 계산 처리 확인
- [ ] `pipeline_status` Lambda 계산 동작 확인
- [ ] DynamoDB LATEST/HISTORY에 Dashboard 조회용 최신 상태 반영 확인
- [ ] 데이터 지연/누락 발생 시 `pipeline_status` 이상 판정 확인
- [ ] 검증 결과를 데이터 플레인 관련 문서와 `docs/ops/03_test_checklist.md`에 반영

### 🔍 Acceptance Criteria

- S3에서 `factory-a` 데이터 주기적 적재 확인 (최소 10분 이상 연속)
- `factory_state`, `infra_state` 두 경로에 데이터 분리 적재 확인
- `edge-iot-publisher` 강제 중지 후 `pipeline_status` 이상 판정 확인
- 재기동 후 파이프라인 자동 복구 확인

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
          -> DynamoDB HISTORY
          -> S3 processed

Dashboard API/Web
  -> DynamoDB LATEST/HISTORY
  -> S3 processed
```

M4의 cloud-side 구현 대상은 Lambda data processor와 DynamoDB/S3 저장 계약 검증으로 정리한다.
