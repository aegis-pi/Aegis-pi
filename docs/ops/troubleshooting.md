# 트러블슈팅

상태: draft
기준일: 2026-04-24

## 목적

프로젝트 구성, 배포, 데이터 수집, Risk Twin 반영 과정에서 자주 만날 문제를 빠르게 분류하고 우선 확인 순서를 제시한다.

## 현재 상태

- 현재 문서는 대표 장애 유형과 1차 확인 방향을 담은 운영 초안이다.
- 실제 운영 사례가 쌓이면 증상별 해결 기록을 추가한다.

## 범위

- Safe-Edge 기준선 문제
- 배포 문제
- 네트워크 문제
- 데이터 플레인 문제
- Risk Twin 문제
- 테스트베드형 Spoke 문제

## 상세 내용

## 사용 원칙

1. 먼저 장애가 어느 축인지 분류한다.
   - Safe-Edge 기준선
   - Hub/배포
   - Mesh VPN
   - 데이터 플레인
   - Risk Twin
2. `self_check.md`에서 실패한 항목을 확인한다.
3. 이 문서에서 같은 증상을 찾고 우선 확인 순서대로 본다.

## 1. `factory-a` Safe-Edge 기준선이 정상적으로 올라오지 않음

증상:
- Raspberry Pi 노드가 모두 Ready가 아님
- Longhorn 복제가 비정상
- 센서 입력이 전혀 보이지 않음

가능 원인:
- K3s 3노드 구성 실패
- 노드 역할/라벨 설정 오류
- 스토리지 계층 미구성
- 입력 모듈 또는 Edge Agent 미기동

우선 확인:
- `kubectl get nodes`
- Longhorn 상태
- 센서/입력 모듈 프로세스 상태
- 기본 모니터링 입력 여부

다음 조치:
- `docs/ops/safe_edge_bootstrap.md` 기준으로 단계 역추적
- Safe-Edge 기준선이 안정화되기 전까지 Hub 확장은 보류

## 2. ArgoCD 동기화가 실패함

증상:
- Application이 `OutOfSync` 또는 `Degraded`
- Spoke 배포가 반영되지 않음

가능 원인:
- Git 리포지토리 경로 오류
- values 경로 오류
- 대상 클러스터 연결 문제

우선 확인:
- ArgoCD Application 상태 확인
- 대상 Spoke kubeconfig 확인
- Tailscale 경로 확인
- ApplicationSet이 공장별 values를 올바르게 읽는지 확인

다음 조치:
- values 기반 자동 생성 구조를 먼저 확인
- 운영형/테스트베드형 sync 정책 차이를 확인

## 3. Tailscale로 Spoke 접근이 안 됨

증상:
- Hub에서 Spoke Master API 접근 실패
- ArgoCD 대상 클러스터 연결 실패

가능 원인:
- Spoke별 키/인증 문제
- Master 미참여
- 주소 정책 혼선

우선 확인:
- Tailscale IP 확인
- Master 참여 여부 확인
- kubeconfig server 주소 확인
- 운영형/테스트베드형 접근 정책 차이 확인

다음 조치:
- 기본은 Master 중심 접근 원칙으로 되돌린다
- 예외 접근은 장애 분석/운영 복구 시에만 수동 허용한다

## 4. IoT Core에는 보낸 것 같은데 S3에 데이터가 없음

증상:
- Edge Agent 송신 로그는 있는데 Hub에서 데이터가 안 보임
- `pipeline_status`가 비정상으로 남음

가능 원인:
- Rule Engine 설정 문제
- 권한 문제
- 메시지 형식 문제

우선 확인:
- IoT Core 수신 로그 확인
- S3 대상 경로 확인
- payload 필수 필드 누락 여부 확인
- 날짜 파티셔닝 경로가 의도대로 생성되는지 확인

다음 조치:
- source_type별 필수 필드 확인
- S3 적재 전 단계와 후단계를 분리해서 본다

## 5. `pipeline_status`가 잘못 계산됨

증상:
- 실제 적재는 됐는데 비정상으로 표시됨
- 반대로 적재가 끊겼는데 정상처럼 보임

가능 원인:
- 집계 주기 문제
- source_type별 지연 기준 미정 또는 오적용
- `pipeline-status-aggregator` 문제

우선 확인:
- Hub 집계 주기 설정
- 마지막 수신/적재 시각
- source_type 분류 값

다음 조치:
- 현재는 주기 집계형 기준이므로 즉시 반영을 기대하지 않는다
- 수치 기준은 테스트 보정 항목으로 분리한다

## 6. Risk 상태가 갱신되지 않음

증상:
- 센서/상태 입력은 있는데 카드 상태가 그대로임
- 주요 원인 Top 3가 비어 있음

가능 원인:
- 정규화/판단 서비스 문제
- Risk Score Engine 호출 실패
- `pipeline_status` 또는 source_type 분류 오류

우선 확인:
- S3 적재 이후 처리 로그 확인
- 정규화 결과 확인
- Risk 결과 저장/조회 경로 확인
- 주요 원인 코드 매핑 확인

다음 조치:
- 상태 전환만 볼지, 원인 필드까지 실패했는지 분리해서 본다
- 이벤트 코드는 현재 예약 상태이므로 미사용이 정상일 수 있다

## 7. 카메라/마이크 상태가 비정상으로 표시됨

증상:
- 장치가 붙어 있는데 비정상으로 표시됨
- 실제 입력 유무와 관계없이 상태가 고정됨

가능 원인:
- 장치 연결 문제
- 관련 프로세스 비정상

우선 확인:
- 프로세스 생존 여부 확인
- 장치 연결 상태 확인

다음 조치:
- 현재 MVP는 프로세스 기준형이므로, 실제 입력 유무는 데이터 플레인 쪽과 분리해서 해석한다

## 8. `factory-b`, `factory-c` 테스트베드형 Spoke가 의도대로 동작하지 않음

증상:
- Dummy 시나리오 전환이 반영되지 않음
- 두 VM이 독립 공장으로 식별되지 않음

가능 원인:
- Dummy 입력 모듈 비정상
- values 오적용
- `factory-b` / `factory-c` 식별 정보 충돌

우선 확인:
- `factory_id`
- `environment_type`
- `input_module_type`
- Dummy 제어 입력 상태

다음 조치:
- 운영형 Spoke와 혼동하지 않도록 values를 먼저 검토한다
- Dummy 시나리오 세부값은 테스트 기반 보정 항목으로 본다

## TODO

- TODO: 실제 장애 사례가 생기면 항목 추가
- TODO: 항목별 실제 명령어 또는 대시보드 경로 추가
