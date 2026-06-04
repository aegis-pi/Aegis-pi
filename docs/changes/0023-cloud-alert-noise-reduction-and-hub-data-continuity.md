# Change 0023 - Cloud alert noise reduction and Hub-only data collection continuity

상태: accepted
결정일: 2026-06-04

## 기존 계획

- Cloud infra section이 non-normal이면 generic section alert와 specific 원인 alert를 함께 생성했다.
- Cloud fast snapshot의 factory freshness를 Cloud `overall_status`와 Cloud Slack alert에 포함했다.
- ALB Target Group은 설정된 이름으로 조회했고, `draining` target도 unhealthy로 계산될 수 있었다.
- pipeline freshness는 warning 40초 초과, critical 60초 초과 기준이었다.
- Hub-only rebuild 전후에도 dummy generator와 data-pipeline을 중단하거나 다시 시작하는 절차가 남아 있었다.

## 변경된 실제 기준

- Cloud alert는 specific 원인을 우선하고 같은 section의 generic alert는 fallback으로만 사용한다.
- 일부 Cloud warning은 서로 다른 최신 snapshot 2회 연속 관측 후 Slack으로 전송한다.
- Factory freshness는 Cloud snapshot 참고 데이터에는 유지하지만 Cloud `overall_status`와 Cloud Slack alert에서는 제외한다.
- Factory 비-pipeline alert fingerprint는 pipeline 상태와 무관한 `{severity}#{reason}#state_snapshot`을 사용한다.
- FastCollector는 ECS service의 `loadBalancers[].targetGroupArn`을 우선 사용하고, ALB target state를 healthy/unhealthy/draining/initial/unused/unknown으로 분리한다.
- Failed Pod 1개는 warning, 2개 이상은 critical로 판정한다.
- pipeline freshness는 normal 60초 이하, warning 60초 초과, critical 120초 초과 기준을 사용한다.
- Hub-only 데이터 수집 유지 모드에서는 dummy generator, Spoke publisher, data-pipeline과 ECS backend를 유지한다. `build-hub.sh`가 새 Hub EKS 생성 후 SlowCollector access binding을 자동 복구한다.

## 변경 이유

- rolling deployment와 일시적인 collector/pipeline 지연을 실제 장애로 오판하는 Slack 알림을 줄인다.
- 같은 장애 원인에 대한 generic/specific 중복 알림을 제거한다.
- Target Group 이름 drift와 ECS 배포 중 `draining` 상태로 인한 ALB 오탐을 방지한다.
- Hub 비용 절감 삭제 중에도 factory 데이터 수집과 cloud-side 처리를 지속한다.
- Hub 재생성 후 SlowCollector가 새 EKS Kubernetes API를 읽을 수 있도록 access entry를 자동 복구한다.

## 영향

- DynamoDB `ALERT#cloud-infra`에 `OBSERVATION#{severity}#{reason}#{status}` 확인 item이 추가된다.
- Cloud `overall_status`는 `backend_runtime`, `data_pipeline`, `eks_management`, `storage_freshness`만 반영한다.
- Dummy generator freshness gap과 Dashboard/API 요구사항이 60초/120초 기준으로 변경된다.
- Change 0020의 Hub-only 운영 순서는 데이터 수집 유지 모드에 대해 이 변경 기록의 절차로 대체된다.

## 업데이트 문서

- 상위 README와 `apps/`, `infra/`, `scripts/` 하위 README
- `docs/architecture/`, `docs/product/`, `docs/planning/`, `docs/specs/`
- `docs/ops/` Hub, data-pipeline, DynamoDB, dummy generator, Cloud collector, alert dispatcher 문서
- `docs/issues/SESSION_STATE.md`, 데모/발표/트러블슈팅 문서

## 검증

- 오래된 freshness 기준, 기존 factory alert key, 과거 Hub-only 중단 절차 문구 재검색 결과 없음.
- `git diff --check` 통과.
- `bash -n scripts/build/build-hub.sh scripts/build/reconcile-data-pipe-eks-access.sh` 통과.
