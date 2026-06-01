# MVP 범위

상태: source of truth
기준일: 2026-05-29

## 목적

현재 MVP에 포함되는 것과 포함하지 않는 것을 분리한다.

## 현재 상태

- MVP의 첫 기준선인 M0 `factory-a` Safe-Edge 구축과 실측 검증은 완료됐다.
- AWS Hub EKS/ArgoCD, AWS Load Balancer Controller, Admin UI HTTPS Ingress, foundation S3/AMP/IoT Rule, `factory-a/b/c` IoT Thing/Policy/K3s Secret은 현재 build 스크립트와 factory별 등록 스크립트로 재생성/검증 가능하다. Hub는 `build-hub.sh`, Admin UI는 `build-admin-ui-after-ns.sh`, Tailnet UI는 `connect-hub-tailscale-ui.sh`, Spoke 등록은 `register-spoke-factory-a/b/c.sh`, 최종 확인은 `verify-complete.sh`가 담당한다.
- 전체 MVP는 운영형 Spoke 1개와 테스트베드형 Spoke 2개를 포함한 멀티 공장 관제 구조를 목표로 한다.
- 2026-05-29 기준 IoT Core -> Lambda data processor -> DynamoDB LATEST/HISTORY#STATE + S3 processed, DataProcessorRefresh1m -> stale factory `pipeline_status`/`risk` 재계산, GraphAggregator5m -> DynamoDB GRAPH#5M + S3 processed_agg data-pipeline은 `factory-a/b/c` 기준으로 실제 AWS 리소스 검증을 완료했다.
- Lambda data processor의 `risk-v0.2.0` Risk Score 계산은 구현/검증 완료 상태다. runtime-config 기반 weight/threshold/factory override 연결과 Risk Twin read model 고정은 후속 고도화다.
- Bedrock 기반 factory별 일일 운영 보고서 초안 생성은 MVP 포함 범위로 확정했고, 로컬 테스트, Bedrock Sonnet 실호출, AWS reporting stack 배포, `factory-b` Step Functions 수동 실행, S3 산출물 검증까지 완료했다. reporting stack은 비용 방지를 위해 검증 후 삭제했으며 S3 input/output object는 보존한다. 세부 설계 source of truth는 `docs/planning/17_llm_daily_factory_report_plan.md`다.
- Dashboard page와 Dashboard VPC 구현은 별도 담당 범위다. 이 repo에서는 Dashboard가 조회할 DynamoDB/S3 processed/processed_agg read model과 Risk output 계약을 유지한다.

## 2026-05-13 멘토링 반영

### 기존 초안

기존 MVP 초안은 `factory-a/b/c`, EKS Hub, Tailscale, IoT Core -> S3, Risk Score, 메인 대시보드를 중심으로 정의했다. 이 초안에서는 LLM 기반 일일 보고서 자동 생성은 MVP 범위 초과로 분류했다.

### 변경 이유

멘토링에서는 CI/CD와 ArgoCD가 필요한 이유를 더 명확히 설명해야 한다는 피드백이 있었다. 단순 대시보드만으로는 모델/설정 업데이트와 배포 파이프라인의 필요성이 약해질 수 있다.

### 보강 방향

기존 MVP 범위는 유지하되, LLM 보고서를 전체 자동화 기능이 아니라 하루 1회 운영 리포트 초안 생성으로 제한해 포함한다. 이 리포트는 자동 재학습이나 자동 배포가 아니라, Edge AI 판단의 실패/불확실 사례와 모델/설정 업데이트 후보를 찾는 용도다.

추가로 Dashboard 최신 상태는 S3 raw를 직접 조회하는 방식이 아니라, DynamoDB LATEST를 통해 준실시간으로 조회하고 최근 그래프는 DynamoDB GRAPH#5M을 우선 사용한다. 상세 drill-down은 HISTORY#STATE를 사용한다. S3 raw는 원본 보존, 재처리, 감사용으로 유지한다. 일일 운영 보고서의 MVP 입력은 S3 `processed/`이며, Bedrock에는 원본 raw payload를 직접 넣지 않는다.

## 현재 완료 범위

- `factory-a` Safe-Edge 기준선 재구성
- Raspberry Pi 3노드 K3s
- ArgoCD + Helm 기반 GitOps
- GitHub repo `https://github.com/aegis-pi/safe-edge-config-main.git`
- `monitoring`, `ai-apps` namespace 분리
- InfluxDB/Grafana/Prometheus
- Grafana 센서/AI/노드 대시보드
- Longhorn 기반 PVC
- InfluxDB 1일 retention policy
- AI snapshot 24시간 cleanup
- 이미지 prepull DaemonSet
- LAN 제거 및 전원 제거 failover/failback 테스트
- Hub EKS/VPC/namespace/ArgoCD bootstrap
- Foundation S3 bucket
- AMP Workspace
- IoT Rule -> S3 raw 적재
- `factory-a` IoT Thing/certificate/policy 및 K3s Secret
- `factory-b/c` VM K3s 테스트베드, local dummy generator, 공통 publisher, S3 raw 적재 검증
- Lambda data processor, DynamoDB LATEST/HISTORY#STATE, S3 processed, `pipeline_status` 계산 및 `factory-a/b/c` end-to-end 검증
- DataProcessorRefresh1m 기반 stale `pipeline_status`/`risk` 재계산 검증. 2026-05-29 기준 `factory-a` 입력 중단 상태는 `critical/danger/0`으로 표시된다.
- GraphAggregator5m, DynamoDB GRAPH#5M, S3 processed_agg 5분 그래프 집계 검증
- Lambda data processor `risk-v0.2.0` Risk Score 계산
- Daily Factory Report MVP local/AWS manual execution 검증

## MVP 포함 범위

- `factory-a` 운영형 Spoke
- `factory-b`, `factory-c` K3s 테스트베드형 Spoke
- AWS EKS Hub
- Tailscale 기반 Hub-Spoke 연결
- IoT Core -> S3 수집 경로
- Risk Score 기반 `안전 / 주의 / 위험` 표현
- Bedrock 기반 factory별 일일 운영 보고서 초안
  - 매일 00:30 KST 기준 전일 KST 00:00:00~23:59:59 대상
  - `factory-a/b/c`별 개별 Markdown 보고서
  - S3 `processed/` 기반 집계, `report-context.json`, `factory-daily-summary.json`, `report.md`, `generation-metadata.json` 저장
  - 운영자 검토용 초안이며 자동 재학습/자동 배포를 수행하지 않음
- 메인 대시보드 - page/VPC 구현은 별도 담당 범위, 이 repo는 조회 데이터 계약 제공
  - 공장별 위험 상태 카드
  - 센서 현황
  - 이상 시스템 목록
  - 최근 상태 변화 로그

## MVP 제외 범위

- event 기반 점수 반영
- 별도 이벤트 전용 파이프라인
- 공장별 상세 커스텀 정책 활성화
- 완전 자동화된 장애/복구 리허설
- 장기 이력 분석 계층
- Bedrock을 통한 S3 raw 원본 직접 분석
- DOCX/PDF 보고서 생성
- 전체 공장 통합 보고서

## 후속 확장 범위

- event 입력 반영
- 분석 계층
- 공장 수 확대
- 세부 알람 정책
- 운영 자동화 고도화
- 장기 저장소와 리포트 자동화
- DOCX/PDF 보고서 후처리 Lambda
- 전체 공장 요약 보고서

## MVP 완료 판정

MVP는 아래 조건을 만족할 때 완료로 본다.

- `factory-a`, `factory-b`, `factory-c`가 Hub에서 독립 공장으로 식별된다.
- 운영형 `factory-a`는 실제 입력 기반 상태를 보낸다.
- 테스트베드형 `factory-b`, `factory-c`는 Dummy 시나리오 기반 상태를 보낸다.
- Hub 관제에서 공장별 `안전 / 주의 / 위험` 상태가 보인다.
- S3 `processed/` 기반 factory별 일일 보고서 context와 Markdown 초안이 `reports/daily/.../{factory_id}/`에 생성된다.
- 배포, 데이터 수집, 장애 시나리오가 문서와 일치한다.
