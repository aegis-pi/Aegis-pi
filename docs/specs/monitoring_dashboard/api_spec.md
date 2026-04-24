# 관제 대시보드 API 스펙

상태: draft
기준일: 2026-04-24

## 목적

관제 대시보드가 필요로 하는 조회 API의 기본 경로, 요청 형태, 응답 형태, 오류 동작을 정리한다.

## 현재 상태

- 실제 구현된 API는 아직 없다.
- 본 문서는 화면 요구사항과 데이터 모델을 맞추기 위한 초안이다.

## 범위

- 조회 API 후보
- 요청/응답 형태
- 오류 처리 방향

## 상세 내용

## 설계 원칙

- 내부 Risk Score는 API 응답에 포함될 수 있으나,
  메인 카드 노출 여부는 프론트엔드 정책으로 분리한다.
- `pipeline_status`는 Hub에서 계산된 상태를 반환한다.
- 운영형 Spoke와 테스트베드형 Spoke를 모두 공장 단위로 동일하게 조회할 수 있어야 한다.
- 화면은 일부 섹션 실패를 허용하므로, API도 부분 실패를 감안한 설계가 필요하다.

## 공통 응답 원칙

- 시간 필드는 가능하면 UTC ISO 8601 문자열을 사용한다.
- 상태 값은 문자열 enum 형태로 반환한다.
- `factory_id`는 `factory-a`, `factory-b`, `factory-c` 기준을 사용한다.
- 값이 없는 필드는 `null`을 허용할 수 있다.
- TODO: 공통 envelope 사용 여부 확정

## 공통 오류 동작 초안

- `400`: 잘못된 요청 파라미터
- `404`: 대상 공장 또는 조회 대상 미존재
- `500`: 내부 집계 또는 조회 실패
- `503`: Hub 내부 의존 서비스 비정상

## 화면과 API의 관계

| 화면 섹션 | 주요 API |
| --- | --- |
| 상단 공장 카드 | `GET /api/factories/summary` |
| 센서 현황 | `GET /api/factories/{factory_id}/sensors` 또는 집계형 API 후보 |
| 이상 시스템 목록 | `GET /api/systems/abnormal` |
| 최근 로그 | `GET /api/logs/recent` |
| 파이프라인 상태 | `GET /api/pipeline/status` |

## Endpoint 초안

### 1. GET `/api/factories/summary`

목적:
- 메인 화면 상단 카드 데이터 조회

쿼리 파라미터 후보:
- `limit` 선택
- `include_score` 선택

응답 필드:
- `factory_id`
- `state`
- `trend`
- `abnormal_component_count`
- `risk_score`
- `updated_at`

응답 예시:

```json
[
  {
    "factory_id": "factory-a",
    "state": "warning",
    "trend": "up",
    "abnormal_component_count": 2,
    "risk_score": 58,
    "updated_at": "2026-04-24T09:00:00Z"
  }
]
```

오류 처리:
- `400`: 잘못된 파라미터
- `500`: 집계 실패

비고:
- 메인 카드에는 `risk_score`를 직접 표시하지 않을 수 있으나,
  내부 계산 결과 추적을 위해 응답에는 포함 가능하다.

### 2. GET `/api/factories/{factory_id}/sensors`

목적:
- 공장별 온도/습도 및 추세 조회

경로 파라미터:
- `factory_id`

쿼리 파라미터 후보:
- `window` 예: `10m`

응답 필드:
- `factory_id`
- `temperature`
- `humidity`
- `trend_window`
- `trend_points`

응답 예시:

```json
{
  "factory_id": "factory-a",
  "temperature": 27.3,
  "humidity": 54.1,
  "trend_window": "10m",
  "trend_points": []
}
```

오류 처리:
- `404`: 공장 미존재
- `500`: 조회 실패

비고:
- `temperature`, `humidity`는 일부 상황에서 `null` 가능
- TODO: `trend_points` 내부 구조 확정

### 3. GET `/api/systems/abnormal`

목적:
- 이상 시스템 목록 조회

쿼리 파라미터:
- `factory_id` 선택
- `limit` 선택
- `severity` 선택 후보

응답 필드:
- `factory_id`
- `component_type`
- `status`
- `occurred_at`
- `updated_at` 후보
- `environment_type` 후보

응답 예시:

```json
[
  {
    "factory_id": "factory-b",
    "component_type": "pipeline",
    "status": "abnormal",
    "occurred_at": "2026-04-24T09:05:00Z"
  }
]
```

오류 처리:
- `400`: 파라미터 오류
- `500`: 목록 집계 실패

비고:
- 목록 정렬은 기본적으로 공장 위험도 우선, 같은 위험도 안에서는 최신 발생 순이다.

### 4. GET `/api/logs/recent`

목적:
- 최근 상태 변화/이벤트 로그 조회

쿼리 파라미터 후보:
- `limit`
- `factory_id`
- `type`

응답 필드:
- `type`
- `factory_id`
- `message`
- `timestamp`
- `raw_code` 후보

응답 예시:

```json
[
  {
    "type": "state_change",
    "factory_id": "factory-c",
    "message": "위험 상태로 변경",
    "timestamp": "2026-04-24T09:10:00Z"
  }
]
```

오류 처리:
- `400`: 파라미터 오류
- `500`: 로그 조회 실패

비고:
- 이 API는 모든 이벤트를 내려주기보다, 운영 판단에 필요한 변화 중심 로그를 제공한다.

### 5. GET `/api/pipeline/status`

목적:
- 공장별 `pipeline_status` 조회

응답 필드:
- `factory_id`
- `pipeline_status`
- `last_seen_at`
- `processed_at` 후보
- `delay_state` 후보

응답 예시:

```json
[
  {
    "factory_id": "factory-a",
    "pipeline_status": "healthy",
    "last_seen_at": "2026-04-24T09:11:00Z"
  }
]
```

오류 처리:
- `500`: 파이프라인 상태 집계 실패

비고:
- `pipeline_status`는 Edge 보고값이 아니라 Hub 계산값이다.
- 현재 구조는 주기 집계형이므로 즉시 반영되지 않을 수 있다.

## 추가 API 후보

### 6. GET `/api/factories/{factory_id}/risk`

목적:
- 공장 상세 화면이 생길 경우 Risk 상태 상세 조회

상태:
- candidate

### 7. GET `/api/health/overview`

목적:
- Hub 내부 관제 보조 상태를 한 번에 조회

상태:
- candidate

## 구현 메모

- 현재 API는 모두 조회성(read-only) 기준이다.
- Dummy 시나리오 수동 전환 API는 아직 범위에 포함하지 않는다.
- 실제 구현 시 응답 envelope, pagination, 인증은 별도 정책이 필요하다.

## TODO

- TODO: 인증/인가 필요 여부 확인
- TODO: 실 구현 경로와 메서드 확정
- TODO: 오류 코드 체계 표준화
- TODO: 공통 응답 envelope 사용 여부 확정
- TODO: 추세 데이터 포맷 확정
