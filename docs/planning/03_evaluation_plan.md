# 테스트 및 평가 계획

상태: draft
기준일: 2026-04-24

## 목적

프로젝트를 어떤 축으로 검증할지 정의하고, 마일스톤 완료 기준과 테스트 후 보정 항목을 구분한다.

## 현재 상태

- 구조 기준은 정리되었고, 세부 수치 기준은 테스트 후 보정 예정이다.
- 현재는 "무엇을 성공으로 볼 것인가"를 고정하는 단계이며, 일부 수치 기준은 후속 실측으로 확정한다.
- `docs/issues/M7_integration-test.md` 기준 시나리오를 반영해 운영형, 테스트베드형, Failover, 롤백 검증을 포함한다.

## 범위

- 검증 축
- 성공 기준
- 실측 필요 항목
- 마일스톤별 검증 시점
- 테스트 후 보정 항목

## 상세 내용

## 평가 축

### 1. 인프라 축

- 배포 파이프라인 동작 여부
- Spoke 등록/배포 성공 여부
- Tailscale 연결 상태

현재 검증 포인트:
- ApplicationSet 생성 가능 여부
- `factory-a`, `factory-b`, `factory-c` 대상 분리 가능 여부
- 운영형/테스트베드형 sync 정책 차등 반영 여부
- Tailscale 경유 접근 가능 여부

### 2. 데이터 플레인 축

- 입력 모듈 -> Edge Agent -> IoT Core -> S3 적재
- `pipeline_status` 계산
- 정규화/판단 계층 동작

현재 검증 포인트:
- 운영형 Spoke 실제 입력 수집 여부
- 테스트베드형 Dummy 입력 수집 여부
- S3 적재 확인
- 정규화/판단 계층 동작 여부
- Risk Score Engine 호출 가능 여부

### 3. Risk Twin 축

- 상태 전환
- 내부 점수 변화
- 주요 원인 Top 3 반영

현재 검증 포인트:
- `안전 / 주의 / 위험` 상태 변화
- 최근 10분 변화 방향
- 주요 원인 필드 반영
- 메인 대시보드 표시 일관성

### 4. 가용성/복구 축

- 센서 무수신 감지
- 노드/서비스 이상 감지
- Failover 반영
- 배포 실패/롤백 반영

현재 검증 포인트:
- 센서 무수신 반영 여부
- `edge_agent_status`, `node_status`, `pipeline_status` 이상 반영 여부
- 운영형과 테스트베드형 장애 처리 차등 정책 설명 가능 여부
- Worker-2 장애 -> Worker-1 승계 흐름 확인 가능 여부

## 현재 성공 기준

| 항목 | 현재 기준 | 상태 |
| --- | --- | --- |
| 배포 성공 | `Sync`, `Healthy`, `Running` | 확정 |
| 데이터 플레인 성공 | S3 적재 확인 포함 | 확정 |
| Risk Twin 검증 | 상태 + 원인 확인 | 확정 |
| 배포 지연 시간 수치 | TODO | 미정 |
| 온습도 기준값 | TODO | 미정 |

추가 기준:

| 항목 | 현재 기준 | 상태 |
| --- | --- | --- |
| 운영형 Spoke 검증 | 운영 흐름형 + 센서 무수신 포함 | 확정 |
| 테스트베드형 Spoke 검증 | 시나리오 검증형 | 확정 |
| Dummy 전환 방식 | 간단한 제어 입력형 | 확정 |
| `pipeline_status` 성격 | Hub 계산 상태 | 확정 |
| 운영형 롤백 정책 | 수동 확인 후 조치 | 확정 |
| 테스트베드형 롤백 정책 | 자동 롤백 허용 | 확정 |

## 실측이 필요한 항목

- 배포 지연 시간
- IoT Core -> S3 적재 지연
- Risk 반영 지연
- source_type별 지연/누락 수치
- 가중치 보정 효과
- `pipeline_status` 주기 집계 간격 적정성
- 메인 대시보드 반응 속도
- 운영형/테스트베드형 상태 반영 차이

## 마일스톤별 검증 시점

### M0 후 검증

- `factory-a` Safe-Edge 기준선 복구 여부
- 센서/상태/모니터링 경로 확인
- Longhorn / NFS 기준선 확인

### M1 후 검증

- Hub 핵심 서비스 배치 여부
- 네임스페이스/앱 배치 기준 설명 가능 여부
- `runtime-config.yaml` 구조 준비 여부

### M2 후 검증

- Hub -> `factory-a` API 접근 가능 여부
- ArgoCD `factory-a` 테스트 배포 가능 여부

### M3 후 검증

- GitHub Push -> ECR -> ArgoCD -> `factory-a` 롤아웃 확인
- 운영형 배포 실패 시 수동 대응 흐름 설명 가능 여부

### M4 후 검증

- IoT Core -> S3 적재 확인
- 정규화/판단 -> Risk Score 처리 확인
- `pipeline_status` 반영 확인

### M5 후 검증

- `factory-b`, `factory-c` Dummy 입력 반영
- 3개 공장 Fleet 인식 여부
- 테스트베드형 자동 롤백 정책 확인

### M6 후 검증

- Risk Score 변화가 관제 화면에 반영되는지 확인
- 상태 카드 / 이상 목록 / 로그 패널 동작 확인

### M7 후 검증

- 운영형 시나리오
- 테스트베드형 시나리오
- Failover 시나리오
- 롤백 시나리오
- `docs/ops/03_test_checklist.md` 전수 보정

## 운영형 / 테스트베드형 평가 차이

### 운영형 Spoke(`factory-a`)

- 실제 입력이 들어오는가
- Safe-Edge 기준선이 유지되는가
- 센서 무수신 시나리오가 반영되는가
- Failover가 Hub 관제에 반영되는가

### 테스트베드형 Spoke(`factory-b`, `factory-c`)

- Dummy 입력이 정상적으로 수집되는가
- `normal / warning / danger` 시나리오 전환이 반영되는가
- 배포 실패 시 자동 롤백 정책이 실제로 동작하는가

## M7 통합 시나리오 기준

### 1. 운영형 시나리오

- 정상 상태 baseline 기록
- 실 센서 데이터 기반 Risk Score 계산
- 센서 무수신 -> 이상 판정 -> 관제 반영
- 배포 후 데이터 수집 재개

### 2. 테스트베드 시나리오

- `factory-b`, `factory-c` 각각 상태 전환
- Edge Agent 종료 / 재기동
- Dummy 중지에 따른 `pipeline_status` 이상 판정

### 3. Failover 시나리오

- Worker-2 장애
- Worker-1 승계
- Longhorn 데이터 유지
- Hub 관제에서 `node_not_ready` 반영

### 4. 롤백 시나리오

- `factory-a`: 실패 시 기존 파드 유지 + 수동 복구
- `factory-b`: 실패 시 자동 롤백

## 테스트 후 보정 대상

- 온도/습도 기준값
- Risk 가중치
- source_type별 지연/누락 수치
- 배포 지연 시간 수치
- Dummy 시나리오 세부값
- null 허용 정책
- 보존 기간 수치

## TODO

- TODO: 실제 실측표 템플릿 추가
- TODO: 테스트 결과 입력 섹션 추가
- TODO: 마일스톤별 실측 결과 링크 연결
