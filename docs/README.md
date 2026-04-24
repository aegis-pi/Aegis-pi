# Aegis-Pi Docs

상태: source of truth
기준일: 2026-04-24

## 목적

이 디렉터리는 Aegis-Pi 프로젝트를 설계, 구현, 운영, 시연하기 위한 공식 문서 집합이다.
문서는 `계획`, `제품`, `아키텍처`, `기능 스펙`, `운영`, `데모`, `발표`, `보고서`로 분리한다.

## 현재 상태

- 문서 기준 프로젝트명: `Aegis-Pi Risk Twin`
- 현재 프로젝트는 `factory-a`의 Safe-Edge 기준선을 먼저 재구성한 뒤, Hub/Spoke 멀티 공장 구조로 확장하는 단계로 정의한다.
- 실제 구현 산출물 일부는 아직 미정이며, 필요한 부분은 `TODO:`와 `확인 필요`로 표시한다.
- `docs/`는 현재 `docs/issues/` 하위 마일스톤(M0~M7) 흐름과 맞춰 정리된 상태다.
- 현재 문서 점검 기준으로 `factory-d`, `factory-e` 같은 구식 공장 식별자는 남아 있지 않다.
- 실제 구현 순서를 따라 작업할 때는 `docs/issues/`의 마일스톤 문서를 실행 기준으로 본다.

## 범위

- 프로젝트 배경과 계획
- MVP 범위와 사용자 흐름
- 현재 구조와 목표 구조
- 관제 대시보드 기능 스펙
- 운영 및 시연 가이드
- 발표/보고용 요약 자료

## 상세 내용

### 읽기 우선순위

1. `planning/00_project_overview.md`
2. `product/mvp_scope.md`
3. `architecture/current_architecture.md`
4. `ops/safe_edge_bootstrap.md`
5. `specs/monitoring_dashboard/requirements.md`
6. `planning/04_document_creation_priority.md`
7. `issues/` 하위 마일스톤 문서

### 현재 추천 읽기 순서

#### 구조를 이해할 때

1. `planning/00_project_overview.md`
2. `planning/01_safe_edge_transition.md`
3. `architecture/current_architecture.md`
4. `planning/02_implementation_plan.md`

#### 실제 구축을 시작할 때

1. `ops/quick_start.md`
2. `ops/safe_edge_bootstrap.md`
3. `planning/02_implementation_plan.md`
4. `planning/03_evaluation_plan.md`

#### 관제 화면을 구현하거나 수정할 때

1. `specs/monitoring_dashboard/requirements.md`
2. `specs/monitoring_dashboard/screen_plan.md`
3. `specs/monitoring_dashboard/api_spec.md`
4. `specs/monitoring_dashboard/data_model.md`

### 핵심 원칙

- Safe-Edge를 먼저 세운다.
- `factory-a`는 실제 운영형 Spoke로 취급한다.
- `factory-b`, `factory-c`는 테스트베드형 Spoke로 취급한다.
- Hub는 AWS EKS 기반 중앙 제어/관제 지점으로 둔다.
- 위험도는 `안전 / 주의 / 위험` 3단계 하이브리드 모델로 관리한다.
- 이벤트 기반 확장과 분석 계층은 열어두되, 현재 MVP 문서와 혼합하지 않는다.

### 문서 상태 규칙

- `source of truth`: 현재 구현/설계 기준 문서
- `draft`: 방향은 있으나 세부값이 미정인 문서
- `candidate`: 후속 확장 또는 검토용 문서

### 문서 우선순위 관리

- 어떤 문서를 먼저 작성/보강해야 하는지는 `planning/04_document_creation_priority.md`를 기준으로 관리한다.

### 실행 기준 문서

- 설계와 설명은 `docs/` 각 문서를 본다.
- 실제 구현 순서와 작업 단위는 `docs/issues/`의 M0~M7 문서를 기준으로 진행한다.
- 구현 중 문서 보정이 필요하면
  - 구조 변경은 `planning/`, `architecture/`, `specs/`
  - 실행 절차 변경은 `ops/`
  - 마일스톤 작업 단위 변경은 `issues/`
  를 갱신한다.

### 현재 정합성 점검 메모

- `docs/`의 구현 순서는 현재 `M0 -> M7` 흐름을 기준으로 정리되어 있다.
- `planning/02_implementation_plan.md`와 `planning/03_evaluation_plan.md`는 마일스톤 기준으로 다시 맞춰져 있다.
- `ops/quick_start.md`와 `ops/safe_edge_bootstrap.md`는 실제 구축 시작 순서와 연결된다.
- `architecture/current_architecture.md`는 현재 MVP 기준 구조만 설명하고, 확장 구조는 `architecture/target_architecture.md`로 분리한다.
- `presentation/`과 `report/`는 현재 구조를 요약한 문서이며, 실제 구현 산출물의 source of truth는 아니다.

## TODO

- TODO: 실제 실행 명령, yaml, values, playbook이 생성되면 `ops/` 문서를 보강한다.
- TODO: 구현이 시작되면 API와 데이터 모델 세부값을 `specs/`에 반영한다.
