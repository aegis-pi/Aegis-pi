# 문서 생성 우선순위

상태: source of truth
기준일: 2026-04-24

## 목적

프로젝트 문서 중 어떤 파일을 먼저 작성/유지해야 하는지 우선순위를 정리하고, 각 파일이 무엇을 담고 어떤 역할을 하는지 빠르게 파악할 수 있도록 한다.

## 현재 상태

- `docs/` 기본 구조와 초안은 생성되었다.
- 이 문서는 그중에서도 먼저 관리해야 하는 문서와 후순위 문서를 구분하는 운영 기준 문서다.

## 범위

- 우선 생성/유지 대상 문서
- 후순위 작성 대상 문서
- 각 문서의 역할
- 각 문서가 담아야 하는 핵심 내용

## 상세 내용

## 우선순위 기준

우선순위는 아래 기준으로 판단한다.

1. 프로젝트 방향을 결정하는가
2. 구현 시작 전에 반드시 읽어야 하는가
3. 운영/구축 순서에 직접 영향을 주는가
4. 다른 문서의 기준점 역할을 하는가

## 1차 우선 생성/유지 문서

### 1. `docs/README.md`

- 역할:
  - `docs/` 전체 문서 체계의 진입점
  - 읽기 순서와 문서 상태 규칙 제공
- 왜 우선인가:
  - 새 팀원이나 발표 준비자가 가장 먼저 보는 문서이기 때문
  - 다른 모든 문서의 접근 경로를 정리하기 때문
- 핵심 내용:
  - 프로젝트 문서화 원칙
  - 읽기 우선순위
  - 문서 상태 규칙
  - Safe-Edge 선행 원칙

### 2. `docs/planning/00_project_overview.md`

- 역할:
  - 프로젝트의 문제 정의, 목표, 사용자, 핵심 기능을 한 문서에 고정
- 왜 우선인가:
  - 프로젝트 전체 방향을 가장 압축적으로 설명하는 기준 문서이기 때문
- 핵심 내용:
  - 프로젝트명
  - 한 줄 소개
  - 문제 정의
  - 해결 방향
  - 대상 사용자
  - 핵심 기능
  - 현재 구현 상태

### 3. `docs/planning/01_safe_edge_transition.md`

- 역할:
  - Safe-Edge를 왜 기준선으로 삼는지 설명
  - Aegis-Pi가 Safe-Edge에서 무엇을 계승하고 무엇을 확장하는지 정리
- 왜 우선인가:
  - 이 프로젝트는 Safe-Edge를 먼저 복구한 뒤 확장하는 순서가 핵심이기 때문
- 핵심 내용:
  - Safe-Edge 계승 자산
  - Safe-Edge의 한계
  - Aegis-Pi 확장 방향
  - 구현 순서상의 의미

### 4. `docs/architecture/current_architecture.md`

- 역할:
  - 현재 freeze된 구조를 구현 기준으로 설명
- 왜 우선인가:
  - 개발자, 운영자, 발표 준비자가 모두 참조하는 아키텍처 기준 문서이기 때문
- 핵심 내용:
  - Hub/Spoke 구조
  - 공장 역할
  - 제어 평면
  - 데이터 평면
  - Risk 모델 요약
  - 운영형/테스트베드형 차이

### 5. `docs/ops/safe_edge_bootstrap.md`

- 역할:
  - `factory-a` Safe-Edge 기준선을 다시 구성하는 운영 가이드
- 왜 우선인가:
  - 실제 구현이 이 문서 순서에서 시작하기 때문
- 핵심 내용:
  - 선행 조건
  - 노드 역할과 IP
  - K3s/MetalLB/Longhorn/GitOps/모니터링 복구 순서
  - 확인 방법

### 6. `docs/specs/monitoring_dashboard/requirements.md`

- 역할:
  - 본사 관제 대시보드의 기능 요구사항 정의
- 왜 우선인가:
  - Risk Twin 결과를 최종적으로 어떻게 보여줄지 결정하는 기준 문서이기 때문
- 핵심 내용:
  - 사용자
  - 메인 화면 목표
  - 위험 카드 요구사항
  - 센서 현황 요구사항
  - 이상 시스템 목록 요구사항
  - 로그 요구사항

### 7. `docs/product/mvp_scope.md`

- 역할:
  - MVP에 포함되는 것과 제외되는 것을 명확히 구분
- 왜 우선인가:
  - 구현 범위가 퍼지지 않도록 막아주는 제품 기준 문서이기 때문
- 핵심 내용:
  - 포함 범위
  - 제외 범위
  - 후속 확장 범위

## 2차 작성/보강 문서

### 1. `docs/planning/02_implementation_plan.md`

- 역할:
  - 단계별 구현 계획과 완료 조건 정리
- 핵심 내용:
  - Phase별 구현 순서
  - 구현 중 테스트로 정할 항목

### 2. `docs/planning/03_evaluation_plan.md`

- 역할:
  - 검증 축과 평가 기준 정리
- 핵심 내용:
  - 인프라/데이터/Risk/가용성 평가 축
  - 현재 성공 기준
  - 실측 필요 항목

### 3. `docs/product/user_flow.md`

- 역할:
  - 본사 관제 담당자 사용 흐름 정리
- 핵심 내용:
  - 주요 사용자
  - 기본 흐름
  - 예외 흐름

### 4. `docs/ops/quick_start.md`

- 역할:
  - 시작 순서를 짧게 안내
- 핵심 내용:
  - 빠른 시작 절차
  - 빠른 확인 포인트

### 5. `docs/ops/self_check.md`

- 역할:
  - 구성 후 빠른 상태 점검용 체크리스트
- 핵심 내용:
  - Safe-Edge 점검
  - Hub 점검
  - 데이터 플레인 점검
  - Risk Twin 점검

### 6. `docs/ops/troubleshooting.md`

- 역할:
  - 대표 장애 유형과 점검 방향 정리
- 핵심 내용:
  - ArgoCD 문제
  - Tailscale 문제
  - S3 적재 문제
  - Risk 갱신 문제

## 3차 후속 문서

### 1. `docs/architecture/target_architecture.md`

- 역할:
  - 미래 확장 구조 정리
- 핵심 내용:
  - event 확장
  - analysis 계층
  - 데이터 플레인 확장

### 2. `docs/specs/monitoring_dashboard/screen_plan.md`

- 역할:
  - 라우트와 화면 상세 설계
- 핵심 내용:
  - route
  - 상태별 UI
  - 예외 흐름

### 3. `docs/specs/monitoring_dashboard/api_spec.md`

- 역할:
  - API 초안 정리
- 핵심 내용:
  - endpoint
  - request/response
  - error behavior

### 4. `docs/specs/monitoring_dashboard/data_model.md`

- 역할:
  - 조회 데이터 모델과 저장 경계 정리
- 핵심 내용:
  - 엔티티
  - 저장 경계
  - null 정책

### 5. `docs/demo/`, `docs/presentation/`, `docs/report/` 하위 문서

- 역할:
  - 시연, 발표, 보고를 위한 2차 문서
- 핵심 내용:
  - 데모 순서
  - 발표 요약
  - 보고서 초안

## 권장 운영 방식

1. 1차 우선 문서를 먼저 최신 상태로 유지한다.
2. 실제 구현이 시작되면 `ops/`와 `specs/` 문서를 즉시 보강한다.
3. 발표나 데모 일정이 잡히면 `demo/`, `presentation/`, `report/` 문서를 갱신한다.

## 현재 실제 정리 순서

아래 순서는 "파일 생성 순서"가 아니라, 지금 시점에서 내용을 더 구체화해야 하는 실제 작업 순서다.

1. `docs/ops/safe_edge_bootstrap.md`
   - 이유:
     - 실제 구현은 `factory-a` Safe-Edge 기준선에서 시작하기 때문
     - 하드웨어, K3s, Longhorn, GitOps, 모니터링의 선행 순서를 여기서 먼저 잠가야 한다.
   - 보강 목표:
     - 단계별 목표 상태
     - 완료 기준
     - Safe-Edge 완료 후 Aegis-Pi로 넘어가는 조건

2. `docs/architecture/current_architecture.md`
   - 이유:
     - Safe-Edge 기준선 이후 Hub/Spoke 구조를 구현 기준으로 다시 확인해야 하기 때문
   - 보강 목표:
     - Hub 내부 계층 배치
     - 운영형/테스트베드형 차이
     - 제어/데이터 평면 경계 명확화

3. `docs/specs/monitoring_dashboard/requirements.md`
   - 이유:
     - 관제 화면이 최종 사용자에게 보이는 핵심 산출물이기 때문
   - 보강 목표:
     - 화면별 필수 정보
     - 표시 제약
     - 예외 흐름과 상태 표현 정리

4. `docs/planning/02_implementation_plan.md`
   - 이유:
     - 위 3개가 더 구체화된 뒤 전체 구현 단계를 다시 정리해야 하기 때문
   - 보강 목표:
     - Phase별 산출물
     - 선행/후행 관계
     - 테스트 후 보정 항목 위치

위 4개를 먼저 다듬은 뒤, 나머지 2차 문서와 3차 문서를 순차적으로 보강한다.

## TODO

- TODO: 실제 구현이 진행되면 각 문서의 마지막 갱신일을 추가한다.
- TODO: 담당자 필드가 필요하면 문서별 owner를 추가한다.
