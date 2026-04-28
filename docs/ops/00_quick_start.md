# Quick Start

상태: draft
기준일: 2026-04-24

## 목적

프로젝트를 처음 시작하는 사람이 `무엇부터 해야 하는지`를 짧은 순서로 이해하고, 더 상세한 운영 문서로 이동할 수 있게 안내한다.

## 현재 상태

- 현재 문서는 `구성 순서 + 단계별 확인 포인트` 중심이다.
- 실제 설치 명령, yaml, values, playbook은 후속 운영 문서에서 보강한다.
- 구현 순서는 `docs/issues/` 하위 마일스톤 문서를 기준으로 M0~M7 흐름을 따른다.

## 범위

- 시작 전 확인 사항
- 최소 시작 순서
- 단계별 완료 판단
- 상세 문서 이동 경로

## 상세 내용

## 이 문서를 먼저 읽어야 하는 경우

- 프로젝트를 처음 셋업하는 경우
- Safe-Edge 기준선부터 다시 구성해야 하는 경우
- Hub/Spoke 전체 순서를 빠르게 파악하려는 경우

## 시작 전 확인 사항

- `factory-a`용 Raspberry Pi 노드와 네트워크 전제가 준비되어 있는가
- AWS Hub 계정/리소스 생성 권한이 있는가
- `factory-b`, `factory-c`용 VM 환경을 만들 수 있는가
- Tailscale 가입/키 발급 방식이 정리되어 있는가
- 현재 구조 기준 문서를 읽었는가
  - `docs/architecture/00_current_architecture.md`
  - `docs/planning/02_implementation_plan.md`
  - `docs/ops/01_safe_edge_bootstrap.md`

## 어디서부터 시작할지 판단

### 아직 `factory-a` Safe-Edge 기준선이 없는 경우

- 이 문서에서 전체 순서를 확인한 뒤
- 바로 `docs/ops/01_safe_edge_bootstrap.md`로 이동한다.

### `factory-a`는 이미 있고 Hub 확장부터 시작하는 경우

- 이 문서의 `2단계`부터 진행한다.

## 최소 시작 순서

1. M0 `factory-a` Safe-Edge 기준선 구성
2. M1 AWS Hub 준비
3. M2 Tailscale로 Hub-`factory-a` 연결
4. M3 `factory-a` 배포 파이프라인 확인
5. M4 `factory-a` 데이터 플레인 확인
6. M5 `factory-b`, `factory-c` 테스트베드형 Spoke 추가
7. M6 Risk Twin 및 관제 화면 확인
8. M7 통합 검증 및 문서 보정

## 단계별 요약

### 1. M0 `factory-a` Safe-Edge 기준선 구성

목표:
- 실제 운영형 Spoke 하나를 먼저 안정화한다.

주요 산출물:
- Raspberry Pi 3노드 K3s
- Longhorn / NFS
- Safe-Edge 입력 계층
- 기본 모니터링

완료 판단:
- `factory-a`가 실제 입력을 올린다.
- Safe-Edge 기준선 완료 조건을 만족한다.

상세 문서:
- `docs/ops/01_safe_edge_bootstrap.md`

### 2. M1 AWS Hub 준비

목표:
- 중앙 제어/관제의 기준선을 만든다.

주요 산출물:
- EKS
- ArgoCD
- Grafana
- IoT Core
- S3
- AMP
- Risk Score Engine
- `runtime-config.yaml` 구조

완료 판단:
- Hub 핵심 서비스가 배치되어 있다.
- Spoke 연결을 받을 준비가 되어 있다.

### 3. M2 Tailscale 연결

목표:
- Hub가 `factory-a` Spoke Master에 접근 가능해야 한다.

완료 판단:
- Hub에서 `factory-a` Master API 접근이 가능하다.
- ArgoCD가 `factory-a` 클러스터를 등록할 수 있다.

### 4. M3 `factory-a` 배포 파이프라인

목표:
- GitHub Push -> ECR -> ArgoCD -> `factory-a` 롤아웃이 실제로 동작해야 한다.

완료 판단:
- `Sync`
- `Healthy`
- 대상 파드 `Running`

### 5. M4 `factory-a` 데이터 플레인

목표:
- `factory-a` 데이터가 실제로 IoT Core와 S3까지 올라와야 한다.

완료 판단:
- `입력 모듈 -> Edge Agent -> IoT Core -> S3` 확인
- 정규화/판단 수행 확인
- `pipeline_status` 계산 확인

### 6. M5 테스트베드형 Spoke 추가

목표:
- `factory-b`, `factory-c`를 Dummy 기반 테스트베드형 Spoke로 추가한다.

완료 판단:
- 두 VM이 독립 공장으로 식별된다.
- Dummy 데이터를 보낼 준비가 된다.
- 세 공장이 Hub에서 함께 보인다.

### 7. M6 Risk Twin 및 관제 화면

목표:
- 상태 변화가 Risk Score와 메인 대시보드에 반영되어야 한다.

완료 판단:
- 상태 카드, 센서 현황, 이상 시스템 목록, 로그가 갱신된다.

### 8. M7 통합 검증

목표:
- 운영형, 테스트베드형, Failover, 롤백 시나리오를 전체 검증한다.

완료 판단:
- `docs/ops/03_test_checklist.md` 보정 완료
- 문서와 실제 구현이 일치한다.

## 빠른 확인 포인트

- `factory-a`가 실제 입력을 올리는가
- VM Spoke가 Dummy 데이터를 올리는가
- Hub가 3개 공장을 구분하는가
- 위험 상태 카드가 변하는가

## 지금 당장 막히기 쉬운 지점

- `factory-a`를 건너뛰고 Hub부터 시작하려는 경우
  - 이 프로젝트는 Safe-Edge 기준선이 선행 조건이다.
- VM을 운영형 Spoke처럼 구성하려는 경우
  - `factory-b`, `factory-c`는 테스트베드형 Spoke다.
- `pipeline_status`를 Edge가 보내는 값으로 이해하는 경우
  - 현재 구조에서는 Hub 계산 상태다.
- 메인 카드에서 Risk Score 숫자를 먼저 보여주려는 경우
  - 현재 MVP는 상태 중심 관제를 우선한다.

## 다음에 읽을 문서

- Safe-Edge 실제 복구:
  - `docs/ops/01_safe_edge_bootstrap.md`
- 현재 구조 이해:
  - `docs/architecture/00_current_architecture.md`
- 단계 계획:
  - `docs/planning/02_implementation_plan.md`
- 대시보드 요구사항:
  - `docs/specs/monitoring_dashboard/00_requirements.md`

## TODO

- TODO: 실제 명령 예시 추가
- TODO: 환경 변수/인증 정보 목록 추가
- TODO: AWS 계정/리소스 준비 체크리스트 추가
