# Hub Run Commands

상태: source of truth
기준일: 2026-05-06

## 기본 실행

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-all.sh
scripts/build/build-hub.sh
scripts/ops/argocd-initial-password.sh
scripts/ops/argocd-port-forward.sh
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
scripts/build/build-all.sh --admin-ui
```

Hub만 다시 적용할 때는 아래처럼 실행한다.

```bash
ADMIN_UI_INGRESS_ENABLED=true scripts/build/build-hub.sh
```

상세 절차는 `docs/ops/21_hub_admin_ui_ingress.md`를 따른다.

## 비용 절감 삭제

장시간 사용하지 않을 때는 Hub EKS/VPC/NAT Gateway/node group을 먼저 내린다.

```bash
scripts/destroy/destroy-hub.sh
```

## 전체 삭제

`build-all.sh`의 전체 생성 범위에 대응해 IoT factory-a, Hub, foundation까지 모두 삭제하려면 `destroy-all.sh`를 실행한다.

```bash
scripts/destroy/destroy-all.sh
```

foundation을 보존하고 Hub 비용만 줄이려면 `scripts/destroy/destroy-hub.sh`를 사용한다. 자세한 삭제 범위와 순서는 `scripts/destroy/README.md`를 따른다.
