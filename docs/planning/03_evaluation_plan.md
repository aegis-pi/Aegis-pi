# 테스트 및 평가 계획

상태: source of truth
기준일: 2026-04-28

## 목적

프로젝트를 어떤 축으로 검증할지 정의하고, 마일스톤 완료 기준과 테스트 후 보정 항목을 구분한다.

## 현재 상태

- M0 `factory-a` Safe-Edge 기준선은 실제 장애 테스트까지 완료됐다.
- 남은 평가는 AWS Hub, Hub-Spoke 연결, 중앙 데이터 플레인, Risk Twin 확장 단계에서 수행한다.
- 실측 결과는 `docs/ops/09_failover_failback_test_results.md`를 기준으로 관리한다.

## 평가 축

### 1. 인프라 축

- K3s 노드 상태
- ArgoCD/Helm 배포 상태
- Longhorn volume/replica 상태
- 이미지 prepull 상태
- Hub-Spoke 연결 상태
- 배포 파이프라인 동작 여부

현재 검증 결과:

- `factory-a` 3노드 K3s 기준선 확인
- ArgoCD 앱 분리 확인
- Longhorn PVC 확인
- `safe-edge-image-prepull` DaemonSet 적용
- Hub-Spoke 연결은 후속

### 2. 데이터 플레인 축

- 입력 모듈 -> InfluxDB 로컬 저장
- InfluxDB retention policy
- AI snapshot 저장 및 cleanup
- 후속 IoT Core -> S3 적재
- `pipeline_status` 계산
- 정규화/판단 계층 동작

현재 검증 결과:

- Grafana에서 InfluxDB 기반 센서/AI 결과 확인
- InfluxDB 1일 retention policy 적용
- AI snapshot 24시간 cleanup 적용
- IoT Core/S3는 후속

### 3. 관제 축

- Grafana 현장 대시보드
- Prometheus node dashboard `1860`
- 후속 Risk Twin 상태 카드
- 주요 원인 Top 3 반영
- 최근 상태 변화 로그

현재 검증 결과:

- Grafana `10.10.10.202` 기준 현장 대시보드 구성
- InfluxDB 센서/AI 패널 구성
- Prometheus dashboard `1860` 구성
- Risk Twin은 후속

### 4. 가용성/복구 축

- worker2 장애 감지
- worker1 failover
- worker2 복구 후 조건부 failback
- Longhorn 데이터 유지
- 데이터 공백/중복 write 분석

현재 검증 결과:

- LAN 제거 기반 failover/failback 완료
- 전원 제거 기반 failover/failback 완료
- 전원 제거 테스트에서 1초 bucket 데이터 공백 측정 완료

## 현재 성공 기준

| 항목 | 현재 기준 | 상태 |
| --- | --- | --- |
| 배포 성공 | ArgoCD `Synced`, `Healthy`, Pod `Running` | 확정 |
| 로컬 데이터 성공 | InfluxDB 최신 timestamp 갱신 | 확정 |
| Grafana 성공 | 센서/AI/노드 패널 표시 | 확정 |
| Failover 성공 | worker2 장애 후 worker1에서 대상 Pod `Running` | 확정 |
| Failback 성공 | worker2 Ready 이후 대상 Pod가 worker2에서 `Running` | 확정 |
| 데이터 공백 분석 | 10초/1초 bucket count 확인 | 확정 |
| Hub 데이터 성공 | IoT Core/S3 적재 확인 | 후속 |
| Risk Twin 성공 | 상태 + 원인 확인 | 후속 |

## M0 실측 요약

전원 제거 테스트 기준:

| 항목 | 결과 |
| --- | --- |
| 전원 제거 관측 후 worker2 NotReady | 약 42초 |
| NotReady 후 worker1 전체 Running | 약 32초 |
| 전원 제거 관측 후 worker1 전체 Running | 약 74초 |
| 전원 재연결 관측 후 worker2 Ready | 약 21초 |
| worker2 Ready 후 worker2 전체 Running | 약 1분 50초 |
| 전원 재연결 관측 후 worker2 전체 Running | 약 2분 11초 |
| 전원 재연결 관측 후 Longhorn healthy | 약 2분 22초 |

1초 bucket 연속 공백:

| 구간 | measurement | 최대 공백 |
| --- | --- | --- |
| failover | `environment_data` | 65초 |
| failover | `ai_detection` | 72초 |
| failover | `acoustic_detection` | 75초 |
| failback | `environment_data` | 2초 |
| failback | `ai_detection` | 2초 |
| failback | `acoustic_detection` | 2초 |

LAN 제거 테스트에서는 10초 bucket 기준 명확한 데이터 공백은 없었고, 일부 중복 write 가능성을 확인했다.

## 마일스톤별 검증 시점

### M0 후 검증

- `factory-a` Safe-Edge 기준선 복구 여부
- 센서/AI/모니터링 경로 확인
- Longhorn 기준선 확인
- Failover/Failback 실측
- 데이터 공백 분석

상태: 완료

### M1 후 검증

- Hub 핵심 서비스 배치 여부
- 네임스페이스/앱 배치 기준 설명 가능 여부
- Dashboard VPC 외부 관리자 접근 구조 설명 가능 여부
- Dashboard VPC와 Processing VPC 사이에 직접 network peering이 없음을 확인
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
- `system_status`, `device_status`, `workload_status`, `pipeline_heartbeat` 적재 확인
- latest status store 반영 확인

### M5 후 검증

- `factory-b`, `factory-c` Dummy 입력 반영
- 3개 공장 Fleet 인식 여부
- 테스트베드형 자동 롤백 정책 확인

### M6 후 검증

- Risk Score 변화가 관제 화면에 반영되는지 확인
- 상태 카드 / 이상 목록 / 로그 패널 동작 확인
- Dashboard VPC Web/API가 latest status store와 S3 processed를 read-only로 조회하는지 확인
- 일반 상태 변화 10~35초, 장애 판정 40~60초 목표 범위 확인

### M7 후 검증

- 운영형 시나리오
- 테스트베드형 시나리오
- Failover 시나리오
- 롤백 시나리오
- `docs/ops/03_test_checklist.md` 전수 보정

## 테스트 후 보정 대상

- Hub-Spoke 연결 지연
- IoT Core -> S3 적재 지연
- Risk 반영 지연
- Dashboard 반영 지연
- Risk 가중치
- source_type별 지연/누락 수치
- heartbeat miss 장애 판정 기준
- Dummy 시나리오 세부값
- null 허용 정책
- 장기 보존 정책
