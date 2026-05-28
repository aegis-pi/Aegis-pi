# Next Session Prompt

아래 프롬프트를 다음 Codex 세션 시작 시 그대로 사용한다.

```text
작업 디렉터리는 /home/vicbear/Aegis/git_clone/Aegis-pi 입니다.

현재 목표는 Dashboard 담당자가 붙기 쉬운 형태로 Aegis-Pi 데이터/Risk/리포팅 계약을 고도화하는 것입니다. Dashboard page 및 Dashboard VPC 구현은 다른 팀원 담당 범위입니다.

먼저 현재 상태를 확인하세요.

1. git status --short
2. docs/issues/SESSION_STATE.md 확인
3. docs/issues/M6_risk-twin-dashboard.md 확인
4. docs/ops/23_data_pipeline.md 확인
5. docs/ops/24_daily_factory_report.md 확인
6. docs/ops/25_daily_factory_report_cost.md 확인
7. apps/data-processor/ 확인
8. apps/daily-report-generator/ 확인

현재 완료 상태:

- M0~M5 주요 구현과 검증은 완료.
- Lambda data processor는 IoT Core 수신 메시지를 DynamoDB LATEST/HISTORY와 S3 processed에 저장한다.
- 기본 Risk Score 계산은 apps/data-processor/processor/risk.py 에 구현되어 있다.
- 현재 Risk 계산 대상은 temperature, humidity, AI event rate이며 score/level/top_causes를 출력한다.
- configs/runtime/runtime-config.yaml은 존재하지만 data processor risk.py는 아직 하드코딩 상수를 사용한다.
- factory-a/b/c data-pipeline은 S3 raw/processed 및 DynamoDB LATEST 갱신 검증을 완료했다.
- Daily Factory Report는 로컬 검증, Bedrock Sonnet 실호출, infra/reporting 배포, factory-b Step Functions 수동 실행, S3 산출물 검증까지 완료했다.
- 검증 실행: manual-factory-report-20260528T012107Z, SUCCEEDED.
- 검증 output: s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-b/
- reporting stack은 비용 방지를 위해 scripts/destroy/destroy-reporting.sh 로 삭제했다. S3 processed input과 reports/daily output은 보존된다.
- Daily Report 비용 기준은 docs/ops/25_daily_factory_report_cost.md에 정리했다.

다음 작업 우선순위:

1. Risk output 계약을 고정한다.
   - 현재 score/level/top_causes 구조를 확인한다.
   - Dashboard read model로 필요한 필드를 정의한다.
   - Risk Twin 출력 후보: current_status, risk_score, score_delta_10m, top_causes[{code,label,weight,contribution}], event_timestamp, processed_at.

2. runtime-config.yaml을 Lambda Risk 계산에 연결한다.
   - configs/runtime/runtime-config.yaml의 weights/thresholds/risk_enabled/factory override 구조를 확인한다.
   - Lambda package에 포함하거나 배포 시 주입하는 방식을 선택한다.
   - 하드코딩 상수를 config 기반으로 바꾼다.
   - 단위 테스트를 추가/수정한다.

3. Risk Twin 출력 구조를 DynamoDB/S3 processed에 반영한다.
   - DynamoDB LATEST/HISTORY에서 Dashboard가 읽을 필드를 안정화한다.
   - S3 processed risk_score/state_snapshot에 동일 계약을 남긴다.
   - Dashboard 구현은 하지 않는다.

4. Daily Factory Report 고도화 후보를 진행한다.
   - S3ProcessedReader에서 S3_GET_CONCURRENCY를 실제로 사용해 GetObject 병렬화.
   - state_snapshot 전체 읽기 대신 latest N개 또는 hour별 마지막 snapshot만 읽도록 축소.
   - generation-metadata.json에 Bedrock token usage, context bytes, output bytes, input object count 저장.

주의:

- root에서 python -m pytest -q 전체 실행은 기존 data-processor import 경로 문제로 실패할 수 있으니, 우선 변경한 app 범위로 테스트하세요.
- reporting stack은 현재 삭제된 상태입니다. 다시 AWS 실행 검증이 필요할 때만 scripts/build/build-reporting.sh 를 사용하세요.
- destroy는 사용자가 명시적으로 요청한 경우에만 실행하세요.
- Dashboard page/VPC 구현은 별도 담당 범위이므로 이 repo에서는 read model과 계약을 우선하세요.
```
