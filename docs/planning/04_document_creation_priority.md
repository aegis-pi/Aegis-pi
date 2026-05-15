# 문서 생성 우선순위

상태: source of truth
기준일: 2026-04-28

## 목적

프로젝트 문서 중 어떤 파일을 먼저 유지해야 하는지 우선순위를 정리하고, 각 파일이 무엇을 담고 어떤 역할을 하는지 빠르게 파악할 수 있도록 한다.

## 현재 상태

- `factory-a` Safe-Edge 기준선은 구축 및 실측 검증까지 완료됐다.
- 현재 문서 우선순위는 신규 생성보다 실제 상태 반영과 후속 Hub 확장 준비에 맞춘다.

## 우선순위 기준

우선순위는 아래 기준으로 판단한다.

1. 현재 실제 운영 상태를 설명하는가
2. 다음 작업 순서에 직접 영향을 주는가
3. 테스트 결과와 장애 대응 기준을 담는가
4. 후속 Hub/Risk Twin 확장의 기준점 역할을 하는가

## 1차 유지 문서

### 1. `README.md`

- 역할:
  - GitHub 진입점
  - 현재 프로젝트 상태와 읽기 순서 제공
- 핵심 내용:
  - `factory-a` 완료 범위
  - 다음 단계
  - 주요 운영 주소

### 2. `docs/README.md`

- 역할:
  - `docs/` 전체 문서 체계의 진입점
  - 문서 상태와 읽기 순서 제공
- 핵심 내용:
  - 현재 source of truth
  - 문서 그룹별 목적
  - 후속 단계 문서 경로

### 3. `docs/ops/05_factory_a_status.md`

- 역할:
  - 현재 `factory-a` 상태 요약
- 핵심 내용:
  - K3s/ArgoCD/Longhorn/Grafana/InfluxDB/AI 앱 상태
  - 완료 범위와 보류 범위

### 4. `docs/ops/06_argocd_gitops.md`

- 역할:
  - ArgoCD와 GitHub GitOps 운영 기준
- 핵심 내용:
  - GitHub repo URL
  - ArgoCD UI 등록 및 sync 방식
  - `monitoring`, `ai-apps` 분리

### 5. `docs/ops/07_grafana_dashboard.md`

- 역할:
  - Grafana 대시보드 구성 기준
- 핵심 내용:
  - InfluxDB 센서/AI 패널
  - 최근 N개 평균과 value mapping
  - Prometheus dashboard `1860`

### 6. `docs/ops/08_data_retention.md`

- 역할:
  - 로컬 데이터 보존 정책
- 핵심 내용:
  - InfluxDB 1일 retention
  - Longhorn replica와 retention 관계
  - AI snapshot 24시간 cleanup

### 7. `docs/ops/09_failover_failback_test_results.md`

- 역할:
  - 실제 장애 테스트 결과 기록
- 핵심 내용:
  - LAN 제거 테스트
  - 전원 제거 테스트
  - 데이터 공백 분석

### 8. `docs/ops/04_troubleshooting.md`

- 역할:
  - 대표 장애 유형과 점검 방향 정리
- 핵심 내용:
  - ArgoCD, Grafana, InfluxDB, Longhorn, failback, prepull, snapshot 문제

### 9. `docs/ops/11_ansible_test_automation.md`

- 역할:
  - `start_test` 기반 반복 검증 절차를 Ansible playbook으로 표준화하기 위한 계획
- 핵심 내용:
  - baseline 수집
  - 테스트 실행
  - failover/failback 관측
  - InfluxDB bucket query
  - evidence pack 생성

## 2차 유지 문서

### 1. `docs/planning/00_project_overview.md`

- 역할:
  - 프로젝트 전체 문제 정의와 현재 상태 고정

### 2. `docs/planning/01_safe_edge_transition.md`

- 역할:
  - Safe-Edge 기준선에서 Aegis-Pi 확장으로 넘어가는 전략 정리

### 3. `docs/planning/02_implementation_plan.md`

- 역할:
  - M0 완료 후 M1~M7 구현 순서 정리

### 4. `docs/planning/03_evaluation_plan.md`

- 역할:
  - 실측 결과와 후속 평가 기준 정리

### 5. `docs/planning/05_decision_rationale.md`

- 역할:
  - 주요 기술 선택과 대안 보류 이유 정리
- 핵심 내용:
  - K3s + Edge data-plane + IoT Core 선택 이유
  - Greengrass, Lambda, 직접 HTTP API, Custom Dashboard 보류 이유
  - ArgoCD/ApplicationSet, Dashboard VPC/DynamoDB LATEST-HISTORY, Ansible 자동화 선택 이유

### 6. `docs/planning/06_edge_agent_deployment_plan.md`

- 역할:
  - 클라우드 송신용 adapter/publisher 이미지와 K3s 배포 기준 정리
- 핵심 내용:
  - 예상 CPU/Memory
  - worker2 preferred / worker1 failover / master avoid 배치
  - AWS IoT 인증서 Secret mount
  - InfluxDB/Kubernetes API 기반 초기 수집 방식

### 7. `docs/architecture/00_current_architecture.md`

- 역할:
  - 현재 `factory-a` 로컬 아키텍처 설명

### 8. `docs/architecture/01_target_architecture.md`

- 역할:
  - AWS Hub와 멀티 공장 확장 목표 설명

## 3차 유지 문서

### 1. `docs/specs/monitoring_dashboard/`

- 역할:
  - 현재 Grafana 구성과 후속 Risk Twin 관제 요구사항 정리

### 2. `docs/product/`

- 역할:
  - MVP 범위와 사용자 흐름 정리

### 3. `docs/demo/`

- 역할:
  - 시연 순서와 운영 메모

### 4. `docs/presentation/`

- 역할:
  - 발표/검토용 요약

### 5. `docs/report/`

- 역할:
  - 보고서 초안과 executive summary

## 권장 운영 방식

1. 실제 `factory-a` 상태가 바뀌면 `docs/ops/05_factory_a_status.md`부터 갱신한다.
2. GitOps, Grafana, retention, failover 관련 변경은 각각의 `docs/ops/06~09` 문서에 먼저 반영한다.
3. 반복 검증 자동화 범위가 바뀌면 `docs/ops/03_test_checklist.md`와 `docs/ops/11_ansible_test_automation.md`를 함께 갱신한다.
4. 운영 문서 변경이 프로젝트 방향에 영향을 주면 planning, architecture, product 문서를 따라 갱신한다.
5. 발표나 데모 일정이 잡히면 demo, presentation, report 문서를 마지막에 맞춘다.
