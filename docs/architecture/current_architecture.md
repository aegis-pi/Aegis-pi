# 현재 구조 요약

상태: source of truth
기준일: 2026-04-24

## 목적

현재 freeze된 Aegis-Pi 구조를 구현 기준 관점에서 요약한다.

## 현재 상태

- 이 문서는 현재 설계 기준 구조를 설명한다.
- 수치 기준 일부는 테스트 후 보정 예정이다.
- 실제 구현은 아직 시작 전이므로, 이 문서는 "현재 freeze된 설계 기준"을 설명한다.
- `docs/issues/` 하위 마일스톤 문서를 반영해 현재 구현 순서와 현재 MVP 저장/관제 해석을 함께 정리한다.

## 범위

- Hub/Spoke 구조
- 공장 역할
- 데이터/제어 평면
- 현재 확정된 운영 원칙
- 현재 구조에서 구현 범위와 후속 확장 범위의 경계

## 상세 내용

## 전체 구조

- Hub: AWS EKS 기반 중앙 제어/관제 영역
- Spoke:
  - `factory-a`: 실제 운영형 Raspberry Pi Safe-Edge K3s
  - `factory-b`: Mac mini VM K3s 테스트베드
  - `factory-c`: Windows VM K3s 테스트베드

현재 구조는 `Hub가 여러 독립 Spoke를 중앙에서 다루는 구조`다.
즉, 클라우드와 엣지가 하나의 단일 Kubernetes 클러스터를 이루는 방식이 아니라,
`EKS Hub + 공장별 독립 K3s Spoke` 구조를 기준으로 한다.

## 공장별 역할

### `factory-a`

- 실제 운영형 Spoke
- Safe-Edge 기준선 복구 대상
- Longhorn 유지
- 실제 센서/카메라/마이크/시스템 상태 입력 사용

### `factory-b`

- Mac mini VM 기반 테스트베드형 Spoke
- Dummy 시나리오 기반 검증
- Longhorn 제외
- 배포 검증 + 데이터 플레인 검증 대상

### `factory-c`

- Windows VM 기반 테스트베드형 Spoke
- Dummy 시나리오 기반 검증
- Longhorn 제외
- 배포 검증 + 데이터 플레인 검증 대상

## 제어 평면

- GitHub Push
- GitHub Actions
- ECR
- ArgoCD
- Tailscale 경유 Spoke 롤아웃

제어 평면의 목적은 아래와 같다.

- 표준 템플릿을 여러 공장에 배포
- 공장별 values 기준으로 ApplicationSet 생성
- 운영형 Spoke와 테스트베드형 Spoke의 sync 정책 차등 적용
- 배포 상태를 `Sync / Healthy / Running` 기준으로 확인

현재 제어 평면 해석:

`GitHub Push -> GitHub Actions -> ECR -> ArgoCD -> Tailscale -> 각 Spoke 롤아웃`

## 데이터 평면

- 입력 모듈
- Edge Agent
- IoT Core
- S3
- 정규화/판단
- Risk Score 처리

데이터 평면의 목적은 아래와 같다.

- Edge 입력을 표준 경로로 수집
- IoT Core와 S3를 통해 중앙 적재
- EKS 내부 정규화/판단 서비스에서 처리
- Risk Score Engine에 빠르게 반영

현재 데이터 평면 해석:

`입력 모듈 -> Edge Agent -> IoT Core -> S3 -> 정규화/판단 -> Risk Score`

추가 원칙:

- `sensor`, `system_status`, `event`는 Edge origin 입력
- `pipeline_status`는 Hub derived 상태
- `event`는 구조상 수용하지만 현재 점수 반영은 보류
- S3 경로는 `factory_id / source_type / 날짜` 파티셔닝을 기준으로 한다.

## Hub 내부 역할

- `argocd`: 배포 제어
- `observability`: 관제/메트릭
- `risk`: 정규화/판단, Risk Score 처리
- `ops-support`: `pipeline_status` 집계 보조 기능

### EKS 내부 배치 원칙

- 네임스페이스는 기능 기준으로 분리한다.
  - `argocd`
  - `observability`
  - `risk`
  - `ops-support`
- 내부 앱은 역할 단위로 분리한다.
  - `risk`: `risk-score-engine`, `risk-normalizer`
  - `ops-support`: `pipeline-status-aggregator`

### AWS 관리형 서비스 역할

- IoT Core: 중앙 수신 진입점
- S3: 원본 데이터 적재
- AMP: 메트릭 백엔드
- Timestream: 현재 MVP 필수 저장소가 아니라 후속 후보

즉, 현재 구조는 `AWS 관리형 서비스가 백엔드 저장/수집 축`, `EKS가 제어/처리/조회 축`을 맡는 형태다.

## 설정 관리 구조

- 중앙 설정 파일: `configs/runtime/runtime-config.yaml`
- 구조:
  - `global`
  - `factories`
- 필드별 제어:
  - `display`
  - `risk_enabled`
  - `weight`

현재 원칙:
- 초기 운영은 전역 설정을 사용한다.
- 공장별 override 구조는 준비만 되어 있고, 실제 활성화는 후속 단계다.

## Risk 모델 요약

- 표현 방식: 하이브리드
- 상태 단계:
  - 안전
  - 주의
  - 위험
- 내부 점수 구간:
  - 0~39
  - 40~69
  - 70~100

현재 주요 Risk 입력:

- `temperature`
- `humidity`
- `sensor_status`
- `edge_agent_status`
- `node_status`
- `camera_status`
- `mic_status`
- `pipeline_status`

현재 출력:

- 상태
- 내부 Risk Score
- 최근 10분 변화량
- 주요 원인 Top 3
- `event_timestamp`
- `processed_at`

현재 MVP에서 Risk Twin 결과는 별도 저장소를 강하게 전제하지 않고, Prometheus 호환 메트릭 형태로 노출해 AMP / Grafana 축에서 읽는 구조를 우선한다.

## 관제 구조 요약

메인 관제 화면은 아래 구조를 기준으로 한다.

- 상단: 공장별 위험 상태 카드
- 중단 왼쪽: 온도/습도 센서 현황
- 중단 오른쪽: 이상 시스템 목록
- 하단: 최근 상태 변화 / 주요 이벤트 로그

카드에는 아래를 보여준다.

- 공장명
- 현재 상태
- 최근 10분 변화 방향
- 이상 시스템 개수

메인 카드에는 내부 점수를 직접 노출하지 않는다.

## 운영형 / 테스트베드형 차이

| 구분 | 운영형 (`factory-a`) | 테스트베드형 (`factory-b`, `factory-c`) |
| --- | --- | --- |
| 입력 | 실제 센서/상태 | Dummy 시나리오 |
| 스토리지 | Longhorn 유지 | Longhorn 제외 |
| 배포 정책 | 보수적 | 더 빠른 반영 허용 |
| 실패 처리 | 수동 확인 | 자동 롤백 허용 |

## 현재 구현 범위와 후속 확장 범위

### 현재 구현 범위

- `factory-a` Safe-Edge 기준선 복구
- Hub 기준선 구성
- Mesh 기반 `factory-a` 연결
- `factory-a` 배포 파이프라인
- `factory-a` 데이터 플레인
- `factory-b`, `factory-c` 테스트베드형 Spoke 추가
- Risk Twin + 메인 관제 화면

### 후속 확장 범위

- `event` 기반 Risk 반영
- 별도 이벤트 경로
- Analysis 계층
- LLM 기반 보고서/후처리
- 공장별 override 실운영 활성화
- 큐/이벤트 기반 데이터 트리거

## 구현 시작 순서에서의 위치

이 문서는 "최종 목표 구조" 설명이 아니라,
현재 실제 작업 순서에서 아래 위치를 설명한다.

1. `factory-a` Safe-Edge 기준선 복구
2. Hub 기준선 구성
3. Mesh 기반 `factory-a` 연결
4. `factory-a` 배포/데이터 기준선 구성
5. VM Spoke 확장
6. Risk Twin 관제 연결
7. 통합 검증

즉, 현재 구조 문서는 Hub부터 단독으로 구현하는 문서가 아니라,
Safe-Edge 기준선 이후 어떤 식으로 전체 구조를 묶을지 설명하는 기준 문서다.

## TODO

- TODO: 구현 후 실제 배포 구조 이미지 추가
- TODO: 실제 네임스페이스/앱 배치 다이어그램 추가
