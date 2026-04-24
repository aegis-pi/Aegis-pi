# 프로젝트 보고서 초안

상태: draft
기준일: 2026-04-24

## 목적

중간 보고서 또는 최종 보고서 작성 시 바로 수정해 사용할 수 있는 본문 초안을 제공한다.

## 현재 상태

- 본 문서는 구조 설계 1차 완료 시점의 보고서 초안이다.
- 실제 실측, 캡처, 수치 표는 후속 단계에서 추가해야 한다.

## 범위

- 문제 정의
- 설계 방향
- 시스템 구조
- 구현 계획
- 기대 효과
- 한계 및 후속 계획

## 상세 내용

## 1. 프로젝트 배경

기존 Safe-Edge는 단일 공장 생존형 엣지 시스템으로 의미 있는 기준선을 제공했다. 그러나 멀티 공장 중앙 관제와 공장 단위 위험 상태 표현은 지원하지 못했다.

기존 구조는 현장 생존성과 데이터 보존 측면에서는 유의미했지만, 본사 관제 담당자가 여러 공장을 한 번에 비교하고 위험 상태를 판단하는 구조로 바로 연결되지는 않았다. 따라서 Safe-Edge를 새로 대체하기보다, 기존 기준선을 유지하면서 상위 관제 구조를 덧붙이는 접근이 필요했다.

## 2. 프로젝트 목표

- Safe-Edge 기준선 계승
- 멀티 공장 Fleet 구조 구성
- 중앙 Risk Twin 관제

세부 목표는 다음과 같다.

1. `factory-a`에 Safe-Edge 기준선을 다시 구성한다.
2. `factory-b`, `factory-c`를 테스트베드형 Spoke로 추가한다.
3. AWS EKS 기반 Hub에서 여러 Spoke를 중앙 배포/관제한다.
4. IoT Core -> S3 -> Risk Score 처리 구조를 통해 공장별 위험 상태를 생성한다.

## 3. 시스템 개요

- 운영형 Spoke: `factory-a`
- 테스트베드형 Spoke: `factory-b`, `factory-c`
- Hub: AWS EKS, IoT Core, S3, Grafana, Risk Score Engine

시스템은 `Hub + Spoke` 구조를 따른다.

- Spoke는 공장 단위의 독립 K3s 환경이다.
- Hub는 중앙 제어, 배포, 데이터 집계, 관제를 담당한다.
- 운영형 Spoke와 테스트베드형 Spoke를 구분하여 실환경 보호와 반복 검증을 동시에 달성한다.

## 4. 현재 구조 설명

### 4.1 운영형 Spoke

- `factory-a`
- Raspberry Pi 기반 K3s
- Safe-Edge 기준선 계승
- 실제 센서/상태 입력 사용
- Longhorn 유지

### 4.2 테스트베드형 Spoke

- `factory-b`: Mac mini VM K3s
- `factory-c`: Windows VM K3s
- Dummy 입력 기반
- Longhorn 제외
- 배포, 데이터 플레인, 시나리오 검증 중심

### 4.3 Hub

- AWS EKS
- ArgoCD
- Grafana
- Risk Score Engine
- `pipeline_status` 집계 보조 기능
- IoT Core / S3 / AMP 연계
- Timestream은 현재 MVP 필수 저장소가 아니라 후속 후보

### 4.4 데이터 흐름

- 입력 모듈 -> Edge Agent -> IoT Core -> S3 -> 정규화/판단 -> Risk Score 처리

### 4.5 배포 흐름

- GitHub Push -> GitHub Actions -> ECR -> ArgoCD -> Tailscale -> Spoke 롤아웃

## 5. 핵심 설계 포인트

- Safe-Edge 선행 복구
- Hub/Spoke 분리
- Tailscale 기반 연결
- 하이브리드 위험도 모델

추가로 현재 설계의 핵심 판단은 다음과 같다.

- `pipeline_status`는 Edge 보고값이 아니라 Hub 계산 상태로 둔다.
- 메인 대시보드는 점수보다 상태 중심으로 설계한다.
- 운영형과 테스트베드형의 배포 정책은 다르게 둔다.
- `event`, `analysis`, LLM 계층은 현재 MVP에 넣지 않고 확장 후보로 둔다.

## 6. MVP 범위

- 메인 대시보드
- 데이터 플레인
- Risk Score 처리
- 배포 파이프라인

메인 대시보드의 핵심 정보는 다음과 같다.

- 공장별 위험 상태 카드
- 온도/습도 센서 현황
- 이상 시스템 목록
- 최근 상태 변화 로그

포함하지 않는 범위는 다음과 같다.

- LLM 기반 자동 보고서
- event 기반 Risk 반영
- 별도 이벤트 전용 파이프라인
- 공장별 override 활성화
- 자동화된 장애/복구 리허설

## 7. 구현 계획 요약

1. `factory-a` Safe-Edge 기준선 구성
2. AWS Hub 준비
3. `factory-b`, `factory-c` 테스트베드형 Spoke 구성
4. Tailscale 연결
5. ArgoCD 배포 확인
6. IoT Core -> S3 -> Risk Score -> 대시보드 확인

## 8. 평가 계획 요약

- 배포 성공 기준:
  - `Sync`
  - `Healthy`
  - 대상 파드 `Running`
- 데이터 플레인 성공 기준:
  - 입력 모듈 -> Edge Agent -> IoT Core -> S3 적재 확인
- Risk Twin 성공 기준:
  - 상태 전환
  - 내부 점수 변화
  - 주요 원인 Top 3 반영

## 9. 기대 효과

- 본사 관제 시야 확보
- 공장별 위험 상태 비교 가능
- 운영형과 테스트베드형 환경을 통한 검증 체계 확보

추가 기대 효과:
- 기존 Safe-Edge 자산을 재사용하면서도 확장 가능성을 유지한다.
- 공장 단위 운영 위험과 데이터 파이프라인 이상을 함께 볼 수 있다.
- 후속으로 event/analysis/보고서 계층을 붙일 수 있는 구조를 확보한다.

## 10. 한계 및 후속 계획

현재 한계:
- 온도/습도 임계값은 테스트 후 보정 필요
- source_type별 지연 기준 수치는 미확정
- 실제 구축 명령과 매니페스트는 아직 미작성

후속 계획:
- event 확장
- analysis 계층
- LLM 기반 일일 보고서/요약
- 공장 수 및 정책 확장

## TODO

- TODO: 실측 결과 추가
- TODO: 화면 캡처 추가
- TODO: 비용/성능 표 추가
- TODO: 평가 결과 표 추가
