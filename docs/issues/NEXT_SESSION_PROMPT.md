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
7. docs/ops/27_dummy_data_generation_and_risk_scenarios.md 확인
8. docs/ops/29_cloud_infra_metrics_pipeline_plan.md 확인
9. docs/ops/31_risk_alert_dispatcher.md 확인
10. apps/data-processor/ 확인
11. apps/cloud-infra-collector/ 확인
12. apps/risk-alert-dispatcher/ 확인
13. apps/daily-report-generator/ 확인

현재 완료 상태:

- M0~M5 주요 구현과 검증은 완료.
- Lambda data processor는 IoT Core 수신 메시지를 DynamoDB LATEST/HISTORY#STATE와 S3 processed에 저장한다.
- DataProcessor freshness refresh가 배포됐다. `AEGIS-Schedule-DataProcessorRefresh1m`가 1분마다 `AEGIS-Lambda-DataProcessor`를 `action=refresh_pipeline_status`로 호출해 새 메시지가 없는 factory의 `pipeline_status`와 `risk`를 재계산한다.
- `risk-v0.2.0` Risk Score 계산은 apps/data-processor/processor/risk.py 에 구현되어 있다.
- 현재 Risk 계산 대상은 temperature, humidity, pressure, AI event rate, node_status, pod_health, device_availability, data_freshness, storage_pressure, network_reachability이며 score/base_score/level/base_level/top_causes/gates를 출력한다.
- configs/runtime/runtime-config.yaml은 존재하지만 data processor risk.py는 아직 하드코딩 상수를 사용한다.
- factory-a/b/c data-pipeline은 S3 raw/processed 및 DynamoDB LATEST 갱신 검증을 완료했다.
- CloudInfraFastCollector1m/SlowCollector5m은 DynamoDB `CLOUD#infra/LATEST`, S3 `processed/cloud_infra/{fast,slow}/` snapshot 저장까지 완료했다.
- CloudInfraSlowCollector는 EKS access entry(`AmazonEKSAdminViewPolicy`, cluster scope)를 통해 Kubernetes API node/pod/ArgoCD read를 수행한다. 2026-06-02 기준 이전 401 Unauthorized 문제는 해결됐다.
- RiskAlertDispatcher는 S3 `processed/{factory}/state_snapshot/`, `processed/cloud_infra/{fast,slow}/` ObjectCreated 이벤트를 받아 warning/danger 조건을 판단하고 DynamoDB `ALERT#{scope}` cooldown/dedupe 후 Slack으로 알림을 보낸다.
- Slack webhook은 cloud/factory-a/factory-b/factory-c 별도 Secrets Manager secret으로 라우팅한다. URL 값은 repo나 로그에 출력하지 않는다. 이전 세션에서 webhook이 채팅에 노출된 이력이 있으므로 운영 전 rotate를 권장한다.
- 2026-05-29 점검 결과 `factory-a`는 2026-05-28T07:54Z 이후 IoT 입력이 중단된 상태였다. stale LATEST 100점 문제는 refresh 배포로 해결되어 `pipeline_status=critical`, `risk.score=0`, `risk.level=danger`로 갱신됐다. 다음 세션에서는 먼저 최신 raw/processed timestamp를 재확인한 뒤 factory-a data-plane Pod/Secret/outbox/publisher 복구 여부를 확인한다.
- Daily Factory Report는 로컬 검증, Bedrock Sonnet 실호출, infra/reporting 배포, factory-b Step Functions 수동 실행, S3 산출물 검증까지 완료했다.
- 검증 실행: manual-factory-report-20260528T012107Z, SUCCEEDED.
- 검증 output: s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-b/
- reporting stack은 비용 방지를 위해 scripts/destroy/destroy-reporting.sh 로 삭제했다. S3 processed input과 reports/daily output은 보존된다.
- Daily Report 비용 기준은 docs/ops/25_daily_factory_report_cost.md에 정리했다.

다음 작업 우선순위:

1. factory-a data-plane 입력 중단 원인을 복구한다.
   - 먼저 DynamoDB LATEST와 S3 raw/processed 최신 timestamp를 재확인한다.
   - `factory-a` K3s에서 `aegis-spoke-edge-iot-publisher`와 `aegis-spoke-factory-a-log-adapter` 상태 확인.
   - outbox PVC/권한/파일 backlog 확인.
   - IoT Secret, ECR pull secret, pod logs 확인.
   - S3 raw/factory-a 최신 timestamp가 현재로 전진하는지 확인.

2. Risk output 계약을 고정한다.
   - 현재 score/level/top_causes 구조를 확인한다.
   - base_score/base_level/gates도 Dashboard read model에 포함할지 결정한다.
   - Dashboard read model로 필요한 필드를 정의한다.
   - Risk Twin 출력 후보: current_status, risk_score, score_delta_10m, top_causes[{code,label,weight,contribution}], event_timestamp, processed_at.

3. runtime-config.yaml을 Lambda Risk 계산에 연결한다.
   - configs/runtime/runtime-config.yaml의 weights/thresholds/risk_enabled/factory override 구조를 확인한다.
   - Lambda package에 포함하거나 배포 시 주입하는 방식을 선택한다.
   - 하드코딩 상수를 config 기반으로 바꾼다.
   - 단위 테스트를 추가/수정한다.

4. Risk Twin 출력 구조를 DynamoDB/S3 processed에 반영한다.
   - DynamoDB LATEST/HISTORY#STATE에서 Dashboard가 읽을 필드를 안정화한다.
   - S3 processed risk_score/state_snapshot에 동일 계약을 남긴다.
   - Dashboard 구현은 하지 않는다.

5. RiskAlertDispatcher 운영 품질을 보강한다.
   - Slack webhook rotate 여부를 사용자에게 확인한다.
   - alert `reason` label을 한글 운영 문구로 매핑할지 결정한다.
   - cloud/factory별 webhook routing과 cooldown 정책을 유지한다.
   - 실제 Slack test alert는 사용자 확인 후에만 보낸다.

6. Daily Factory Report 고도화 후보를 진행한다.
   - S3ProcessedReader에서 S3_GET_CONCURRENCY를 실제로 사용해 GetObject 병렬화.
   - state_snapshot 전체 읽기 대신 latest N개 또는 hour별 마지막 snapshot만 읽도록 축소.
   - generation-metadata.json에 Bedrock token usage, context bytes, output bytes, input object count 저장.

주의:

- root에서 python -m pytest -q 전체 실행은 기존 data-processor import 경로 문제로 실패할 수 있으니, 우선 변경한 app 범위로 테스트하세요.
- reporting stack은 현재 삭제된 상태입니다. 다시 AWS 실행 검증이 필요할 때만 scripts/build/build-reporting.sh 를 사용하세요.
- destroy는 사용자가 명시적으로 요청한 경우에만 실행하세요.
- Dashboard page/VPC 구현은 별도 담당 범위이므로 이 repo에서는 read model과 계약을 우선하세요.
- Slack webhook URL, secret value, local `.secrets/` 파일 내용은 절대 출력하지 마세요.
```
