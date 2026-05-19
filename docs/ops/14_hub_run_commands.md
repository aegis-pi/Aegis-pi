# Hub Run Commands

상태: source of truth
기준일: 2026-05-19

## 표준 3단계 실행

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-hub.sh
scripts/build/build-admin-ui-after-ns.sh
scripts/build/build-iot-factory-a.sh
```

현재 표준 순서는 Hub -> Admin UI -> IoT/Spoke deploy다.

`build-hub.sh`는 Hub AWS 인프라와 Hub Kubernetes platform을 올리고, Tailscale을 통해 ArgoCD가 `factory-a` K3s에 접근할 수 있도록 cluster Secret까지 등록한다. 단, Spoke workload ApplicationSet 배포는 기본값에서 실행하지 않는다.

`build-admin-ui-after-ns.sh`는 Gabia NS 위임 이후 ACM certificate가 `ISSUED`가 될 때까지 기다린 뒤 ArgoCD/Grafana HTTPS Ingress를 활성화한다.

`build-iot-factory-a.sh`는 IoT Thing/Policy/certificate와 K3s Secret을 준비한 뒤 ArgoCD ApplicationSet을 적용해 `factory-a` data-plane workload 배포를 시작한다.

## 최종 검증

3단계를 모두 실행한 뒤 전체 설정을 확인한다.

```bash
scripts/build/verify-complete.sh
```

검증 범위:

```text
Hub: ArgoCD, Prometheus Agent, Grafana, AWS Load Balancer Controller, Admin UI Ingress, Tailscale, Spoke ApplicationSet
AWS IoT: Thing, Policy, certificate ACTIVE, attachment
factory-a K3s: IoT Secret, edge-iot-publisher rollout, factory-a-log-adapter rollout
```

## Admin UI HTTPS 준비

Hub build는 Terraform apply 직후 Gabia 위임용 Route53 NS 파일을 자동 갱신한다.

```bash
cat secret/admin-ui-nameservers.txt
```

`minsoo-tech.cloud`를 Gabia에서 위 파일의 NS 4개로 위임한 뒤 ACM certificate가 `ISSUED`가 되면 Admin UI Ingress를 활성화한다.

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

장시간 사용하지 않을 때는 Hub EKS/VPC/NAT Gateway/node group을 먼저 내린다.

```bash
scripts/destroy/destroy-hub.sh
```

`destroy-hub.sh`는 Hub EKS/VPC/NAT Gateway/node group과 EKS 내부 ArgoCD/Tailscale/ApplicationSet 리소스를 제거한다. Foundation S3/AMP/ECR/IoT 리소스와 `factory-a` K3s Secret은 별도 삭제 대상이다.

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
