# Hub Run Commands

상태: source of truth
기준일: 2026-06-04

## Hub-only 재시작 실행 순서

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh [MFA_OTP]
scripts/build/build-admin-ui-after-ns.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-a.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-b.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-c.sh [MFA_OTP]
```

현재 Hub-only 데이터 수집 유지 표준 순서는 Hub -> Admin UI -> factory별 Spoke Hub-only reconnect다. Hub만 삭제/재생성한 경우 IoT Core Thing/certificate, Spoke K3s Secret, factory-b/c dummy generator, data-pipeline, ECS Fargate backend는 다시 만들거나 재시작하지 않는다.

data-pipeline은 Hub/Spoke registration과 별도 생명주기다. `scripts/build/build-data-pipe.sh`는 IoT Rule, DataProcessor, GraphAggregator5m, CloudInfraFast/SlowCollector, RiskAlertDispatcher, S3 processed alert trigger, Slack webhook secret metadata를 생성/갱신한다. Slack webhook URL 값은 로컬 `.secrets/` 파일에서 Secrets Manager로 주입하며 명령 출력이나 repo에 남기지 않는다.

개발 중 데이터 수집을 계속 유지하면서 비용만 줄이는 경우에는 아래 Hub-only reconnect 절차를 우선 사용한다.

```bash
# 퇴근 시: data-pipeline과 Spoke publisher는 유지하고 Hub만 내림
scripts/destroy/destroy-hub.sh [MFA_OTP]

# 출근 시: Hub infra, SlowCollector EKS access binding, Hub platform 복구
scripts/build/build-hub.sh [MFA_OTP]

# Admin UI HTTPS Ingress/ALB 복구
scripts/build/build-admin-ui-after-ns.sh [MFA_OTP]

# 기존 Spoke pod를 건드리지 않고 Hub ArgoCD/ApplicationSet 제어 경로만 재연결
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-a.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-b.sh [MFA_OTP]
HUB_ONLY_RECONNECT=true scripts/build/register-spoke-factory-c.sh [MFA_OTP]

# 재연결 전후 publisher 중복/rollout 안전성 확인
scripts/ops/check-spoke-publisher-safety.sh
```

`HUB_ONLY_RECONNECT=true`는 `SYNC_SPOKE_APP=false`, `REFRESH_SPOKE_ECR_PULL_SECRET=false`, `RESTART_SPOKE_AFTER_ECR_SECRET_REFRESH=false`를 기본값으로 둔다. 이 모드는 Hub 재생성 후 새 ArgoCD가 기존 Spoke workload를 불필요하게 sync/restart하지 않게 하기 위한 개발용 안전 모드다.

GitOps 변경을 실제로 반영해야 할 때만 명시적으로 sync를 켠다.

```bash
HUB_ONLY_RECONNECT=true SYNC_SPOKE_APP=true scripts/build/register-spoke-factory-b.sh [MFA_OTP]
```

`build-hub.sh`는 Hub AWS infra를 올린 직후 유지 중인 CloudInfraSlowCollector의 EKS access entry와 `AmazonEKSAdminViewPolicy` association을 자동 복구하고, Hub Kubernetes platform을 설치한다. 자동 reconcile은 data-pipeline Terraform state와 SlowCollector IAM role이 모두 존재할 때 실행된다.

`reconcile-data-pipe-eks-access.sh`는 ECS Fargate backend와 관계없다. ECS backend 상태는 유지 중인 CloudInfraFastCollector가 ECS cluster/service 이름으로 `DescribeServices`를 호출하고, ALB 상태는 2026-06-04 AWS 배포본 기준 `ALB_TARGET_GROUP_NAME` 이름으로 Target Group을 조회한다. AWS resource tag 탐색은 사용하지 않는다.

`build-admin-ui-after-ns.sh`는 Gabia NS 위임 이후 ACM certificate가 `ISSUED`가 될 때까지 기다린 뒤 ArgoCD/Grafana HTTPS Ingress를 활성화한다.

`connect-hub-tailscale-ui.sh`는 Tailnet 안에서 ArgoCD/Grafana UI에 직접 접근해야 할 때만 실행한다. ALB/Admin UI HTTPS를 쓰는 개발 흐름에서는 필수가 아니다.

`build-iot-factory-a.sh`는 `factory-a` IoT Thing/Policy/certificate와 K3s Secret을 새로 준비해야 할 때 사용한다. Hub-only 재시작에서는 `register-spoke-factory-a.sh`를 사용한다.

`register-spoke-factory-a/b/c.sh`는 기존 IoT Secret을 유지하고 해당 factory의 Hub Tailscale egress, ArgoCD cluster Secret과 ApplicationSet repo 연결을 복구한다. `HUB_ONLY_RECONNECT=true`에서는 기존 Spoke workload 보호를 위해 Application sync/wait와 ECR pull secret refresh/restart를 기본 생략한다.

`manage-dummy-generators.sh start factory-b/c`는 VM worker의 local dummy generator만 켠다. IoT publish는 각 Spoke K3s에 배포된 `edge-iot-publisher`가 담당한다.

## 최종 검증

3단계를 모두 실행한 뒤 전체 설정을 확인한다.

```bash
scripts/build/verify-complete.sh
```

검증 범위:

```text
Hub: ArgoCD, legacy Prometheus Agent cleanup, Grafana, AWS Load Balancer Controller, Admin UI Ingress, Hub-Spoke Tailscale, Spoke ApplicationSet
AWS IoT: Thing, Policy, certificate ACTIVE, attachment
factory-a K3s: IoT Secret, edge-iot-publisher rollout, factory-a-log-adapter rollout
factory-b/c K3s: cluster Secret, Application 생성, hostPath data-plane 전환 후 publisher rollout
```

## Admin UI HTTPS 준비

Hub build는 foundation output을 통해 Gabia 위임용 Route53 NS 파일을 자동 갱신한다. 일반적인 Hub-only destroy/build에서는 Route53 Hosted Zone과 ACM certificate가 foundation에 남으므로 가비아 네임서버를 다시 바꿀 필요가 없다.

```bash
cat secret/admin-ui-nameservers.txt
```

최초 1회 `minsoo-tech.cloud`를 Gabia에서 위 파일의 NS 4개로 위임한 뒤 ACM certificate가 `ISSUED`가 되면 Admin UI Ingress를 활성화한다. 이후 foundation Hosted Zone을 destroy/recreate한 경우에만 가비아 NS를 다시 설정한다.

```bash
aws acm describe-certificate \
  --region ap-south-1 \
  --certificate-arn "$(terraform -chdir=infra/hub output -raw admin_ui_certificate_arn)" \
  --query 'Certificate.Status' \
  --output text
```

```bash
scripts/build/build-admin-ui-after-ns.sh
```

Hub와 Admin UI Ingress까지 한 번에 다시 적용해야 하는 예외 상황에서는 아래처럼 실행할 수 있다.

```bash
ADMIN_UI_INGRESS_ENABLED=true scripts/build/build-hub.sh
```

상세 절차는 `docs/ops/21_hub_admin_ui_ingress.md`를 따른다.

## 비용 절감 삭제

데이터 수집까지 멈추는 경우에는 dummy generator를 먼저 정지한 뒤 Hub를 내린다.

```bash
scripts/destroy/stop-dummy-generators.sh
scripts/destroy/destroy-hub.sh
```

`stop-dummy-generators.sh`는 Hub가 내려간 뒤에도 factory-b/c worker outbox가 계속 쌓이는 것을 막는다. legacy local publisher unit이 설치돼 있으면 함께 정지하지만, 현재 표준 publish 경로는 K3s `edge-iot-publisher`다. `destroy-hub.sh`는 Hub EKS/VPC/NAT Gateway/node group과 EKS 내부 ArgoCD/Tailscale/ApplicationSet 리소스를 제거한다. Foundation S3/ECR/DynamoDB, IoT 리소스와 Spoke K3s Secret은 별도 삭제 대상이다.

데이터를 계속 쌓는 개발 모드에서는 `stop-dummy-generators.sh`, `destroy-data-pipe.sh`, `build-data-pipe.sh`를 실행하지 않는다. Hub ArgoCD self-heal은 멈추지만 기존 Spoke K3s `edge-iot-publisher`, factory-b/c dummy generator, IoT Core, data-pipeline과 ECS Fargate backend는 계속 동작한다.

## 전체 삭제

`build-all.sh`의 전체 생성 범위에 대응해 IoT factory-a, Hub, foundation까지 모두 삭제하려면 `destroy-all.sh`를 실행한다.

```bash
scripts/destroy/destroy-all.sh
```

`DESTROY_IOT=true` 기본값에서는 AWS MFA 전에 `factory-a` K3s IoT Secret을 먼저 삭제하므로 OpenSSH 비밀번호 프롬프트가 먼저 나올 수 있다. Secret 삭제는 `--ignore-not-found=true`라 이미 삭제된 상태에서도 계속 진행된다.

Terraform destroy 확인 프롬프트까지 자동 승인하려면 아래처럼 실행한다.

```bash
TF_CLI_ARGS_destroy=-auto-approve scripts/destroy/destroy-all.sh
```

foundation을 보존하고 Hub 비용만 줄이려면 `scripts/destroy/destroy-hub.sh`를 사용한다. 자세한 삭제 범위와 순서는 `scripts/destroy/README.md`를 따른다.
