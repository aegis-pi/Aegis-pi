# 관제 대시보드 데이터 모델

상태: draft
기준일: 2026-04-24

## 목적

관제 대시보드가 읽는 주요 엔티티, 저장 경계, 조회 모델을 정의한다.

## 현재 상태

- 데이터 플레인 구조는 확정되었다.
- 세부 저장 스키마와 일부 필드는 테스트 후 보정 예정이다.

## 범위

- 주요 엔티티
- 저장 경계
- 조회용 집계 모델
- 민감 정보 여부

## 상세 내용

## 저장 경계

| 경계 | 역할 | 비고 |
| --- | --- | --- |
| Edge 입력 | 센서/상태 발생 | Spoke 내부 |
| S3 원본 | 원본 수집 데이터 보존 | 장기 보존 대상 |
| 정규화 계층 | Hub 내부 정규화/판단 | EKS 내부 |
| Risk 결과 | 상태/점수/원인 | 조회용 결과 |

## 저장 경계 해석

- Edge 입력은 공장 현장에서 생성되는 원본 상태다.
- S3 원본은 장기 보존 대상이며, 후속 분석의 기준선이 된다.
- 정규화 계층은 Hub 내부 처리용 중간 계층이다.
- Risk 결과는 관제 화면과 후속 분석이 읽는 최종 집계 결과다.

## 공통 식별 필드

현재 설계 기준의 공통 필수 필드:
- `factory_id`
- `node_id`
- `timestamp`
- `source_type`
- `environment_type`

비고:
- `factory_id`: `factory-a`, `factory-b`, `factory-c`
- `environment_type`: `physical-rpi`, `vm-mac`, `vm-windows`
- `source_type`: `sensor`, `system_status`, `pipeline_status`, `event`

## 주요 엔티티

### Factory

- `factory_id`
- `environment_type`
- `role`

민감 정보 여부:
- 낮음

비고:
- 관제 화면에서 공장을 비교하는 기본 단위다.

### SensorObservation

- `factory_id`
- `node_id`
- `timestamp`
- `temperature`
- `humidity`
- `sensor_status`

민감 정보 여부:
- 낮음

비고:
- 현재 MVP에서는 `temperature`, `humidity`가 핵심 환경 입력이다.
- 일부 값은 `null` 가능하다.

### DeviceStatus

- `factory_id`
- `node_id`
- `timestamp`
- `camera_status`
- `mic_status`
- `edge_agent_status`
- `input_module_status`
- `node_status`

민감 정보 여부:
- 낮음

비고:
- `camera_status`, `mic_status`는 현재 MVP에서 프로세스 기준형으로 해석한다.
- `node_status`는 Kubernetes 상태 + 운영 맥락을 따른다.

### PipelineStatus

- `factory_id`
- `pipeline_status`
- `last_seen_at`
- `event_timestamp`
- `processed_at`

민감 정보 여부:
- 낮음

비고:
- `pipeline_status`는 Edge 보고값이 아니라 Hub 계산 상태다.
- 현재는 주기 집계형을 기준으로 한다.

### RiskState

- `factory_id`
- `state`
- `risk_score`
- `delta_10m`
- `top_causes`
- `event_timestamp`
- `processed_at`

민감 정보 여부:
- 낮음

비고:
- 메인 카드에는 `state`, `trend`, `abnormal_component_count` 중심으로 사용한다.
- `risk_score`는 내부 계산값으로 유지하되 메인 카드 직접 노출은 기본 정책이 아니다.

### RecentLog

- `type`
- `factory_id`
- `message`
- `timestamp`
- `raw_code` 후보

민감 정보 여부:
- 낮음

비고:
- 전체 이벤트 로그가 아니라 운영 판단용 최근 변화 로그를 의미한다.

## 조회용 집계 모델

### FactorySummaryView

용도:
- 메인 화면 상단 공장 카드

필드:
- `factory_id`
- `state`
- `trend`
- `abnormal_component_count`
- `risk_score`
- `updated_at`

### FactorySensorView

용도:
- 메인 화면 센서 현황

필드:
- `factory_id`
- `temperature`
- `humidity`
- `trend_window`
- `trend_points`

### AbnormalSystemItem

용도:
- 메인 화면 이상 시스템 목록

필드:
- `factory_id`
- `component_type`
- `status`
- `occurred_at`
- `updated_at` 후보

### PipelineStatusView

용도:
- 파이프라인 상태 조회

필드:
- `factory_id`
- `pipeline_status`
- `last_seen_at`
- `processed_at`

## 민감 정보 여부 정리

- 현재 MVP 기준으로 직접적인 개인정보/민감정보는 핵심 모델에 포함하지 않는다.
- 운영 식별자와 상태 정보가 중심이다.
- TODO: 실제 사용자 계정, 인증 토큰, 접속 정보가 붙으면 별도 보안 분류 필요

## null 허용 방향

- 공통 식별 필드는 필수
- 확장 또는 환경별 미사용 필드는 `null` 허용
- 실제 `null` 처리 정책은 테스트 후 확정

예시:
- `temperature`, `humidity`: 센서 미수신 시 `null` 가능
- `camera_status`, `mic_status`: 환경에 따라 `null` 또는 비활성 상태 가능
- event 관련 필드: 현재 미사용이므로 향후 `null` 허용 후보

## 현재 문서에서 아직 고정하지 않은 것

- 표준 입력 스키마의 내부 JSON 구조
- source_type별 지연/누락 수치 기준
- 보존 기간의 실제 수치
- `trend_points` 세부 구조
- event 활성화 시 데이터 모델 추가 필드

## TODO

- TODO: 실제 저장소별 스키마 매핑 표 추가
- TODO: 원본/정규화/결과 저장 위치 상세화
- TODO: 조회용 집계 모델과 실제 API 응답의 차이를 정리
