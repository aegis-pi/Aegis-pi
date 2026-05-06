# Hub Admin UI HTTPS Ingress

상태: source of truth
기준일: 2026-05-06

## 목적

이 문서는 Hub EKS 안의 ArgoCD와 Grafana를 관리자용 HTTPS 경로로 노출하는 절차를 정리한다.

MVP 기준은 Public ALB 1개, host 기반 Ingress, ACM public certificate, Route53 DNS, ArgoCD/Grafana 자체 로그인이다. WAF, Cognito, 외부 OIDC/SSO는 M1 Issue 11 운영 보안 강화 백로그로 분리한다.

## 책임 경계

| 영역 | 담당 | 내용 |
| --- | --- | --- |
| Terraform `infra/hub` | AWS 인프라 | Route53 Hosted Zone, ACM certificate, ACM DNS validation record, AWS Load Balancer Controller IRSA |
| Ansible `scripts/ansible` | EKS bootstrap | AWS Load Balancer Controller Helm release, Admin UI Ingress apply/verify/cleanup |
| AWS Load Balancer Controller | Kubernetes -> AWS 연동 | Ingress를 보고 ALB, listener, target group, security group 생성/삭제 |
| Gabia | 도메인 등록기관 | `minsoo-tech.cloud` 네임서버를 Route53 NS로 위임 |

ArgoCD와 Grafana Kubernetes Service는 계속 `ClusterIP`로 유지한다. 외부 진입점은 ALB Ingress뿐이다.

## 현재 상태

```text
Domain: minsoo-tech.cloud
ArgoCD host: argocd.minsoo-tech.cloud
Grafana host: grafana.minsoo-tech.cloud
Route53 Hosted Zone: Z03975332EWIGUYGA3VRQ
ACM certificate: arn:aws:acm:ap-south-1:611058323802:certificate/3b557271-aa5a-416a-a55d-e8501e05d7be
ACM status: ISSUED
Admin Ingress default: disabled, currently enabled by explicit build
Current ALB: aegis-admin-ui-1532265527.ap-south-1.elb.amazonaws.com
```

Route53 name servers:

```text
ns-1079.awsdns-06.org
ns-1913.awsdns-47.co.uk
ns-7.awsdns-00.com
ns-872.awsdns-45.net
```

`build-hub.sh`와 `build-all.sh`는 Hub Terraform apply 직후 현재 Route53 Hosted Zone의 NS 목록을 아래 파일에 다시 쓴다. Hosted Zone을 destroy/recreate하면 NS가 바뀔 수 있으므로 Gabia에 입력하기 전에는 이 파일을 확인한다.

```text
secret/admin-ui-nameservers.txt
```

수동 갱신이 필요하면 아래 스크립트를 실행한다.

```bash
scripts/ops/admin-ui-nameservers.sh
```

## 활성화 절차

1. Gabia 관리 화면에서 `minsoo-tech.cloud`의 네임서버를 `secret/admin-ui-nameservers.txt`에 적힌 Route53 NS 4개로 변경한다.
2. DNS 전파 후 ACM certificate가 `ISSUED`인지 확인한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
aws acm describe-certificate \
  --region ap-south-1 \
  --certificate-arn "$(terraform -chdir=infra/hub output -raw admin_ui_certificate_arn)" \
  --query 'Certificate.Status' \
  --output text
```

3. 인증서가 `ISSUED`가 된 뒤 Admin Ingress를 활성화해 전체 build를 실행한다.

```bash
scripts/build/build-all.sh --admin-ui
```

Hub만 다시 적용할 때는 아래처럼 실행한다.

```bash
ADMIN_UI_INGRESS_ENABLED=true scripts/build/build-hub.sh
```

4. 생성 상태를 확인한다.

```bash
kubectl -n argocd get ingress argocd-admin
kubectl -n observability get ingress grafana-admin
aws elbv2 describe-load-balancers \
  --region ap-south-1 \
  --names aegis-admin-ui
```

5. 브라우저에서 접속한다.

```text
https://argocd.minsoo-tech.cloud
https://grafana.minsoo-tech.cloud
```

## 현재 검증 결과

2026-05-06 기준 `ADMIN_UI_INGRESS_ENABLED=true`로 Admin Ingress를 활성화했고 아래 상태를 확인했다.

```text
Shared ALB: aegis-admin-ui-1532265527.ap-south-1.elb.amazonaws.com
ArgoCD: https://argocd.minsoo-tech.cloud
Grafana: https://grafana.minsoo-tech.cloud
ACM: ISSUED
ArgoCD Service: ClusterIP
Grafana Service: ClusterIP
```

## 기본 비활성화 이유

ACM certificate가 `ISSUED`가 되기 전에는 HTTPS listener가 정상 구성될 수 없다. 그래서 `ADMIN_UI_INGRESS_ENABLED=false`를 기본값으로 둔다.

이 기본값에서는 `build-hub.sh`가 Route53, ACM, IRSA, AWS Load Balancer Controller까지 준비하지만 Admin Ingress와 ALB는 만들지 않는다. Gabia NS 위임 전에도 build가 실패하지 않고, 불필요한 ALB 비용도 발생하지 않는다.

## 삭제 기준

`scripts/destroy/destroy-hub.sh`는 Terraform destroy 전에 `hub_admin_ingress_cleanup.yml`을 먼저 실행한다. Admin Ingress가 켜져 있었다면 이 단계에서 Route53 CNAME, Kubernetes Ingress, AWS Load Balancer Controller가 만든 ALB/TargetGroup/SecurityGroup 삭제를 기다린다.

이후 Terraform destroy가 Route53 Hosted Zone, ACM certificate, LBC IRSA, EKS/VPC 리소스를 삭제한다.

## 비용 기준

현재 Admin Ingress가 활성화되어 Public ALB 1개, ALB LCU, internet-facing ALB public IPv4 비용이 발생한다. ACM public certificate는 비용이 없고, AWS Load Balancer Controller pod는 기존 EKS node 위에서 실행되므로 별도 고정 비용이 없다.

Admin Ingress를 비활성화하거나 Hub를 destroy하면 ALB 관련 비용을 줄일 수 있다. 최신 계산 기준은 `docs/ops/15_aws_cost_baseline.md`를 따른다.
