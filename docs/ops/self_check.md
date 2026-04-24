# 셀프 체크 가이드

상태: draft
기준일: 2026-04-24

## 목적

구성 후 현재 상태가 최소 기준을 만족하는지 빠르게 판단하기 위한 점검 체크리스트를 제공한다.

## 현재 상태

- 현재 문서는 `구성 직후`, `배포 직후`, `데모 직전`에 공통으로 사용할 수 있는 기준 점검표다.
- 실제 명령과 대시보드 URL은 일부 미정이다.

## 범위

- Safe-Edge 기준선 점검
- Hub 점검
- 데이터 플레인 점검
- Risk Twin 점검
- 테스트베드형 Spoke 점검

## 상세 내용

## 사용 시점

### 1. Safe-Edge 기준선 복구 직후

- `factory-a`의 최소 운영 가능 상태를 확인한다.

### 2. Hub 및 Spoke 배포 직후

- Hub, Tailscale, 배포 파이프라인, 테스트베드형 Spoke를 확인한다.

### 3. 데모 또는 검증 직전

- Risk 상태, 최근 로그, Dummy 전환 반응까지 확인한다.

## 판정 원칙

- 핵심 항목은 모두 `예`여야 다음 단계로 넘어간다.
- 보조 항목은 일부 미정이어도 진행 가능하지만, 데모 직전에는 다시 확인한다.
- 하나라도 실패하면 `troubleshooting.md`를 먼저 본다.

## Safe-Edge 기준선 점검

### 핵심 항목

- [ ] `factory-a` K3s 3노드가 정상인가
- [ ] Master / Worker 역할이 의도대로 구성됐는가
- [ ] Longhorn 복제가 정상인가
- [ ] 센서값이 수집되는가
- [ ] 카메라/마이크 상태가 최소 수준으로 확인되는가
- [ ] Grafana에서 기본 입력이 보이는가

### 실패 시 먼저 볼 것

- `docs/ops/safe_edge_bootstrap.md`
- Longhorn 상태
- 입력 모듈과 Edge Agent 상태

## Hub 점검

### 핵심 항목

- [ ] EKS 핵심 서비스가 배치됐는가
- [ ] `argocd`, `observability`, `risk`, `ops-support` 역할이 분리됐는가
- [ ] ArgoCD가 동기화 가능한가
- [ ] Tailscale 연결이 정상인가
- [ ] Hub가 `factory-a`, `factory-b`, `factory-c`를 구분 가능한가

### 실패 시 먼저 볼 것

- Tailscale Master 연결
- ArgoCD 대상 클러스터 등록 상태
- Hub 핵심 서비스 배치 상태

## 테스트베드형 Spoke 점검

### 핵심 항목

- [ ] `factory-b` K3s가 정상인가
- [ ] `factory-c` K3s가 정상인가
- [ ] Dummy 입력 모듈이 동작하는가
- [ ] 두 공장이 독립 공장으로 식별되는가
- [ ] 운영형/테스트베드형 배포 정책 차이가 반영되는가

### 실패 시 먼저 볼 것

- Dummy 입력 모듈 상태
- values 기반 ApplicationSet 적용 상태
- Tailscale 연결 상태

## 데이터 플레인 점검

### 핵심 항목

- [ ] 입력 모듈 -> Edge Agent 경로가 정상인가
- [ ] IoT Core 수신 확인
- [ ] S3 적재 확인
- [ ] `pipeline_status` 집계 확인
- [ ] `pipeline_status`가 Edge가 아닌 Hub 계산 상태로 반영되는가

### 실패 시 먼저 볼 것

- payload 필수 필드 누락 여부
- IoT Core Rule
- S3 경로 및 날짜 파티셔닝
- `pipeline-status-aggregator` 상태

## Risk Twin 점검

### 핵심 항목

- [ ] 공장별 상태가 보이는가
- [ ] `안전 / 주의 / 위험` 상태가 의도대로 반영되는가
- [ ] 최근 10분 변화 방향이 계산되는가
- [ ] 주요 원인 Top 3가 반영되는가
- [ ] 메인 카드에 내부 Risk Score가 직접 노출되지 않는가

### 시나리오 확인 항목

- [ ] 센서 무수신 시 상태 변화가 보이는가
- [ ] Dummy 시나리오 전환이 관제에 반영되는가
- [ ] 시스템 이상 또는 파이프라인 이상이 목록과 로그에 반영되는가

### 실패 시 먼저 볼 것

- 정규화/판단 서비스
- Risk Score Engine
- 주요 원인 코드 매핑
- 메인 대시보드 조회 데이터

## TODO

- TODO: 각 체크 항목의 실제 명령/대시보드 경로 추가
- TODO: 단계별 점검 결과 기록 표 추가
