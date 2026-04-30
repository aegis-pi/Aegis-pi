# M4. 데이터 플레인 - `factory-a` 단일 Spoke 기준

> **마일스톤 목표**: `factory-a` Spoke의 센서/상태 데이터가 Edge Agent → IoT Core → S3까지 실제로 흐르는 것을 검증한다.
> M2(Hub-Spoke 연결) 완료 후 M3(배포 파이프라인)과 병렬로 진행 가능하다.  
> 이 마일스톤이 완료되어야 M6(Risk Twin)에서 실데이터 기반 Risk Score 계산이 가능해진다.
> Dashboard VPC가 Spoke에 직접 붙지 않으므로 노드, 장치, 워크로드 상태도 Edge Agent가 송신한다.

---

## Issue 1 - [데이터/Schema] 표준 입력 스키마 확정

### 🎯 목표 (What & Why)

`입력 모듈 → Edge Agent` 사이의 데이터 구조를 고정한다.  
이 스키마가 확정되어야 Edge Agent, Dummy Sensor, 정규화 서비스가 모두 같은 포맷을 기준으로 구현된다.  
라즈베리파이와 VM의 입력 차이는 이 스키마 안에서 `input_module_type`으로만 구분한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 필수 공통 필드 확정
  - `factory_id` (string)
  - `node_id` (string: `master` / `worker1` / `worker2`)
  - `timestamp` (ISO 8601)
  - `source_type` (`sensor` / `system_status` / `device_status` / `workload_status` / `pipeline_heartbeat` / `pipeline_status` / `event`)
  - `environment_type` (`physical-rpi` / `vm-mac` / `vm-windows`)
- [ ] source_type별 payload 구조 확정 및 샘플 작성
  - `sensor`: `temperature`, `humidity`, `pressure`
  - `system_status`: `node_status`, `edge_agent_status`, CPU/memory/disk usage
  - `device_status`: BME280, camera, microphone availability
  - `workload_status`: 주요 Pod Running 여부, restart count, node placement
  - `pipeline_heartbeat`: Edge Agent alive, last publish status
  - `pipeline_status`: Hub derived 상태 (Edge가 직접 보내지 않음)
  - `event`: 구조만 예약, 현재 미사용
- [ ] 선택 필드 `null` 허용 원칙 명시
- [ ] 스키마 예시 JSON 작성 및 관련 입력/데이터 모델 문서에 반영

```json
{
  "factory_id": "factory-a",
  "node_id": "worker2",
  "timestamp": "2026-04-24T12:00:00Z",
  "source_type": "sensor",
  "environment_type": "physical-rpi",
  "payload": {
    "temperature": 24.5,
    "humidity": 58.2
  }
}
```

### 🔍 Acceptance Criteria

- 스키마 JSON 예시가 관련 입력/데이터 모델 문서에 source_type별로 작성됨
- Edge Agent 구현 시 이 스키마를 기준으로 바로 개발 가능한 수준
- `pipeline_status`가 Hub derived임이 명확히 구분됨

---

## Issue 2 - [데이터/Edge Agent] `factory-a` Edge Agent 수집/변환 로직 구현

### 🎯 목표 (What & Why)

`factory-a` 라즈베리파이 환경에서 실제 센서 데이터와 시스템 상태를 수집하여 표준 스키마로 변환하는 Edge Agent 핵심 로직을 구현한다.  
이 이슈에서는 수집/변환 로직 자체에 집중하고, 컨테이너 이미지화와 K3s 배포 준비는 다음 이슈에서 진행한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Edge Agent 구현 언어/프레임워크 결정 (Python 권장, 라즈베리파이 ARM64 호환)
- [ ] 수집 대상 구현
  - BME280 온도/습도 (`sensor`)
  - 카메라 연결/프로세스 상태 (`system_status`)
  - 마이크 연결/프로세스 상태 (`system_status`)
  - 노드 상태, Edge Agent 상태, 입력 모듈 상태 (`system_status`)
  - BME280, 카메라, 마이크 장치 상태 (`device_status`)
  - AI/audio/BME Pod 상태와 restart count (`workload_status`)
  - Edge Agent heartbeat와 마지막 publish 결과 (`pipeline_heartbeat`)
- [ ] 수집 데이터 → 표준 입력 스키마 변환 로직
- [ ] 수집 주기 설정 (주기값은 `docs/ops/03_test_checklist.md` 기반 테스트 후 확정)
  - 권장 초기값: heartbeat 10초, full status 30초, status change event 즉시

### 🔍 Acceptance Criteria

- 로컬 실행 또는 개발 환경 기준으로 수집/변환 로직 동작 확인
- 표준 스키마 형식의 메시지 payload 생성 확인
- 센서값/시스템 상태가 source_type별로 올바르게 분리됨 확인

---

## Issue 3 - [데이터/Container] `factory-a` Edge Agent 컨테이너화 및 K3s 배포 준비

### 🎯 목표 (What & Why)

Issue 2에서 구현한 Edge Agent 로직을 ARM64 환경에서 실행 가능한 컨테이너 이미지로 만들고,  
`factory-a` K3s에 배포 가능한 상태까지 준비한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Edge Agent ARM64 Docker 이미지 빌드 가능 상태 확인
- [ ] ECR 푸시 가능한 이미지 태그 전략 연결
- [ ] K3s 배포 매니페스트 또는 Helm values 반영
- [ ] `worker-2` 배치 기준 배포 스펙 정리
- [ ] 파드 실행에 필요한 Secret / Config / 디바이스 마운트 요구사항 정리

### 🔍 Acceptance Criteria

- Edge Agent 이미지가 ARM64 기준으로 빌드됨 확인
- `factory-a` 배포 대상 매니페스트에서 Edge Agent를 참조 가능
- K3s 배포 전 필요한 환경값/Secret/마운트 요구사항이 문서화됨

---

## Issue 4 - [데이터/IoT Core] Edge Agent → IoT Core 연결 및 수신 확인

### 🎯 목표 (What & Why)

Edge Agent가 실제 IoT Core 엔드포인트에 연결되어 데이터가 수신되는지 확인한다.  
인증서 관리와 연결 안정성을 검증하고, 연결 장애 시 재연결 로직을 확인한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] IoT Core 인증서 파일을 K3s Secret으로 배포
- [ ] Edge Agent 파드에서 인증서 마운트 및 MQTT 연결 성공
- [ ] IoT Core MQTT 테스트 클라이언트에서 메시지 실시간 수신 확인
- [ ] 연결 장애 시 재연결 로직 동작 확인
- [ ] IoT Core 연결 로그 확인 (CloudWatch 또는 파드 로그)

### 🔍 Acceptance Criteria

- IoT Core 콘솔 `MQTT 테스트 클라이언트`에서 `factory-a` 메시지 수신 확인
- 메시지 구조가 표준 입력 스키마와 일치
- 파드 재시작 후에도 자동 재연결 확인

---

## Issue 5 - [데이터/S3] IoT Core → S3 적재 확인 (경로 파티셔닝 포함)

### 🎯 목표 (What & Why)

IoT Core Rule이 수신된 메시지를 S3 지정 경로에 자동 적재하는지 확인한다.  
`factory_id` / `source_type` / 날짜 기반 파티셔닝이 올바르게 적용되는지 검증한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] IoT Rule Action이 S3에 메시지 적재하는 것 확인
- [ ] 경로 파티셔닝 규칙 적용 확인
  - `s3://bucket/factory-a/sensor/2026/04/24/<timestamp>.json`
  - `s3://bucket/factory-a/system_status/2026/04/24/<timestamp>.json`
  - `s3://bucket/factory-a/device_status/2026/04/24/<timestamp>.json`
  - `s3://bucket/factory-a/workload_status/2026/04/24/<timestamp>.json`
  - `s3://bucket/factory-a/pipeline_heartbeat/2026/04/24/<timestamp>.json`
- [ ] `source_type`별 경로가 올바르게 분리되어 적재되는지 확인
- [ ] S3 적재 실패 시 IoT Rule 오류 로그 확인 방법 정의

### 🔍 Acceptance Criteria

- S3 콘솔에서 `factory-a/sensor/` 경로에 파일 적재 확인
- 적재된 파일 내용이 표준 스키마와 일치
- 4개 이상의 `source_type` 경로에 파일이 분리 적재됨

---

## Issue 6 - [데이터/정규화] EKS 내부 정규화/판단 서비스 구현

### 🎯 목표 (What & Why)

S3에 적재된 원본 데이터를 읽어 정규화하고 Risk Score Engine에 전달하는 서비스를 구현한다.  
이 서비스는 `risk` 네임스페이스에서 독립 서비스로 동작하며, S3 트리거 기반으로 실행된다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 정규화/판단 서비스 구현
  - S3에서 데이터 읽기 (S3 이벤트 트리거 또는 주기 폴링)
  - 필드 정규화 (타입 변환, null 처리, 단위 통일)
  - 정규화 결과를 Risk Score Engine에 전달
- [ ] `risk` 네임스페이스에 배포
- [ ] 정규화 실패 데이터 처리 원칙 정의 (스킵 또는 오류 로그)
- [ ] IRSA 기반 S3 읽기 권한 설정

### 🔍 Acceptance Criteria

- S3에 데이터 적재 후 정규화 서비스가 자동으로 처리
- 정규화 결과가 Risk Score Engine에 전달됨 (M6와 연계)
- 서비스 파드 `Running` 및 정상 처리 로그 확인

---

## Issue 7 - [데이터/Pipeline] `pipeline_status` 주기 집계 구현 (`ops-support`)

### 🎯 목표 (What & Why)

IoT Core 수신 상태와 S3 적재 상태를 기준으로 `pipeline_status`를 주기적으로 계산하는 보조 서비스를 구현한다.  
`pipeline_status`는 Edge가 직접 보내는 값이 아니라 Hub가 계산하는 관제용 상태이며,  
Risk Score Engine 입력뿐 아니라 Grafana에서 조회 가능한 형태로도 노출한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `pipeline-status-aggregator` 서비스 구현
  - IoT Core 수신 여부 확인 로직
  - S3 최신 적재 시각 기준 지연 판단 로직
  - latest status store 업데이트 로직
  - 주기 집계 간격 설정 (초기값 설정, 실측 후 `docs/ops/03_test_checklist.md` 기반 보정)
- [ ] `ops-support` 네임스페이스에 배포
- [ ] 집계 결과를 Risk Score Engine 입력 및 Grafana 조회 양쪽에서 사용할 수 있게 노출
- [ ] Grafana 조회를 위한 저장/조회 방식 확정
  - 예: DynamoDB, Timestream, Prometheus 메트릭, 별도 API 중 하나
- [ ] Dashboard VPC 조회용 latest/status 저장소 반영
- [ ] `pipeline_status` 판단 기준을 데이터 플레인 관련 문서에 반영

### 🔍 Acceptance Criteria

- `pipeline-status-aggregator` 파드 `Running`
- 주기 집계 결과에서 `factory-a`의 pipeline 상태 확인 가능
- Grafana에서 `factory-a`의 pipeline 상태를 조회 가능
- IoT Core 메시지가 일정 시간 이상 없을 때 `pipeline_status` 이상으로 판정

---

## Issue 8 - [검증/데이터] `factory-a` 데이터 플레인 end-to-end 검증

### 🎯 목표 (What & Why)

`factory-a` 센서 데이터가 Edge Agent에서 S3까지 실제로 흐르는 전체 파이프라인을 검증한다.  
이 검증이 완료되어야 M4 마일스톤이 완료되고 M5(VM Spoke 확장)와 M6(Risk Twin)으로 넘어갈 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `입력 모듈 → Edge Agent → IoT Core → S3` 흐름 end-to-end 확인
- [ ] source_type별 경로 분리 적재 확인 (`sensor`, `system_status`, `device_status`, `workload_status`, `pipeline_heartbeat`)
- [ ] 정규화 서비스 처리 확인
- [ ] `pipeline_status` 집계 동작 확인
- [ ] latest status store에 Dashboard 조회용 최신 상태 반영 확인
- [ ] 데이터 지연/누락 발생 시 `pipeline_status` 이상 판정 확인
- [ ] 검증 결과를 데이터 플레인 관련 문서와 `docs/ops/03_test_checklist.md`에 반영

### 🔍 Acceptance Criteria

- S3에서 `factory-a` 데이터 주기적 적재 확인 (최소 10분 이상 연속)
- `source_type` 5개 이상 경로에 데이터 분리 적재 확인
- Edge Agent 강제 중지 후 `pipeline_status` 이상 판정 확인
- 재기동 후 파이프라인 자동 복구 확인
