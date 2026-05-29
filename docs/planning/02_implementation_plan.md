# 구현 전략 및 단계 계획

상태: source of truth
기준일: 2026-05-28

## 목적

프로젝트를 어떤 순서로 구현할지, 각 단계에서 무엇을 만들어야 하고 어떤 조건이 만족되면 다음 단계로 넘어갈 수 있는지 정리한다.

## 현재 상태

- Phase 0 문서 기준선 정리는 완료 상태로 유지 보수 중이다.
- Phase 1 M0 `factory-a` Safe-Edge 기준선은 구축 및 실측 검증까지 완료됐다.
- Phase 2 M1은 AWS MFA/Terraform 접근, Hub EKS/VPC, Hub namespace, Hub ArgoCD, foundation S3/AMP, `factory-a` IoT Thing/Policy/K3s Secret, IoT Rule -> S3 raw 적재, IRSA S3 권한, Hub Prometheus Agent 설치, AMP remote_write 수신, Grafana AMP datasource query, AWS Load Balancer Controller, Admin UI HTTPS Ingress 검증까지 진행했다.
- Hub AWS 리소스와 foundation S3/AMP/Admin UI는 `build-hub.sh`, `build-admin-ui-after-ns.sh` 기준으로 재생성/검증한다. Hub build는 cluster 등록을 수행하지 않으며, Tailnet UI는 `connect-hub-tailscale-ui.sh`, Spoke ArgoCD cluster 등록과 ApplicationSet sync는 `register-spoke-factory-a/b/c.sh`로 factory별 분리했다.
- M1 Issue 12에서 `configs/runtime/runtime-config.yaml`과 VM dummy data 추천값을 작성했다.
- M2 Issue 1~6에서 Tailnet/tag/Auth Key 정책 수립, `factory-a-master` Tailscale 참여, EKS Hub Tailscale Operator/egress 구성, `factory-a` kubeconfig/ArgoCD cluster 등록, `factory-a-podinfo-smoke` Sync/Healthy, Tailscale egress 장애/복구 검증을 완료했다.
- M3는 Issue 1~5와 build/verify 기반 배포 검증 범위를 완료했다. Issue 6 manifest 자동 갱신 workflow는 M7 CI/CD hardening 때 재검토한다.
- M4 Issue 1~8 Raw 계약, `factory-a-log-adapter`, `edge-iot-publisher`, 이미지화/GitOps chart, IoT Core -> S3 raw 적재, Lambda data processor, DynamoDB LATEST/HISTORY#STATE, S3 processed, `pipeline_status` 검증은 완료했다.
- M5는 `factory-b/c` 2-node VM K3s, Tailnet/Hub ArgoCD 등록, GitOps hostPath outbox 전환, local dummy generator systemd 실행, common `edge-iot-publisher` 배포, IoT Core -> S3 raw 분리 적재 검증까지 완료했다.
- 2026-05-27 기준 `factory-a/b/c` data-pipeline은 실제 AWS 리소스로 end-to-end 검증됐고, `factory-a` 최신 processed `state_snapshot`은 `nodes_ready=3/3`, `pods_ready=6/6`, `pipeline_status=normal` 상태다.
- Bedrock 기반 factory별 일일 운영 보고서는 MVP 포함으로 확정했다. 구현 기준은 `docs/planning/17_llm_daily_factory_report_plan.md`이며, reporting stack은 `ap-south-1`, S3 `processed/` 입력, `reports/daily/` 출력, `infra/reporting/` 별도 Terraform root module을 따른다.
- 2026-05-20 세션에서 `factory-c` VirtualBox NAT 중복 IP로 인한 Flannel/CoreDNS 장애를 enp0s8 고정 IP와 `flannel-iface` 지정으로 해결했고, `factory-b` worker1 clock drift는 `chronyc makestep`으로 복구했다.
- `docs/issues/` 하위 마일스톤 문서를 기준으로 구현 순서를 M0~M7로 관리한다.
- 구현 책임 경계는 `docs/planning/11_delivery_ownership_flow.md`를 source of truth로 삼는다.
- 관리자 대시보드는 Tailscale 의존을 줄이기 위해 `docs/planning/07_dashboard_vpc_extension_plan.md`의 Dashboard VPC 방향을 따른다.
- AWS 인프라 작업 전 로컬 AWS CLI MFA 및 Terraform 접근 설정은 `docs/planning/08_aws_cli_mfa_terraform_access.md`를 따른다.
- AWS 리소스 비용 기준은 `docs/ops/15_aws_cost_baseline.md`를 따른다.

## 단계 계획

### Phase 0. 문서 기준선 고정

주요 작업:

- `docs/` 기준 문서 정리
- 실제 `factory-a` 상태를 README, planning, architecture, ops, specs 문서에 반영
- 오래된 로컬 저장소/NFS/구현 전 표현을 현재 GitHub/ArgoCD/구현 완료 상태로 정리

완료 조건:

- 문서와 실제 `factory-a` 상태가 충돌 없이 읽힌다.
- README는 GitHub에서 바로 읽을 수 있는 이름을 유지한다.
- `docs/issues` 하위 issue 파일은 기존 issue 이름을 유지한다.

### Phase 1. M0 `factory-a` Safe-Edge 기준선 재구성

상태: 완료

주요 산출물:

- Raspberry Pi 3노드 K3s 클러스터
- 고정 IP 기준선
- ArgoCD 설치
- GitHub repo `https://github.com/aegis-pi/safe-edge-config-main.git`
- Helm 기반 `monitoring`, `ai-apps` 배포
- InfluxDB, Grafana, Prometheus
- Longhorn 기반 PVC
- InfluxDB 1일 retention policy
- AI snapshot node-local hostPath 및 24시간 cleanup, 매일 03:00 KST purge
- AI inference result InfluxDB PVC 기반 Longhorn 저장
- 이미지 prepull DaemonSet
- LAN 제거 및 k3s-agent 중지 기반 failover/failback 실측

완료 조건:

- Safe-Edge 핵심 동작 복구
- 센서/AI/모니터링 경로 확인
- Grafana에서 센서/AI/노드 상태 확인
- worker2 장애 시 worker1 승계 확인
- worker2 복구 시 조건부 failback 확인
- 데이터 공백 분석 결과 기록

보류 항목:

- NFS/Cold Storage
- Ansible 기반 Hot/Cold tiering
- 클라우드 장기 보존

### Phase 2. M1 Hub 기준선 구성

선행 조건:

- Phase 1 완료
- `factory-a` 기준선 문서와 GitOps repo 정합성 확인
- 기존 IAM 사용자, Access Key, MFA 장치, AWS 권한 준비
- `docs/planning/08_aws_cli_mfa_terraform_access.md` 기준으로 AWS CLI MFA 세션과 Terraform 접근 검증
- `docs/planning/09_m1_eks_vpc_decision_record.md` 기준으로 EKS/VPC MVP 설계값 확정

주요 작업:

- AWS CLI MFA 및 Terraform 접근 설정 검증 완료
- AWS EKS/VPC 기준선 검증 완료
- Hub namespace/LimitRange 기준선 검증 완료
- Hub ArgoCD Ansible bootstrap 기준 전환 완료
- Delivery ownership flow 확정: Terraform은 인프라, Ansible은 bootstrap/설정/소프트웨어, GitHub Actions는 CI, GitHub+ArgoCD는 CD
- Hub EKS/ArgoCD 재생성 및 active 상태 검증 후 destroy 완료
- 최소 책임 분리 완료: `infra/hub`, `scripts/ansible`, `infra/foundation`
- Dashboard VPC / public authenticated ingress 설계
- ArgoCD 설치 또는 중앙 ArgoCD 운영 기준 정리
- S3 버킷 및 경로 파티셔닝 설계
- IoT Core Thing / 인증서 / Policy / K3s Secret 생성 완료
- IoT Rule -> S3 raw 적재 검증 완료
- `risk/risk-normalizer` IRSA S3 read/write 권한 검증 완료
- AMP Workspace 생성 완료
- `observability/prometheus-agent` IRSA AMP remote_write 권한 검증 완료
- Hub Prometheus Agent 설치 및 AMP Query API 메트릭 수신 검증 완료
- 내부 Grafana 설치 및 AMP datasource query 검증 완료
- AWS Hub 비용 기준 문서화 완료
- latest status 저장소 후보 결정
- `runtime-config.yaml` 구조 초안
- `runtime-config.yaml` 구조 초안

완료 조건:

- Hub 자체가 독립적으로 배치되어 있음
- Spoke 연결을 받을 준비가 완료됨

ArgoCD 접근 운영 기준:

- 현재 단계에서는 사용자 로컬 PC에서 EKS kubeconfig를 설정한 뒤 `kubectl port-forward`로 ArgoCD UI에 접근한다.
- `argocd-server`는 `ClusterIP`로 유지하고 public `LoadBalancer`는 만들지 않는다.
- UI는 상태 확인, diff 확인, 수동 sync 같은 검증 용도로 사용한다.
- 반복 적용해야 하는 ArgoCD 설정은 UI 클릭에 의존하지 않고 Git/YAML/ApplicationSet으로 코드화한다.
- M2에서 Tailscale을 붙일 때 ArgoCD 접근 경로도 함께 정리한다.
- Tailscale 적용 후에는 EKS API endpoint public CIDR `0.0.0.0/0`를 더 좁힌다.

ArgoCD 재생성 자동화 기준:

- `scripts/ansible`에 Terraform output 기반 dynamic inventory와 Hub ArgoCD bootstrap playbook을 추가했다.
- ArgoCD chart version은 현재 검증된 `argo-cd-9.5.11`, app version은 `v3.3.9`를 기준으로 고정한다.
- `scripts/ansible/files/argocd-values.yaml`을 두고 `server.service.type=ClusterIP`를 명시한다.
- `infra/hub terraform apply` 후 `ansible-playbook` 실행으로 namespace, LimitRange, ArgoCD Helm release가 재생성되게 한다.
- Spoke ApplicationSet은 `aegis-pi-gitops` 저장소와 `hub_aegis_spoke_applicationset_bootstrap.yml`로 코드화한다. 기본 repo URL은 `https://github.com/aegis-pi/aegis-pi-gitops.git`이고, 기본 scope는 `envs/factory-a/values.yaml`이다.
- 포트포워딩은 Terraform 리소스로 관리하지 않는다. 로컬에서 실행하는 운영 스크립트로 제공한다.
- 포트포워딩 스크립트는 `scripts/ops/argocd-port-forward.sh`에 두고, 내부에서 `aws eks update-kubeconfig`, `kubectl -n argocd wait`, `kubectl -n argocd port-forward service/argocd-server 8080:443` 순서로 실행하게 한다.
- 초기 admin 비밀번호 조회는 별도 명령 또는 `--print-password` 옵션처럼 명시적인 경우에만 수행하고, 문서나 로그에 저장하지 않는다.

Hub 생성 순서:

- `scripts/build/build-hub.sh`를 실행해 VPC, NAT Gateway, EKS, node group을 생성한다.
- 같은 실행 흐름에서 `aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS`로 로컬 kubeconfig를 갱신한다.
- Ansible `hub_argocd_bootstrap.yml`이 namespace, LimitRange, ArgoCD Helm release를 생성한다.
- Ansible `hub_tailscale_bootstrap.yml`이 Tailscale Operator, factory egress Service, ArgoCD/Grafana Tailscale UI Service, ArgoCD cluster Secret을 생성/검증한다.
- ArgoCD UI가 필요하면 `scripts/build/build-admin-ui-after-ns.sh`로 HTTPS Ingress를 활성화하거나 `scripts/ops/argocd-port-forward.sh`를 실행해 로컬 `https://127.0.0.1:8080`으로 접근한다.
- IoT Secret 준비 후 `scripts/build/build-iot-factory-a.sh`가 `hub_aegis_spoke_applicationset_bootstrap.yml`과 verify를 실행해 Spoke workload 배포를 시작한다.
- 전체 검증은 `scripts/build/verify-complete.sh`로 수행한다.

### Phase 3. M2 Mesh VPN + Hub-Spoke 연결

선행 조건:

- Phase 2 완료
- `factory-a` master API 접근 정책 확정

주요 작업:

- Tailscale 계정 및 Spoke별 키 정책: 완료
- `factory-a` master Tailscale 참여: 완료
- EKS Hub Tailscale 참여: 완료
- ArgoCD/Grafana UI 접근 경로를 Tailscale 기반 private access로 검증 완료
- kubeconfig Tailscale IP 기반 구성: 완료
- ArgoCD `factory-a` 등록: 완료
- Hub -> `factory-a` Sync 검증: 완료
- Tailscale egress 장애/복구 검증: 완료
- EKS API endpoint public CIDR 축소: 설계 마무리 후 재검토로 보류

완료 조건:

- Hub에서 `factory-a` Spoke API 접근 가능
- ArgoCD가 `factory-a`에 테스트 배포 가능
- ArgoCD UI를 public LoadBalancer 없이 접근 가능
- EKS API endpoint CIDR 축소는 M2 완료 조건에서 제외하고 운영 보안 강화/설계 마무리 후 재검토한다.

### Phase 4. M3 배포 파이프라인 구성

선행 조건:

- Phase 3 완료
- 기준 앱과 공통 차트 구조 준비

주요 작업:

- Helm base + 공장별 values 구조
- ECR 저장소 및 이미지 태그 전략
- GitHub Actions 기반 CI, 이미지 빌드/테스트/ECR push
- GitHub repository와 ArgoCD ApplicationSet 기반 CD
- manifest 갱신 워크플로우는 실제 Edge data-plane 이미지가 확정된 뒤 재개
- 배포 검증 워크플로우는 M4의 `factory-a-log-adapter`, `edge-iot-publisher` 기준으로 재개

완료 조건:

- 현재 완료 범위: ECR, GitHub Actions build/push, Hub ArgoCD ApplicationSet, `factory-a` 보수적 rollout/rollback 검증, 실제 data-plane image 기준 GitOps chart 적용
- 후속 완료 범위: manifest/value 자동 갱신 workflow와 최종 CI/CD hardening
- 이미지 prepull 정책과 최신 태그 유지 방식 정리

### Phase 5. M4 데이터 플레인 - `factory-a` 단일 Spoke 기준

선행 조건:

- Phase 3 완료
- M3 현재 완료 범위인 ECR/GitHub Actions/Hub ArgoCD ApplicationSet 검증 완료
- M3 Issue 6~8은 M4 image 확정 후 재개 대상이지만, 현재 수동 값 갱신과 ApplicationSet 배포 경로는 검증됐다.

주요 작업:

- Raw/Processed 데이터 계약 확정
- `factory-a-log-adapter` 구현: `factory-a`의 실제 raw/log/status 데이터를 표준 JSON으로 변환
- local spool/outbox 계약 확정
- `edge-iot-publisher` 구현: canonical JSON을 AWS IoT Core로 MQTT publish
- 두 컴포넌트를 이미지화하고 Hub ArgoCD가 `factory-a` K3s에 배포
- IoT Core -> S3 raw object 적재 검증
- Lambda data processor와 DynamoDB/S3 processed 연계
- `pipeline_status` 집계 및 latest status 저장소 반영

완료 조건:

- `factory-a` 실제 데이터가 canonical JSON으로 변환됨
- IoT Core 수신 메시지와 S3 raw object body가 같은 계약을 만족함
- S3 raw prefix가 `factory_id/source_type/yyyy/mm/dd` 기준으로 확인됨
- Hub ArgoCD가 두 data-plane workload를 `factory-a` K3s에 배포/복구할 수 있음
- worker2 장애 시 data-plane workload가 worker1로 재스케줄되고 pipeline 관련 상태가 계속 송신
- Lambda data processor가 DynamoDB LATEST/HISTORY#STATE와 S3 processed를 갱신함
- `pipeline_status`가 `factory-a/b/c` LATEST와 processed state_snapshot에 반영됨

### Phase 6. M5 VM Spoke 확장 - `factory-b`, `factory-c`

선행 조건:

- Phase 4, 5 완료
- 운영형 Spoke 배포 및 데이터 플레인 기준선 확인

주요 작업:

- `factory-b` K3s
- `factory-c` K3s
- 두 VM의 Tailscale 참여
- ApplicationSet 확장
- `dummy-data-generator` 구현 / 배포
- `factory-b/c`는 canonical JSON 형식의 가데이터를 생성하고, 공통 `edge-iot-publisher`가 IoT Core 송신을 담당
- 테스트베드형 자동 롤백 정책 적용
- 두 VM의 S3 raw 적재 확인
- `pipeline_status` 확인은 M4 Issue 7 Lambda 처리 검증으로 이관

완료 조건:

- 3개 공장이 Hub에서 독립 공장으로 배포/수집 가능
- S3 raw에서 `raw/factory-a/`, `raw/factory-b/`, `raw/factory-c/` prefix가 분리되어 적재됨
- `factory-b/c` dummy generator 중지/재시작을 통해 후속 `pipeline_status` 검증을 수행할 수 있음

### Phase 7. M6 Risk Twin + 관제 화면

선행 조건:

- Phase 5, 6 완료
- 3개 공장 데이터가 Hub에서 읽힘

주요 작업:

- Lambda data processor Risk 계산 로직 구현 - 기본 구현 완료
- `runtime-config.yaml` 적용 - 설정 파일 초안은 있으나 Lambda 연결은 후속
- 온도/습도 기준 초안 반영
- Risk Twin 출력 구조 구현
- Dashboard Web/API 또는 Grafana 관제 화면 구현 - Dashboard page/VPC는 별도 담당 범위
- Dashboard VPC에서 ALB/WAF/Auth를 통해 접근하고, DynamoDB LATEST/HISTORY#STATE와 S3 processed를 read-only로 조회 - 이 repo는 조회 대상 데이터 계약을 제공

완료 조건:

- 상태 변화 -> Risk Score -> DynamoDB/S3 processed read model 반영 확인
- Dashboard 담당 구현에서 해당 read model을 조회할 수 있는 필드 계약 확인

### Phase 7.5. MVP Daily Factory Report

선행 조건:

- Phase 5, 6 완료
- S3 `processed/`에 `factory_state`, `risk_score`, `infra_state`가 factory별로 적재됨
- `docs/planning/17_llm_daily_factory_report_plan.md` 결정값 유지

주요 작업:

- `apps/daily-report-generator/` package 생성 - 완료
- `PrepareReportWindow`, `AggregateFactoryHour`, `MergeFactoryDaily`, `GenerateFactoryReport` Lambda 구현 - 완료
- S3 processed hourly aggregation, daily merge, event severity/top N, recommended checks 구현 - 완료
- Bedrock mock 기반 `report-context.json`/`report.md` 로컬 테스트 - pytest 통과
- Bedrock output invariant validation 구현 - 기본 검증 및 Bedrock Sonnet 실호출 검토 완료
- `infra/reporting/` Terraform root module 추가 - 완료, fmt/init/validate 및 AWS apply 검증 완료
- `scripts/build/build-reporting.sh`, `scripts/destroy/destroy-reporting.sh` 추가 - 완료
- `docs/ops/24_daily_factory_report.md` 운영 기준 작성 - 완료
- `factory-b`, `report_date=2026-05-27`, `timezone=Asia/Seoul` 기준 Step Functions 수동 실행 검증 - 완료
- 검증 후 reporting stack destroy - 완료. S3 `processed/` input과 `reports/daily/` output은 보존

완료 조건:

- 최소 1개 factory의 `factory-daily-summary.json`, `report-context.json`, `report.md`, `generation-metadata.json`이 S3 `reports/daily/.../{factory_id}/`에 생성됨 - `factory-b` 기준 완료
- Bedrock에는 S3 raw 원본 전체가 아니라 `report-context.json`만 전달됨
- factory ID, report date, 핵심 수치 invariant validation이 수행됨
- 한 factory의 보고서 생성 실패가 다른 factory의 생성을 막지 않음

### Phase 8. M7 통합 검증 및 문서 보정

선행 조건:

- Phase 1~7 완료

주요 작업:

- 운영형 시나리오 검증
- 테스트베드형 시나리오 검증
- Failover 검증
- 롤백 검증
- `docs/ops/03_test_checklist.md` 보정
- `docs/` 및 `configs/` 기준 문서 최종 갱신

완료 조건:

- 문서와 실제 구현 상태가 일치
- MVP 완료 선언 가능

## 단계별 선행 관계 요약

| 단계 | 현재 상태 | 핵심 산출물 |
| --- | --- | --- |
| Phase 0 | 완료 | 기준 문서 |
| Phase 1 (M0) | 완료 | `factory-a` Safe-Edge 기준선 |
| Phase 2 (M1) | 핵심 완료, Issue 0~10/12 완료, Issue 11 보류 | Hub 핵심 서비스 |
| Phase 3 (M2) | 완료, Issue 1~6 완료 | Mesh 기반 `factory-a` 연결 |
| Phase 4 (M3) | Issue 1~5 완료, Issue 6~8 보류 | ECR/GitHub Actions/Hub ArgoCD 배포 기준선 |
| Phase 5 (M4) | 완료, Issue 1~8 완료 | `factory-a` adapter/publisher, Lambda data processor, DynamoDB/S3 processed |
| Phase 6 (M5) | 완료 | VM Spoke 확장, dummy generator, S3 raw 수집 |
| Phase 7 (M6) | 진행 중 | 기본 Risk 계산 완료. 다음은 runtime-config 연결, Risk Twin read model 고정. Dashboard page/VPC는 별도 담당 범위 |
| Phase 7.5 | MVP 검증 완료 | Bedrock 기반 factory별 일일 운영 보고서. 로컬 테스트, Bedrock 실호출, AWS 배포, `factory-b` Step Functions 수동 실행, S3 산출물 검증 완료. reporting stack은 검증 후 destroy |
| Phase 8 (M7) | 후속 | 통합 검증 + 문서 보정 |

## 구현 중 테스트로 결정할 항목

- Hub-Spoke 연결 지연
- IoT Core -> S3 적재 지연
- Risk Score 가중치
- source_type별 지연 기준
- dummy data generator 시나리오 값
- `pipeline_status` 주기 집계 간격
- 배포 지연 시간 수치
- null 허용 정책 세부값

## 현재 실측 완료 항목

- worker2 LAN 제거 failover/failback
- worker2 k3s-agent 중지 failover/failback
- LAN 제거 테스트 1초/10초 bucket 데이터 공백
- 이미지 prepull 적용 후 failover 준비 상태
- InfluxDB 1일 retention policy
- AI snapshot 24시간 cleanup 및 매일 03:00 KST purge
