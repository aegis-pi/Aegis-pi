# 2026-05-27 Daily Factory Report Session

상태: handoff
기준일: 2026-05-27

## 목적

다음 세션에서 Bedrock 기반 daily factory report 작업을 바로 이어가기 위한 저장 문서다. 공식 진행 스냅샷은 `docs/issues/SESSION_STATE.md`를 우선한다.

## 현재 완료

- `apps/daily-report-generator/` package와 4개 Lambda handler 구현을 진행했다.
- `AggregateFactoryHour`는 infra summary에 `not_ready_nodes`, `unhealthy_workloads`를 구조화한다.
- node 이름이 비어 있으면 `control-plane:Unknown`, `worker:Unknown` 같은 fallback label을 사용한다.
- `MergeFactoryDaily`는 AI spike count/examples, likely infra causes, recommended checks를 context에 포함한다.
- `recommended_checks`는 rule 기반으로 priority/reason/evidence message id를 구성한다.
- `PromptBuilder`는 AI spike evidence, infra cause, recommended checks, S3 processed/raw 한계, testbed/dummy 해석을 보고서에 반영한다.
- `infra/reporting/` Terraform root module과 `build-reporting.sh`, `destroy-reporting.sh`를 추가했다.

## 테스트 산출물

- `/home/vicbear/Aegis/test_paper/factory-b-hh03-report-context-enriched-v2.json`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-prompt-enriched-v2.txt`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-hourly-aggregate-enriched-v2.json`
- `/home/vicbear/Aegis/test_paper/factory-b-hh03-enriched-v2-test-note.md`

## 검증 상태

- `python -m pytest -q`: 통과, 9 passed.
- `python -m compileall -q apps/daily-report-generator`: 통과.
- `terraform fmt -check -diff`: 통과.
- `terraform validate`: sandbox provider plugin 실행 제한으로 실패했고, escalated 재시도는 사용량 제한으로 거절되어 재검증하지 못했다.

## 남은 작업

1. `git status --short`로 변경 파일 확인.
2. 로컬 pytest/compileall/fmt 재실행.
3. `terraform validate` 재실행.
4. enriched v2 Bedrock 실호출.
5. 생성 Markdown의 factory/date/Risk Score/collection count/evidence id/recommended checks/S3 processed 한계 검증.
6. 24시간 daily merge 기준 `missing_hour_count=0`, count 합산, hour boundary event merge 검증.
7. `scripts/build/build-reporting.sh`로 AWS reporting stack 배포.
8. Step Functions 수동 실행.
9. S3 `reports/daily/.../{factory_id}/` 산출물 확인.
10. 이후 M6 Risk 계산, `runtime-config.yaml`, Risk Twin 출력 구조 구현 진행.

## 주의

- `factory-b` `hh=03` enriched v2 context는 단일 hour 테스트라 `missing_hour_count=23`이 정상이다.
- 24시간 daily merge에서는 `missing_hour_count=0`이어야 한다.
- Bedrock 실호출과 AWS 배포는 아직 하지 않았다.
