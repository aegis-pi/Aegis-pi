# Session State

상태: working tracker
기준일: 2026-05-29

## 목적

이 파일은 현재 작업 세션의 이어받기용 기록이다. `docs/issues/MASTER_CHECKLIST.md`와 각 M0~M7 이슈 문서가 공식 진행 기준이고, 이 파일은 지금까지 한 일과 다음에 할 일을 빠르게 복구하기 위한 보조 문서다.

이 파일은 누적 로그가 아니라 현재 상태 스냅샷으로 관리한다. 사용자가 "문서 최신화" 또는 "세션 저장"을 요청하면 아래 섹션을 덧붙이는 방식이 아니라 현재 기준으로 갱신한다.

## 마일스톤 기준 진행 현황

| 마일스톤 | 이슈 | 상태 | 기준 문서 |
| --- | --- | --- | --- |
| M0 | Issue 1 - Safe-Edge/OS | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 2 - Safe-Edge/네트워크 | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 3 - Safe-Edge/K3s | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 4 - Safe-Edge/MetalLB | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 5 - Safe-Edge/Longhorn | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 6 - Safe-Edge/NFS | 보류 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 7 - 배포/ArgoCD | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 8 - 관제/Grafana | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 9 - 데이터/BME280 | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 10 - Safe-Edge/AI | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 11 - Safe-Edge/Failover | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 12 - 자동화/Ansible | 부분 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M0 | Issue 13 - 검증/통합 | 완료 | `docs/issues/M0_factory-a_safe-edge-baseline.md` |
| M1 | Issue 0 - AWS/Auth | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 1 - Hub/EKS | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 2 - Hub/Kubernetes | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 3 - Hub/ArgoCD | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 4 - Hub/S3 | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 5 - Hub/IoT Core | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 6 - 관제/AMP | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 7 - 관제/Prometheus | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 8 - 관제/Grafana | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 9 - Hub/Ingress | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 10 - Hub/Admin UI | 완료 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 11 - Hub/Admin UI 보안 강화 | 보류 | `docs/issues/M1_hub-cloud.md` |
| M1 | Issue 12 - Risk/Config | 완료 | `docs/issues/M1_hub-cloud.md` |
| M2 | Issue 1 - Mesh/Tailscale 정책 | 완료 | `docs/issues/M2_mesh-vpn-hub-spoke.md` |
| M2 | Issue 2 - factory-a Master Tailscale 참여 | 완료 | `docs/issues/M2_mesh-vpn-hub-spoke.md` |
| M2 | Issue 3 - EKS Hub Tailscale 참여 | 완료 | `docs/issues/M2_mesh-vpn-hub-spoke.md` |
| M2 | Issue 4 - kubeconfig Tailscale IP 기반 구성 | 완료 | `docs/issues/M2_mesh-vpn-hub-spoke.md` |
| M2 | Issue 5 - ArgoCD factory-a cluster 등록 | 완료 | `docs/issues/M2_mesh-vpn-hub-spoke.md` |
| M2 | Issue 6 - Hub -> factory-a Sync 확인 | 완료 | `docs/issues/M2_mesh-vpn-hub-spoke.md` |
| M3 | Issue 1 - 배포/Helm GitOps 저장소 구조 | 완료 | `docs/issues/M3_deploy-pipeline.md` |
| M3 | Issue 2 - 배포/ECR 저장소 구성 및 이미지 태그 전략 | 완료 | `docs/issues/M3_deploy-pipeline.md` |
| M3 | Issue 3 - 배포/GitHub Actions 빌드/푸시 워크플로우 | 완료 | `docs/issues/M3_deploy-pipeline.md` |
| M3 | Issue 4 - 배포/ArgoCD ApplicationSet 구성 | 완료 | `docs/issues/M3_deploy-pipeline.md` |
| M3 | Issue 5 - 배포/ArgoCD 운영형 동기화 정책 및 롤백 정책 | 완료 | `docs/issues/M3_deploy-pipeline.md` |
| M3 | Issue 7 - 배포 검증 워크플로우 | 완료 | `scripts/build/verify-complete.sh` |
| M3 | Issue 8 - factory-a end-to-end 배포 검증 | 완료 | `docs/issues/M3_deploy-pipeline.md` |
| M4 | Issue 1 - Raw/Processed 데이터 계약 확정 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 2 - factory-a-log-adapter 구현 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 3 - edge-iot-publisher 구현 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 4 - 이미지화 및 K3s 배포 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 5 - IoT Core -> S3 적재 확인 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 6 - IoT Core Lambda data processor 구현 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 7 - pipeline_status Lambda 처리 검증 | 완료 | `docs/issues/M4_data-plane.md` |
| M4 | Issue 8 - factory-a 데이터 플레인 end-to-end 검증 | 완료 | `scripts/build/verify-complete.sh` |
| M5 | Issue 1 - VM K3s 2-node 기준선 | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M5 | Issue 2 - factory-b/c Tailnet 참여 | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M5 | Issue 3 - Hub ArgoCD cluster 등록 | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M5 | Issue 4 - ApplicationSet factory-b/c 확장 | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M5 | Issue 5 - 로컬 Dummy generator 구현 및 실행 | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M5 | Issue 6 - 테스트베드 동기화 및 롤백 정책 | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M5 | Issue 7 - 데이터 플레인 연결 확인 (S3 적재) | 완료 | `docs/issues/M5_vm-spoke-expansion.md` |
| M6 | Issue 1 - Lambda Risk 계산 로직 | 완료 | `docs/issues/M6_risk-twin-dashboard.md` |
| Daily Report | Reporting stack 로컬/AWS 수동 실행 검증 | 완료 | `docs/ops/24_daily_factory_report.md` |

현재 바로 이어서 할 이슈/작업:

```text
M6 Issue 2~4 - runtime-config 적용, 온도/습도 기준값 계산 연결, Risk Twin 출력 구조 구현
Daily Factory Report 고도화 - S3 read 병렬화/state_snapshot 축소, generation metadata 비용 관측 필드 추가, CloudWatch 기반 reporting pipeline health 보조 조회
Dashboard page 및 Dashboard VPC - 별도 담당 범위. 이 repo는 DynamoDB/S3 processed read model과 Risk 계약을 제공
factory-a 운영 복구 - 2026-05-28T07:54Z 이후 factory-a IoT 입력이 중단된 상태다. data-plane Pod/Secret/outbox/publisher 재확인이 필요하다.
```

## 다음 세션 시작 지점

바로 이어서 작업할 때는 새 인프라 작업을 시작하기 전에 아래 순서로 현재 상태를 확인한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
git status --short
```

Hub가 내려가 있는 개발 중단 상태라면 아래 순서로 복구한다. IoT Core Thing/certificate와 Spoke K3s Secret은 유지한다.

```bash
scripts/build/build-hub.sh <MFA_OTP>
scripts/build/build-admin-ui-after-ns.sh <MFA_OTP>        # Public HTTPS Admin UI가 필요할 때
scripts/build/connect-hub-tailscale-ui.sh <MFA_OTP>       # Tailnet ArgoCD/Grafana UI가 필요할 때만 선택 실행
scripts/build/register-spoke-factory-a.sh <MFA_OTP>
scripts/build/register-spoke-factory-b.sh <MFA_OTP>
scripts/build/register-spoke-factory-c.sh <MFA_OTP>
```

Hub를 다시 내릴 때는 VM 데이터 생성을 먼저 멈춘다.

```bash
scripts/destroy/stop-dummy-generators.sh
scripts/destroy/destroy-hub.sh <MFA_OTP>
```

Hub 상태와 무관하게 다음 구현 작업은 M6 Risk 데이터 계약 고도화와 Daily Factory Report 성능/관측성 개선이다. Daily report는 `apps/daily-report-generator/`와 `infra/reporting/` 로컬 구현, Bedrock Sonnet 실호출, 24시간 `factory-b` Step Functions 수동 실행, S3 산출물 검증까지 완료했다. 2026-05-28 최종 검증에서는 `manual-factory-report-20260528T064840Z`가 `SUCCEEDED`였고, `report.md`의 핵심 지표/데이터 수집/Risk Score/센서 및 AI 이벤트/인프라 상태/주요 이벤트/확인 필요 항목 표와 분석 문단을 확인했다. 검증 후 reporting stack은 `destroy-reporting.sh`로 삭제했고 S3 `processed/` 입력과 `reports/daily/` 출력은 보존한다.

2026-05-29에는 DataProcessor freshness refresh를 배포했다. `AEGIS-Schedule-DataProcessorRefresh1m`가 `AEGIS-Lambda-DataProcessor`를 1분마다 `action=refresh_pipeline_status`로 호출한다. 이 경로는 새 IoT 메시지가 없는 factory도 DynamoDB LATEST의 `pipeline_status`와 `risk`를 현재 시각 기준으로 재계산하고, HISTORY#STATE와 S3 `state_snapshot`을 남긴다.

## 2026-05-27 Hub Cost Optimization 상태

결정:

- AMP는 사용자가 EKS 상태 확인에 직접 사용하지 않으므로 active 구성에서 제거한다.
- Hub NAT Gateway는 조건 없이 1개만 유지한다.
- 단일 NAT는 `ap-south-1a`의 `AEGIS-NAT-public-Azone`을 보존하고, A/C private route table이 모두 이를 사용한다.
- 데이터 수집/처리 경로는 IoT Core -> Lambda data processor -> DynamoDB/S3 processed이며, Hub EKS의 AMP/Prometheus/Grafana 변경과 직접 연결되지 않는다.

반영한 코드:

```text
infra/foundation/amp.tf 삭제
infra/foundation/outputs.tf AMP output 제거
infra/hub/irsa_prometheus_remote_write.tf 삭제
infra/hub/irsa_grafana_amp_query.tf 삭제
infra/hub/main.tf 단일 NAT Gateway 구성
infra/hub/moved.tf Azone NAT/EIP state move 추가
scripts/ansible/playbooks/hub_prometheus_agent_cleanup.yml 추가
scripts/ansible/templates/prometheus-agent.yaml.j2 삭제
scripts/ansible/templates/grafana-values.yaml.j2 AMP datasource 제거
scripts/build/build-hub-platform.sh legacy Prometheus Agent cleanup 호출
configs/runtime/runtime-config.yaml AMP 설정 제거
```

적용/검증 결과:

```text
foundation apply: AMP workspace ws-60897fc1-019b-417e-acb7-60fbcad61a2b destroy 완료
hub apply: Azone NAT/EIP preserve, Czone NAT nat-0c31e93d9cdf730f1/EIP destroy 완료
hub apply: Czone private route -> Azone NAT nat-0db2f6d136046bcb8 변경 완료
hub apply: Grafana AMP query IRSA, Prometheus remote_write IRSA 삭제 완료
terraform plan: infra/foundation, infra/hub 모두 No changes
AWS AMP: AEGIS-AMP-hub list-workspaces 결과 빈 배열
AWS NAT: AEGIS-NAT-public-Azone nat-0db2f6d136046bcb8 available, Czone NAT deleted
Hub EKS: observability/prometheus-agent Deployment/Service/ConfigMap/ServiceAccount, ClusterRole/ClusterRoleBinding cleanup 완료
Grafana: Helm 재적용 완료, availableReplicas=1, Service=ClusterIP, /api/health database ok
```

데이터 수집/처리 영향:

```text
IoT Core, Lambda data processor, DynamoDB, S3 raw/processed는 Hub EKS 변경과 독립이다.
Hub apply 중 ArgoCD/Grafana/EKS 내부 UI와 EKS private subnet egress는 일시 영향 가능성이 있다.
factory-a/b/c publisher와 IoT Rule/Lambda 경로는 Hub EKS가 잠시 불안정해도 계속 동작하는 구조다.
단일 NAT는 비용을 줄이는 대신 NAT AZ 장애 시 두 private subnet의 외부 egress가 함께 영향을 받는다.
```

실제 확인:

```text
DynamoDB AEGIS-DynamoDB-FactoryStatus LATEST (2026-05-29 refresh 검증 후):
- factory-a updated_at 2026-05-29T06:48:45.209Z, pipeline_status critical, risk danger, score 0
- factory-b updated_at 2026-05-29T06:49:02.806Z, pipeline_status normal, risk safe, score 100
- factory-c updated_at 2026-05-29T06:49:01.949Z, pipeline_status normal, risk safe, score 100

S3 raw:
- factory-a raw latest는 2026-05-28T07:54Z에서 중단
- factory-b/c raw object는 2026-05-29 현재 지속 적재

S3 processed:
- factory-a processed/state_snapshot 2026-05-29T06:48:45.209Z 신규 생성 확인
- factory-b/c processed/state_snapshot 지속 갱신

Lambda:
- AEGIS-Lambda-DataProcessor State=Active, LastUpdateStatus=Successful, Runtime=python3.12
- AEGIS-Schedule-DataProcessorRefresh1m ENABLED, CloudWatch pipeline refresh 로그 반복 확인
```

## 현재 큰 상태

```text
현재 단계: M6 Risk 데이터 계약 고도화 및 MVP Daily Factory Report 검증 완료, DataProcessor freshness refresh 배포 완료 상태 (2026-05-29)

완료: M3 Issue 1~5 배포 파이프라인 전체
완료: M4 Issue 1~5/8 raw 데이터 플레인
  - factory-a-log-adapter: factory_state 3s, infra_state 20s 주기 outbox write (--loop)
  - edge-iot-publisher: outbox scan -> MQTT -> IoT Core -> S3 raw
  - 배포 이미지: sha-f71a104 (stable, ECR 유지 중)
  - S3 확인: raw/factory-a/factory_state/, raw/factory-a/infra_state/ 실적재 확인
  - canonical JSON 필수 필드 모두 채워짐 (published_at, data_plane_instance_id 포함)
  - Hub ArgoCD ApplicationSet: aegis-spoke-factory-a -> factory-a/ai-apps Synced/Healthy 확인

완료: M4 Issue 6~7 Lambda data processor / pipeline_status 검증
  - Lambda: AEGIS-Lambda-DataProcessor Active, LastUpdateStatus Successful, python3.12, 512MB, timeout 60s
  - DataProcessor refresh Scheduler: AEGIS-Schedule-DataProcessorRefresh1m ENABLED, rate(1 minute)
  - Scheduler payload: {"action":"refresh_pipeline_status","factories":["factory-a","factory-b","factory-c"]}
  - IoT Rules: AEGIS_IoTRule_factory_a/b/c_raw_s3 모두 disabled=false, Lambda action + S3 raw action 연결 확인
  - S3: aegis-bucket-data raw/factory-a,b,c 및 processed/factory-a,b,c/state_snapshot 적재 확인
  - DynamoDB: AEGIS-DynamoDB-FactoryStatus factory-a/b/c LATEST 갱신 확인
  - pipeline_status: factory-b/c normal, factory-a는 입력 중단으로 critical 확인
  - risk: factory-b/c safe, factory-a는 입력 중단으로 danger(score 0) 확인
  - DynamoDB TTL: ttl ENABLED, HISTORY#STATE/GRAPH#5M 보존은 Terraform/Lambda TTL 변수 기준
  - S3 bucket 설정: ap-south-1, versioning enabled, SSE-S3 AES256, public access block 전체 true, BucketOwnerEnforced, raw/processed lifecycle 적용

완료: M6 Issue 1 Lambda Risk 계산 로직 구현
  - apps/data-processor/processor/risk.py 에 score/level/top_causes 계산 구현
  - 현재 계산 대상: temperature, humidity, pressure, AI event rate, node_status, pod_health, device_availability, data_freshness, storage_pressure, network_reachability
  - 위험도 구간: safe >= 85, warning >= 50, danger < 50
  - gate: nodes_all_not_ready는 score 0 cap, danger gate는 score 49 cap, warning gate는 score 84 cap
  - 2026-05-29 검증: factory-a stale LATEST가 refresh 후 pipeline_status critical, risk.score 0, risk.level danger로 갱신됨
  - 단위 테스트: apps/data-processor/tests/test_risk.py
  - 남은 보강: runtime-config.yaml 적용, risk_enabled/override 반영, Risk Twin 공식 출력 구조

완료: MVP Daily Factory Report AWS 수동 실행 검증
  - python -m compileall -q apps/daily-report-generator 통과
  - python -m pytest -q apps/daily-report-generator 통과 (11 passed)
  - terraform -chdir=infra/reporting fmt/init/validate 통과
  - scripts/build/build-reporting.sh 로 reporting stack apply 완료 (17 added)
  - 최종 Step Functions manual execution: manual-factory-report-20260528T064840Z, SUCCEEDED
  - 검증 input: report_date=2026-05-27, timezone=Asia/Seoul, factories=["factory-b"], report_type=daily_factory_operations_draft
  - S3 output: s3://aegis-bucket-data/reports/daily/yyyy=2026/mm=05/dd=27/factory-b/
  - hourly hh=00~23, factory-daily-summary.json, report-context.json, report.md, generation-metadata.json 확인
  - report_window: KST 2026-05-27T00:00:00+09:00~23:59:59+09:00, UTC 2026-05-26T15:00:00Z~2026-05-27T14:59:59Z 확인
  - generation-metadata model_id: anthropic.claude-3-sonnet-20240229-v1:0 확인
  - report.md는 S3 processed 기반/raw 미사용/testbed dummy 해석/검증 기준 수치 섹션 포함 확인
  - report.md에 핵심 지표/데이터 수집/Risk Score/센서 및 AI 이벤트/인프라 상태/주요 이벤트/확인 필요 항목 표와 분석 문단 포함 확인
  - Bedrock 출력 heading trailing space 때문에 섹션 표 삽입이 누락될 수 있는 케이스 수정: `generate_report.py` heading match 공백 허용, `test_generate_report.py` 회귀 테스트 추가
  - CloudWatch Logs/metrics 기반 reporting pipeline health 보조 조회를 후속 확장 방향으로 문서화
  - 비용 기준: docs/ops/25_daily_factory_report_cost.md 추가
  - 검증 후 scripts/destroy/destroy-reporting.sh 로 reporting stack destroy 완료 (17 destroyed), reporting Lambda/Step Functions/Scheduler/IAM/LogGroup 삭제 확인, S3 input/output object 보존 확인

버그 수정 이력 (2026-05-18 세션):
  - fix 1: factory-a-log-adapter CMD --once -> --loop (CrashLoopBackOff)
  - fix 2: edge-iot-publisher endpoint Secret trailing newline strip (DNS 조회 실패)
  - fix 3: PVC fsGroup: 10001 pod securityContext 추가 (outbox 디렉토리 권한)
  - fix 4: factory-a-log-adapter outbox 파일 chmod 0o640 (NamedTemporaryFile 기본 600 -> cross-user 읽기 불가)

현재 배포 방식:
  - build-hub.sh: Hub EKS/ArgoCD/legacy Prometheus Agent cleanup/Grafana/AWS Load Balancer Controller 등록
  - build-admin-ui-after-ns.sh: Admin UI HTTPS Ingress 활성화
  - connect-hub-tailscale-ui.sh: ArgoCD/Grafana Tailscale UI Service 연결/검증
  - register-spoke-factory-a.sh: 기존 IoT Secret 유지, factory-a egress/cluster Secret/ApplicationSet/app sync 복구
  - register-spoke-factory-b.sh: 기존 IoT Secret 유지, factory-b egress/cluster Secret/ApplicationSet/app sync 복구
  - register-spoke-factory-c.sh: 기존 IoT Secret 유지, factory-c egress/cluster Secret/ApplicationSet/app sync 복구
  - build-iot-factory-a.sh: factory-a IoT Thing/certificate/K3s Secret을 새로 만들거나 갱신해야 할 때만 사용
  - stop-dummy-generators.sh: Hub 삭제 전 factory-b/c VM dummy generator 정지
  - verify-complete.sh: Hub/IoT/factory-a rollout 통합 검증

현재 AWS 상태: Foundation/IoT/ECR 리소스 활성, Hub EKS는 build/destroy로 반복 재생성 가능
이미지: ECR 611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/{factory-a-log-adapter,edge-iot-publisher}:sha-f71a104
IoT Secret: ai-apps/aws-iot-factory-a-cert 유지 중
ECR pull secret: ai-apps/ecr-registry 유지 중
Longhorn PVC: aegis-spoke-outbox 유지 중

완료: M5 factory-b/c Hub-Spoke 등록 및 데이터 플레인 검증
  - factory-b Tailnet IP: 100.98.121.77
  - factory-c Tailnet IP: 100.76.243.72
  - factory-b nodes: master, worker1
  - factory-c nodes: factory-c-master, factory-c-worker
  - master taint 유지, worker label 적용 완료
  - Hub ArgoCD cluster Secrets: cluster-factory-b, cluster-factory-c
  - Hub egress Services: factory-b-master-tailnet, factory-c-master-tailnet
  - Applications: aegis-spoke-factory-b, aegis-spoke-factory-c 생성 및 Sync operation 성공
  - GitOps chart/values는 b/c hostPath outbox를 지원하도록 전환 완료 (aegis-pi-gitops commit 04f90b2, remote push 완료)
  - factory-b worker1: /var/lib/aegis/outbox drwxrwx--- 10001:10001 생성 확인 (SSH 직접)
  - factory-c worker: /var/lib/aegis/outbox 생성 확인 (kubectl pod exit 0, uid 10001 write 성공)
  - factory-b/c local dummy generator systemd 배포 및 canonical JSON 생성 확인
  - factory-b/c IoT Thing/certificate/K3s Secret 준비 및 K3s edge-iot-publisher 활성화 확인
  - factory-b/c -> IoT Core -> S3 raw/factory-b, raw/factory-c prefix 분리 적재 확인
  - factory-c master/worker VirtualBox NAT 중복 IP 문제 해결: enp0s8 고정 IP와 flannel-iface 적용
  - factory-b worker1 clock drift 약 32분 문제 해결: chrony makestep으로 S3 partition timestamp 정합성 복구

확정: factory-b/c 테스트베드 데이터 플레인 방향
  - dummy generator는 Kubernetes Deployment가 아니라 VM 로컬 script/systemd service로 실행
  - dummy generator는 worker node의 /var/lib/aegis/outbox에 canonical JSON을 write
  - GitOps/ArgoCD는 공통 edge-iot-publisher만 배포
  - publisher는 hostPath /var/lib/aegis/outbox를 mount해 IoT Core로 publish
  - factory-a는 기존 Longhorn PVC outbox + factory-a-log-adapter 구조 유지

Hub-only 삭제/재생성 운영 순서:
  - 내릴 때: scripts/destroy/stop-dummy-generators.sh -> scripts/destroy/destroy-hub.sh 또는 destroy-all.sh
  - 올릴 때: scripts/build/build-hub.sh -> 필요 시 build-admin-ui-after-ns.sh -> register-spoke-factory-a/b/c.sh -> manage-dummy-generators.sh start factory-b/c
  - connect-hub-tailscale-ui.sh는 ALB/Admin UI HTTPS가 아닌 Tailnet UI 직접 접근이 필요할 때만 선택 실행
  - 이 경로에서는 IoT Core Thing/certificate와 Spoke K3s Secret을 다시 만들지 않는다.

다음 우선: M6 Issue 2~4 runtime-config 적용, 온도/습도 기준값 계산 연결, Risk Twin 출력 구조 구현
보류/별도 담당: M3 Issue 6 manifest 자동 갱신 workflow, M6 Dashboard page/VPC 세부 화면, M7 전체 통합 검증
고도화 후보: Daily Report S3 read 병렬화, state_snapshot 읽기 축소, generation-metadata에 Bedrock token usage/input object count 저장
후속 리팩토링: M7 Issue 0에서 repo 분리 및 OIDC CI/CD 고도화

완료: M0 factory-a Safe-Edge 기준선
완료: M1 Issue 0 AWS CLI MFA 및 Terraform 접근 설정
완료: M1 Issue 1 EKS/VPC Terraform apply 및 kubectl 접근 확인
완료: M1 Issue 2 Hub Kubernetes 네임스페이스 설계 및 생성
완료: M1 Issue 3 Hub ArgoCD 설치 및 CLI/UI 검증, Ansible bootstrap 전환
완료: M1 Issue 4 S3 bucket apply, 보안 설정, IoT Rule 적재 검증, risk-normalizer IRSA S3 read/write 검증 완료
완료: M1 Issue 5 IoT Thing, certificate, policy, IoT Rule, 테스트 메시지 S3 적재 검증 완료
완료: M1 Issue 6 AMP Workspace 생성, Prometheus remote_write IRSA 구성, EKS pod assume-role 검증 완료
완료: M1 Issue 7 Hub Prometheus Agent 설치, remote_write 오류 로그 부재, AMP Query API `up{cluster="AEGIS-EKS"}` 수신 검증 완료
완료: M1 Issue 8 내부 Grafana 설치, AMP datasource SigV4/IRSA query 검증 완료
완료: M1 Issue 9 AWS Load Balancer Controller 준비
완료: M1 Issue 10 ArgoCD/Grafana HTTPS Admin Ingress 구성. Route53/ACM/Ingress/ALB와 HTTPS 검증 완료
보류: M1 Issue 11 WAF/Cognito/OIDC 운영 보안 강화
완료: M1 Issue 12 runtime-config.yaml 구조 초안과 VM dummy data 추천값 작성
완료: M2 Issue 1 Tailscale Tailnet/tag/Auth Key 정책 수립 및 Tailnet 확인
완료: M2 Issue 2 `factory-a-master` Tailscale 설치, Tailnet 참여, Windows 운영자 PC에서 ping/SSH 검증
완료: M2 Issue 3 EKS Hub Tailscale Operator 설치, egress Service, ArgoCD/Grafana Tailscale IP UI 접근 검증
완료: M2 Issue 4 Tailscale IP/tls-server-name 기반 factory-a kubeconfig 검증
완료: M2 Issue 5 ArgoCD factory-a cluster 등록 및 Successful 확인
완료: M2 Issue 6 factory-a-podinfo-smoke Sync/Healthy, Tailscale egress 장애/복구 검증
보류: EKS API endpoint CIDR 축소는 전체 설계 마무리 후 재검토
완료: Safe-Edge start_test Ansible playbook
확정: Terraform = 인프라, Ansible = 설정/소프트웨어/bootstrap, GitHub Actions = CI, GitHub+ArgoCD = CD
AWS 실제 리소스 상태: 2026-05-29 기준 Foundation/IoT/data-pipeline 리소스 활성. foundation S3/ECR/DynamoDB, IoT Rule 3개, Lambda data processor, DataProcessorRefresh1m Scheduler, GraphAggregator5m Scheduler, `factory-a/b/c` IoT Thing/Policy/certificate, K3s IoT Secret 활성 상태. Hub EKS/Admin UI는 build/destroy로 재생성 가능하다. AMP workspace는 삭제 완료. Hub NAT Gateway는 Azone 단일 NAT로 전환 완료.
Terraform state: infra/hub apply 완료, infra/foundation apply 완료, infra/data-pipeline apply 완료
다음 작업 우선순위: daily factory report 검증/AWS 실행 완료 후 M6 Risk Twin/Dashboard 구현.
```

## 지금까지 완료한 일

### M0 factory-a 기준선

- Raspberry Pi 3-node K3s `factory-a` 기준선 구축 및 검증 완료
- ArgoCD, Longhorn, MetalLB, monitoring, ai-apps 기준선 정리
- AI snapshot 저장 기준을 Longhorn PVC에서 node-local hostPath로 변경한 현재 운영 기준 반영
- AI 추론 결과는 InfluxDB PVC를 통해 Longhorn에 저장하는 기준 반영
- failover/failback 테스트 결과 및 트러블슈팅 문서 확장
- 변경된 계획 추적용 `docs/changes/` 문서 추가
- `start_test` 반복 점검용 Ansible playbook 추가
- 2026-05-08 기준 `eth0` 내부망, `wlan0` 인터넷 default route, `tailscale0` 원격 제어망 역할을 확정하고 `start_test.yml`에 master `wlan0` 인터넷 경로와 Tailscale 상태 검증을 추가했다.

### Data / Dashboard VPC 확장 방향

- 최신 확정 클라우드 아키텍처는 `docs/planning/15_cloud_architecture_final.md`를 기준으로 한다.
- 사용자 대시보드는 Tailscale에 직접 의존하지 않는 1번 Data / Dashboard VPC 방향으로 정리
- Dashboard Web/API는 ArgoCD, Tailscale, EKS API, Spoke K3s API에 직접 접근하지 않는 방향 확정
- Edge data-plane이 `factory_state`, `infra_state` 안에 센서/시스템/장치/워크로드/heartbeat 상태를 함께 보내야 한다는 기준 반영
- 관련 문서: `docs/planning/07_dashboard_vpc_extension_plan.md`

### Admin UI HTTPS Ingress 방향

- MVP에서는 관리자 외부 접근 검증을 위해 ArgoCD/Grafana를 Public ALB 1개와 HTTPS host 기반 Ingress로 노출하는 방향으로 재정렬했다.
- ArgoCD와 Grafana는 계속 EKS 내부 Pod/Service로 실행하고, Kubernetes Service는 `ClusterIP`를 유지한다.
- 최소 보호선은 HTTPS, MVP 임시 허용 CIDR, ArgoCD/Grafana 자체 로그인이다.
- WAF, Cognito, 외부 OIDC/SSO는 MVP 필수 범위에서 제외하고 운영 보안 강화 백로그인 M1 Issue 11로 분리했다.
- 도메인은 `minsoo-tech.cloud` 기준으로 확정했다. Route53 Hosted Zone NS는 `ns-1079.awsdns-06.org`, `ns-1913.awsdns-47.co.uk`, `ns-7.awsdns-00.com`, `ns-872.awsdns-45.net`이다.
- `scripts/build/build-hub.sh`는 Terraform apply 직후 `scripts/ops/admin-ui-nameservers.sh`를 실행해 `secret/admin-ui-nameservers.txt`를 갱신한다. Gabia에 입력할 NS는 재생성 후 이 파일을 다시 확인한다.
- 현재 기본값은 `ADMIN_UI_INGRESS_ENABLED=false`다. `scripts/build/build-hub.sh`는 Admin UI용 Route53 Hosted Zone/ACM certificate와 NS 파일까지만 준비하고, Gabia NS 위임 뒤 `scripts/build/build-admin-ui-after-ns.sh`로 ACM `ISSUED` 대기와 Admin UI Ingress 활성화를 별도 실행한다.
- 2026-05-20 기준 `scripts/build/build-hub.sh`는 factory-a K3s에 의존하지 않는다. Tailscale Operator, factory-a egress Service, ArgoCD/Grafana Tailscale UI Service, ArgoCD `factory-a` cluster Secret, Spoke ApplicationSet 배포는 `build-iot-factory-a.sh`에서 IoT Secret 준비 후 수행한다. `~/Aegis/.aegis/secrets/tailscale/operator.env`가 없으면 해당 단계가 실패한다.

### AWS CLI MFA 및 Terraform 접근

- 로컬 WSL 환경에서 AWS CLI, Terraform, jq를 프로젝트 로컬 `.tools` 아래에 설치
- `.bashrc`에 Aegis AWS 환경 로더 등록
- `aws configure` 기본 프로필 구성 완료
- MFA ARN을 `mfa.cfg`에 구성 완료
- `mfa <OTP>` 실행 및 `aws sts get-caller-identity` 확인 완료
- 기본 AWS 리전은 `ap-south-1`
- 관련 문서: `docs/planning/08_aws_cli_mfa_terraform_access.md`

### M1 Issue 1 EKS/VPC 설계 및 적용

- EKS/VPC Decision Record 작성
- Terraform skeleton 작성
- VPC/subnet/NAT/route table은 직접 AWS 리소스로 관리하고, EKS는 공식 Terraform module 사용
- `terraform init -backend=false` 완료
- `terraform validate` 통과
- `terraform fmt` 통과
- `terraform plan -out=tfplan` 확인
- `terraform apply -auto-approve tfplan` 완료
- 기존 `aegis-pi-hub-mvp` 인프라를 `terraform destroy -auto-approve`로 제거
- 새 네이밍/버전 기준으로 `terraform apply -auto-approve tfplan` 완료
- `aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS` 완료
- `kubectl v1.34.7`을 `/home/vicbear/Aegis/.tools/bin/kubectl`에 설치
- `kubectl get nodes`에서 worker node 2대 `Ready` 확인
- `kubectl cluster-info`에서 EKS control plane과 CoreDNS 응답 확인
- 리소스 네이밍 규칙을 `AEGIS-[resource]-[feature]-[zone]`로 고정
- Terraform EKS 이름은 `AEGIS-EKS`, Kubernetes 버전은 `1.34`
- Issue 2 namespace/LimitRange 적용 후 최소 분리 작업을 위해 테스트용 Hub 리소스를 `terraform destroy -auto-approve`로 제거
- 책임 범위를 `infra/hub`, `scripts/ansible`, `infra/foundation` 기준으로 분리

관련 문서:

- `docs/planning/09_m1_eks_vpc_decision_record.md`
- `docs/planning/11_delivery_ownership_flow.md`
- `infra/hub/README.md`
- `infra/hub/*.tf`

## 현재 로컬 Terraform 기준

```text
Terraform roots:
- infra/hub: VPC, subnet, single NAT Gateway, EKS cluster, node group
- infra/foundation: S3, ECR, DynamoDB처럼 EKS destroy와 분리할 영속 리소스
Ansible bootstrap:
- scripts/ansible: kubeconfig 갱신, namespace, LimitRange, ArgoCD Helm install, legacy Prometheus Agent cleanup, Grafana/LB Controller 검증
Region: ap-south-1
VPC: 신규 생성
VPC CIDR: 10.0.0.0/16
Resource naming: AEGIS-[resource]-[feature]-[zone]
Target cluster name: AEGIS-EKS
Target Kubernetes version: 1.34
AZ: ap-south-1a, ap-south-1c
Subnets: public 2개 + private 2개
NAT Gateway: public Azone에 1개
Private route table: Azone/Czone 모두 단일 NAT Gateway 사용
EKS endpoint: public endpoint
EKS endpoint CIDR: 0.0.0.0/0 (MVP bootstrap 임시 기준)
Node subnet: private subnet
Node group: EKS Managed Node Group
Instance type: t3.medium 기본
Node count: min/desired/max 2
Capacity: On-Demand
```

`t3.micro`는 사용하지 않는 기준이다. EKS system pod, CNI, CoreDNS, ArgoCD/Grafana/관측 컴포넌트까지 고려하면 메모리 여유가 작아 Hub MVP 기준선으로 부적합하다고 판단했다.

### M1 Issue 3 Hub ArgoCD

- 2026-05-21 기준 Hub-only 생성 순서는 `build-hub.sh` -> 필요 시 `build-admin-ui-after-ns.sh` -> `register-spoke-factory-a/b/c.sh` -> `manage-dummy-generators.sh start factory-b/c`다. `connect-hub-tailscale-ui.sh`는 Tailnet UI 직접 접근이 필요할 때만 선택 실행한다.
- `aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS` 완료.
- `kubectl get nodes -o wide`에서 EKS worker node 2대 `Ready` 확인.
- Hub namespace/LimitRange는 처음 Terraform으로 검증했고, 최종 기준은 Ansible bootstrap으로 전환했다.
- `argocd`, `observability`, `risk`, `ops-support` namespace `Active` 확인.
- 각 namespace에 `default-limits` LimitRange 생성 확인.
- ArgoCD Helm chart `argo/argo-cd` `9.5.11` 설치 완료.
- ArgoCD app version은 `v3.3.9`.
- Helm release는 `argocd`, namespace는 `argocd`.
- `/home/vicbear/Aegis/.tools/bin/argocd` CLI `v3.3.9` 설치 완료.
- `kubectl -n argocd port-forward service/argocd-server 8080:443`로 UI 접근을 검증했다.
- `https://127.0.0.1:8080` HTTP 200 확인.
- 초기 admin secret 생성 확인. 비밀번호 값은 문서에 기록하지 않는다.
- CLI admin login 성공.
- `argocd cluster list`에서 `https://kubernetes.default.svc` / `in-cluster` 확인.
- `argocd-server` service는 `ClusterIP` 유지. M1 Issue 3에서는 AWS LoadBalancer를 만들지 않았다.
- 기존 ArgoCD Helm release가 chart `argo-cd-9.5.11`로 이미 deployed 상태이면 bootstrap에서 Helm upgrade를 건너뛰도록 최적화했다.

## 현재 AWS 상태

```text
AWS 계정 연결: MFA 세션으로 확인 완료
AWS 리소스 상태: 2026-05-15 rebuild 후 active
Hub EKS: AEGIS-EKS active, node 2 Ready
Hub VPC: vpc-004036a95d486c2c3
Private subnets: subnet-06e29617d5f8fa880, subnet-0887213fcdb8222d2
Public subnets: subnet-0bd88736ba79c8bc1, subnet-0aeab1c105fff4ac9
ArgoCD: argo-cd-9.5.11 / app v3.3.9, all pods Running
Grafana: grafana-10.5.15 / app 12.3.1, pod Running
Prometheus Agent: active 구성에서 제거, legacy 리소스 cleanup 대상
AWS Load Balancer Controller: 2 pods Running
Foundation S3 bucket: aegis-bucket-data active
AMP Workspace: active Terraform 구성에서 제거, 다음 foundation plan/apply에서 destroy 확인 필요
ECR repositories: aegis/edge-agent, aegis/factory-a-log-adapter, aegis/edge-iot-publisher active
IoT Thing: AEGIS-IoTThing-factory-a active
IoT Policy: AEGIS-IoTPolicy-factory-a active
IoT Rule: AEGIS_IoTRule_factory_a_raw_s3 active
K3s Secret: factory-a ai-apps/aws-iot-factory-a-cert DATA=4
Admin UI ACM: ISSUED
Admin UI ALB: aegis-admin-ui-1594900970.ap-south-1.elb.amazonaws.com
Admin UI HTTPS: https://argocd.minsoo-tech.cloud, https://grafana.minsoo-tech.cloud
Tailscale UI: https://100.78.107.75/ for ArgoCD, http://100.117.77.36/ for Grafana
ArgoCD cluster Secret: cluster-factory-a -> https://factory-a-master-tailnet.argocd.svc.cluster.local:6443
GitOps Application: aegis-spoke-factory-a Synced + Healthy
factory-a K3s: master/worker1/worker2 Ready
factory-a data-plane workloads: ai-apps/aegis-spoke-edge-iot-publisher, ai-apps/aegis-spoke-factory-a-log-adapter
terraform state: infra/hub apply complete
terraform state: infra/foundation apply complete
```

주의:

- `terraform init`은 provider/module을 로컬에 내려받는 작업이라 AWS 리소스를 만들지 않는다.
- AWS 리소스가 실제로 만들어지는 시점은 `terraform apply` 실행 시점이다.
- 테스트가 끝나면 반드시 `scripts/destroy/destroy-hub.sh` 또는 `scripts/destroy/destroy-all.sh`로 EKS, NAT Gateway, node group을 제거한다.
- 2026-05-20에는 Hub-only 재시작을 단계별 실행 파일로 분리했다. Hub build, Admin UI, Tailnet UI, factory별 Spoke 등록, dummy generator stop을 각각 독립 실행한다.

과거 2026-05-08 삭제 전 검증 기록:

```text
Cluster: AEGIS-EKS
Region: ap-south-1
Kubernetes version: 1.34
VPC: vpc-09c894826697d728f
Private subnets: subnet-002dae5b51fec10e3, subnet-0fbe009eec8a23f95
Public subnets: subnet-017c1e07df8bd8e1f, subnet-0ab9faef9ef8e6086
Node group: AEGIS-EKS-node
Node status before destroy: 2 Ready
Hub namespaces: argocd, observability, risk, ops-support
Terraform state: infra/hub destroyed, infra/foundation destroyed
Ansible bootstrap: namespace, LimitRange, ArgoCD Helm release 재생성 기준 추가
ArgoCD Helm release: argocd / argo-cd-9.5.11 / app v3.3.9
S3 bucket: aegis-bucket-data
AMP Workspace: 과거 검증 이력. 2026-05-27 비용 최적화 기준에서는 active 구성에서 제거
IoT Rule: AEGIS_IoTRule_factory_a_raw_s3
IRSA Role: AEGIS-IAMRole-IRSA-risk-normalizer
IRSA ServiceAccount: risk/risk-normalizer
```

현재 Terraform 기준 이름:

```text
Cluster: AEGIS-EKS
Kubernetes version: 1.34
VPC name: AEGIS-VPC
Public subnets: AEGIS-Subnet-public-Azone, AEGIS-Subnet-public-Czone
Private subnets: AEGIS-Subnet-private-Azone, AEGIS-Subnet-private-Czone
NAT gateways: AEGIS-NAT-public-Azone, AEGIS-NAT-public-Czone
Private route tables: AEGIS-RouteTable-private-Azone, AEGIS-RouteTable-private-Czone
Node group: AEGIS-EKS-node
Cluster IAM role: AEGIS-IAMRole-EKS-cluster
Node IAM role: AEGIS-IAMRole-EKS-node
Cluster security group: AEGIS-SG-EKS
Node security group: AEGIS-SG-EKS-node
```

최신 확인:

```text
kubectl get nodes -o wide
2 Ready

kubectl get namespaces argocd observability risk ops-support
4 Active

kubectl -n argocd get pods
all Running / Ready

helm list -n argocd
argocd deployed argo-cd-9.5.11 app v3.3.9

terraform -chdir=infra/hub plan -detailed-exitcode
No changes

terraform -chdir=infra/foundation plan -detailed-exitcode
No changes

EKS internal IRSA test pod
assumed role: AEGIS-IAMRole-IRSA-risk-normalizer
raw/factory-a read: allowed
latest/factory-a write: allowed
raw/factory-a write: AccessDenied
```

과거 2026-05-04 destroy 전 확인 기록:

```text
kubectl get nodes
2 Ready

kubectl -n argocd get pods
all Running / Ready

ssh minsoo@10.10.10.10 'kubectl -n ai-apps get secret aws-iot-factory-a-cert'
secret exists, DATA=4
```

## 다음에 할 일

### 1. M6 Risk 데이터 계약 고도화

Daily Factory Report AWS 수동 실행 검증은 완료됐다. 다음 세션에서는 Dashboard 담당자가 읽을 수 있는 Risk 데이터 계약을 먼저 고정한다.

```text
1. cd /home/vicbear/Aegis/git_clone/Aegis-pi
2. git status --short 로 변경 파일 확인
3. apps/data-processor/processor/risk.py 현재 하드코딩 상수와 configs/runtime/runtime-config.yaml 비교
4. Risk output 계약 확정: score/level/top_causes + Risk Twin read model 필드
5. runtime-config.yaml을 Lambda package 또는 배포 입력으로 읽는 방식 결정
6. risk_enabled/weight/threshold/factory override 적용
7. DynamoDB LATEST/HISTORY#STATE와 S3 processed risk_score/state_snapshot에 Risk Twin 필드 반영
8. apps/data-processor 단위 테스트와 필요한 fixture 갱신
```

주의:

```text
Dashboard page 및 Dashboard VPC 구현은 별도 담당 범위다.
이 repo의 우선 작업은 Dashboard가 조회할 DynamoDB/S3 processed 계약과 Risk Twin 출력 구조다.
Daily Report reporting stack은 현재 삭제된 상태이며, 필요할 때 scripts/build/build-reporting.sh 로 다시 올린다.
```

### 2. Daily Factory Report 고도화

보고서 기능은 검증 완료 상태다. 다음 개선은 비용/성능/관측성 중심이다.

```text
1. S3ProcessedReader에서 S3_GET_CONCURRENCY를 실제 사용해 GetObject 병렬화
2. state_snapshot 전체 읽기 대신 latest N개 또는 hour별 마지막 snapshot만 읽는 방식 검토
3. generation-metadata.json에 Bedrock token usage, context bytes, output bytes, input object count 저장
4. docs/ops/25_daily_factory_report_cost.md를 실측 기반으로 갱신
```

### 3. Hub 재기동 순서

Hub EKS를 destroy한 뒤 다시 필요한 작업을 시작할 때는 아래 순서로 올린다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

전체 생성은 아래 진입점을 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
```

Admin UI Ingress/ALB는 전체 생성과 분리해, Gabia NS 위임 뒤 아래 진입점을 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-admin-ui-after-ns.sh
```

ArgoCD UI 접근:

```text
https://argocd.minsoo-tech.cloud
```

Grafana UI 접근:

```text
https://grafana.minsoo-tech.cloud
```

로컬 fallback 포트포워딩:

```bash
/home/vicbear/Aegis/git_clone/Aegis-pi/scripts/ops/argocd-port-forward.sh
```

### 3. M1 Issue 4/5 S3 및 IoT Core 완료 상태

현재 공식 이슈 `M1 Issue 4 - [Hub/S3] 버킷 생성 및 경로 파티셔닝 설계`와 `M1 Issue 5 - [Hub/IoT Core] Thing / 인증서 / 규칙 구성`은 완료 상태다.

완료한 내용:

- `infra/foundation`을 독립 Terraform root로 구성
- S3 bucket 이름 결정: `aegis-bucket-data`
- public access block enabled 기준 적용
- versioning enabled 기준 적용
- SSE-S3 encryption 기준 적용
- raw/processed/latest prefix 기준 확정
- lifecycle 기준 확정
- `terraform apply`: `6 added, 0 changed, 0 destroyed`
- AWS API 검증:
  - versioning `Enabled`
  - public access block 4개 옵션 모두 `true`
  - SSE-S3 `AES256`
  - lifecycle rule 4개 적용 확인
- IoT Rule `AEGIS_IoTRule_factory_a_raw_s3` 생성 및 S3 raw prefix 적재 검증
- Test object `raw/factory-a/sensor/yyyy=2026/mm=05/dd=06/manual-20260506T014423Z-31668.json` 확인
- `risk/risk-normalizer` IRSA 구성 및 EKS 내부 pod 검증
- IRSA 권한 범위 확인:
  - `raw/factory-a/` read 허용
  - `latest/factory-a/` write 허용
  - `raw/factory-a/` write 거부

남은 내용: 없음. 이후 M1 Issue 6~10/12와 M2 Issue 1~6은 완료됐다. M2에서는 EKS Hub Tailscale Operator 설치, `factory-a-master` K3s API TCP reachability, `factory-a` kubeconfig/ArgoCD cluster 등록, `factory-a-podinfo-smoke` Sync/Healthy, Tailscale egress 장애/복구 검증까지 완료했다.

### 4. ArgoCD 접근 전략 유지

현재 ArgoCD 접근 기준:

- Hub rebuild 후에는 ArgoCD/Grafana를 Tailscale UI Service 또는 로컬 fallback port-forward로 접근한다.
- M2에서 ArgoCD/Grafana Tailscale IP 접근과 `factory-a` egress 경로를 검증했다.
- EKS API endpoint public CIDR 축소는 M2 완료 조건에서 제외하고, 운영 보안 강화/설계 마무리 후 재검토한다.
- ArgoCD 설정은 UI 클릭보다 Git/YAML/ApplicationSet으로 코드화한다.
- ArgoCD public `LoadBalancer`는 만들지 않는다.

### 5. ArgoCD 재생성 자동화

EKS를 destroy/recreate할 때 ArgoCD 재설치를 반복하지 않도록 현재 수동 Helm install 기준을 Ansible bootstrap으로 전환했다.

적용 내용:

- `scripts/ansible/inventory/hub_eks_dynamic.sh` 추가 완료
- `scripts/ansible/inventory/group_vars/hub_eks.yml` 추가 완료
- `scripts/ansible/files/hub-bootstrap.yaml` 추가 완료
- `scripts/ansible/files/argocd-values.yaml` 추가 완료
- `scripts/ansible/playbooks/hub_argocd_bootstrap.yml` 추가 완료
- `scripts/ansible/playbooks/hub_argocd_verify.yml` 추가 완료
- `helm upgrade --install`로 `argo/argo-cd` chart `9.5.11` 관리
- release name `argocd`, namespace `argocd`, service type `ClusterIP` 유지
- repo, AppProject, Application, ApplicationSet은 후속 코드화
- 포트포워딩은 Terraform에 넣지 않고 `scripts/ops/argocd-port-forward.sh`로 제공
- dynamic inventory는 `infra/hub`의 `terraform output -json`을 읽어 cluster name, region, kubeconfig 명령을 Ansible 변수로 제공한다.
- 다음 `hub_argocd_bootstrap.yml` 실행 때 ArgoCD Helm release가 새로 생성된다.

포트포워딩 스크립트는 아래 흐름을 따른다.

```text
aws eks update-kubeconfig
kubectl -n argocd wait
kubectl -n argocd port-forward service/argocd-server 8080:443
```

### 6. 리소스 종료 기준

작업을 멈추거나 장시간 사용하지 않을 때는 비용 방지를 위해 아래 순서로 제거한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-hub.sh
```

전체 비용 제거가 필요하면 아래 진입점을 사용한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-all.sh
```

장시간 사용하지 않을 리소스를 남기지 않는다. EKS control plane, NAT Gateway, managed node group은 켜져 있는 동안 비용이 발생한다. 2026-05-08에는 `destroy-all.sh`로 K3s IoT Secret, IoT, Hub, foundation을 삭제했고 active AEGIS AWS fixed-cost resource 0개 상태를 확인했다.

## 문서 갱신 상태

M1~M5 완료 상태와 2026-05-27 daily factory report 구현 진행 상태를 문서에 반영했다.
AWS 비용 기준은 `docs/ops/15_aws_cost_baseline.md`에 있고, AWS 리소스나 상시 운영 경로가 추가될 때 함께 갱신한다.
구현 책임 경계는 Terraform, Ansible, GitHub Actions, GitHub+ArgoCD 흐름으로 고정한다.

- `README.md`
- `docs/README.md`
- `docs/issues/M6_risk-twin-dashboard.md`
- `docs/issues/M1_hub-cloud.md`
- `docs/issues/M3_deploy-pipeline.md`
- `docs/issues/MASTER_CHECKLIST.md`
- `docs/issues/SESSION_STATE.md`
- `docs/ops/README.md`
- `docs/ops/00_quick_start.md`
- `docs/ops/13_hub_namespace_baseline.md`
- `docs/ops/14_hub_run_commands.md`
- `docs/ops/15_aws_cost_baseline.md`
- `docs/ops/16_hub_prometheus_amp.md`
- `docs/ops/17_hub_grafana_amp.md`
- `docs/ops/24_daily_factory_report.md`
- `docs/planning/09_m1_eks_vpc_decision_record.md`
- `docs/planning/00_project_overview.md`
- `docs/planning/02_implementation_plan.md`
- `docs/planning/17_llm_daily_factory_report_plan.md`
- `docs/planning/11_delivery_ownership_flow.md`
- `infra/README.md`
- `infra/hub/README.md`
- `infra/foundation/README.md`
- `infra/reporting/README.md`
- `apps/daily-report-generator/README.md`
- `scripts/iot/README.md`
- `scripts/build/README.md`
- `scripts/destroy/README.md`
- `scripts/hub/README.md`
- `scripts/README.md`
- `scripts/ansible/README.md`
- `scripts/ansible/playbooks/README.md`

## 주의사항

- Access Key, Secret Access Key, Session Token, MFA OTP, SSH 비밀번호는 문서에 기록하지 않는다.
- `terraform.tfvars`는 Git에 커밋하지 않는다.
- `infra/hub/.terraform/`은 Git에 커밋하지 않는다.
- `infra/hub/.terraform.lock.hcl`은 provider lock을 위해 커밋 대상이다.
- `terraform apply` 전에는 항상 `terraform plan`을 먼저 확인한다.
- `terraform destroy`는 실험 종료 절차로 함께 수행한다.

## 최근 커밋

```text
18fc7cb docs: add data-plane and vm-spoke validation criteria
4a99c3e docs: justify CD pipeline with operational feedback loop
a65216f docs: record mentoring-based MVP and architecture updates
366aa8b config: normalize factory-a runtime profile labels
7cd2284 docs: align control and data dashboard boundaries
```

현재 세션 정리 내용:

```text
2026-05-28 세션 저장 기준

M4/M5 완료 상태:
  factory-a/b/c data-pipeline은 IoT Core -> S3 raw, IoT Core -> Lambda -> DynamoDB/S3 processed 흐름 검증 완료.
  factory-b/c는 2-node VM K3s 테스트베드, local dummy generator, common edge-iot-publisher, Chrony 시각 동기화 기준으로 검증 완료.
  factory-a 최신 processed state_snapshot 기준 nodes_ready=3/3, pods_ready=6/6, pipeline_status=normal 확인.

Daily Factory Report 검증 완료:
  apps/daily-report-generator/ package와 4개 Lambda handler 구현 완료.
  AggregateFactoryHour:
    not_ready_nodes, unhealthy_workloads 구조화.
    node 이름이 비어 있으면 control-plane:Unknown, worker:Unknown 같은 fallback label 사용.
  MergeFactoryDaily:
    ai_spike_event_count, ai_spike_event_counts, ai_spike_event_examples 추가.
    likely_infra_causes 추가.
    recommended_checks를 rule 기반으로 생성하고 evidence message id 1~2개 포함.
  PromptBuilder:
    AI spike evidence, infra cause, recommended_checks, S3 processed/raw 한계, testbed/dummy 해석 반영.
  infra/reporting/ Terraform root module 추가 및 AWS apply 검증 완료.
  scripts/build/build-reporting.sh, scripts/destroy/destroy-reporting.sh 추가.

저장된 테스트 산출물:
  /home/vicbear/Aegis/test_paper/factory-b-hh03-report-context-enriched-v2.json
  /home/vicbear/Aegis/test_paper/factory-b-hh03-prompt-enriched-v2.txt
  /home/vicbear/Aegis/test_paper/factory-b-hh03-hourly-aggregate-enriched-v2.json
  /home/vicbear/Aegis/test_paper/factory-b-hh03-enriched-v2-test-note.md

검증:
  python -m pytest -q apps/daily-report-generator 통과: 11 passed
  python -m compileall -q apps/daily-report-generator 통과
  terraform -chdir=infra/reporting fmt -check -diff 통과
  terraform -chdir=infra/reporting init/validate 통과
  scripts/build/build-reporting.sh 실행: 17 resources added
  Step Functions manual execution manual-factory-report-20260528T064840Z: SUCCEEDED
  S3 reports/daily/yyyy=2026/mm=05/dd=27/factory-b/ 산출물 확인
  report.md 핵심 지표/데이터 수집/Risk Score/센서 및 AI 이벤트/인프라 상태/주요 이벤트/확인 필요 항목 표와 분석 문단 확인
  scripts/destroy/destroy-reporting.sh 실행: 17 resources destroyed, reporting Lambda/Step Functions/Scheduler/IAM/LogGroup 삭제 확인, S3 processed input과 reports/daily output 보존

주의:
  reporting stack은 현재 내려간 상태다. 필요할 때 build-reporting.sh로 다시 배포한다.
  Daily Report 실행 병목은 작은 S3 processed object 다량 순차 GetObject이며, 비용/성능 개선 후보로 남긴다.
  CloudWatch Logs/metrics 기반 reporting pipeline health는 후속 확장 방향으로 문서화됐고, 아직 구현 전이다.
  Dashboard page와 Dashboard VPC 구현은 별도 담당 범위다.

다음 세션 우선 작업:
  1. git status --short 로 변경 파일 확인
  2. Risk output 계약과 Dashboard read model 필드 확정
  3. runtime-config.yaml을 Lambda data processor Risk 계산에 연결
  4. Risk Twin 출력 구조를 DynamoDB LATEST/HISTORY#STATE와 S3 processed에 반영
  5. Daily Report S3 read 병렬화/state_snapshot 축소/metadata 비용 관측 필드/CloudWatch 보조 조회 중 하나를 선택해 고도화
```

## 갱신 규칙

- 이 파일은 새 내용을 아래에 계속 추가하지 않는다.
- 세션 저장 요청이 오면 `마일스톤 기준 진행 현황`, `현재 큰 상태`, `지금까지 완료한 일`, `현재 AWS 상태`, `다음에 할 일`, `현재 세션 정리 내용`을 현재 기준으로 갱신한다.
- 오래된 완료 기록이 현재 판단에 불필요하면 요약으로 줄인다.
- 공식 체크 여부는 항상 `docs/issues/MASTER_CHECKLIST.md`와 각 M0~M7 이슈 문서를 우선한다.
