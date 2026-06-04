# Hub Admin UI HTTPS Ingress

상태: source of truth
기준일: 2026-05-28

## 목적

이 문서는 Hub EKS 안의 ArgoCD와 Grafana를 관리자용 HTTPS 경로로 노출하는 절차를 정리한다.

MVP 기준은 Public ALB 1개, host 기반 Ingress, ACM public certificate, Route53 DNS, ArgoCD/Grafana 자체 로그인이다. WAF, Cognito, 외부 OIDC/SSO는 M1 Issue 11 운영 보안 강화 백로그로 분리한다.

## 책임 경계

| 영역 | 담당 | 내용 |
| --- | --- | --- |
| Terraform `infra/foundation` | 영속 AWS 인프라 | Route53 Hosted Zone, ACM certificate, ACM DNS validation record |
| Terraform `infra/hub` | Hub AWS 인프라 | AWS Load Balancer Controller IRSA, EKS/VPC |
| Ansible `scripts/ansible` | EKS bootstrap | AWS Load Balancer Controller Helm release, Admin UI Ingress apply/verify/cleanup |
| AWS Load Balancer Controller | Kubernetes -> AWS 연동 | Ingress를 보고 ALB, listener, target group, security group 생성/삭제 |
| Gabia | 도메인 등록기관 | `minsoo-tech.cloud` 네임서버를 Route53 NS로 위임 |

ArgoCD와 Grafana Kubernetes Service는 계속 `ClusterIP`로 유지한다. 외부 진입점은 ALB Ingress뿐이다.

## 현재 상태

```text
Domain: minsoo-tech.cloud
ArgoCD host: argocd.minsoo-tech.cloud
Grafana host: grafana.minsoo-tech.cloud
Route53 Hosted Zone: Z04285032XLZT6GPVQEE4 (foundation-owned)
ACM certificate: arn:aws:acm:ap-south-1:611058323802:certificate/528e603a-9109-4427-bfea-c20f3a619be6
ACM status: ISSUED
Admin Ingress default: disabled
Current ALB: created only when Admin UI Ingress is enabled
```

Route53 name servers:

```text
ns-1418.awsdns-49.org
ns-1719.awsdns-22.co.uk
ns-191.awsdns-23.com
ns-665.awsdns-19.net
```

`build-hub.sh`는 foundation output을 통해 현재 Route53 Hosted Zone의 NS 목록을 아래 파일에 다시 쓴다. 일반적인 Hub destroy/build에서는 Hosted Zone이 유지되므로 Gabia NS를 다시 바꿀 필요가 없다. `DESTROY_FOUNDATION=true`로 foundation Hosted Zone을 삭제하고 재생성한 경우에만 이 파일을 확인해 Gabia NS를 다시 설정한다.

```text
secret/admin-ui-nameservers.txt
```

수동 갱신이 필요하면 아래 스크립트를 실행한다.

```bash
scripts/ops/admin-ui-nameservers.sh
```

## 활성화 절차

1. 최초 1회만 Gabia 관리 화면에서 `minsoo-tech.cloud`의 네임서버를 `secret/admin-ui-nameservers.txt`에 적힌 Route53 NS 4개로 변경한다.
2. DNS 전파 후 ACM certificate가 `ISSUED`인지 확인한다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
aws acm describe-certificate \
  --region ap-south-1 \
  --certificate-arn "$(terraform -chdir=infra/hub output -raw admin_ui_certificate_arn)" \
  --query 'Certificate.Status' \
  --output text
```

3. 인증서가 `ISSUED`가 된 뒤 Admin Ingress만 별도로 활성화한다.

```bash
scripts/build/build-admin-ui-after-ns.sh
```

이미 NS 위임과 ACM 발급이 끝난 상태에서 Hub 전체를 다시 적용해야 할 때만 아래처럼 실행한다.

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

2026-05-19 기준 Admin Ingress는 `build-admin-ui-after-ns.sh`로 ACM `ISSUED` 확인 후 활성화한다. 검증 기준은 아래와 같다.

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

이 기본값에서는 foundation이 Route53/ACM을 보존하고, `build-hub.sh`가 IRSA와 AWS Load Balancer Controller까지 준비하지만 Admin Ingress와 ALB는 만들지 않는다. Gabia NS 위임 전에도 build가 실패하지 않고, 불필요한 ALB 비용도 발생하지 않는다.

## 삭제 기준

`scripts/destroy/destroy-hub.sh`는 Terraform destroy 전에 `hub_admin_ingress_cleanup.yml`을 먼저 실행한다. Admin Ingress가 켜져 있었다면 이 단계에서 Route53 CNAME, Kubernetes Ingress, AWS Load Balancer Controller가 만든 ALB/TargetGroup/SecurityGroup 삭제를 기다린다.

이후 Terraform destroy가 LBC IRSA와 EKS/VPC 리소스를 삭제한다. Route53 Hosted Zone과 ACM certificate는 foundation에 보존된다.

Admin UI Ingress는 `alb.ingress.kubernetes.io/load-balancer-name: aegis-admin-ui` 고정 이름을 사용한다. Hub-only 반복 생성/삭제에서는 이 이름을 변경하지 않는 것을 운영 기준으로 한다. ECS Fargate backend처럼 ECS service의 Target Group ARN을 사용하는 구조가 아니며, Admin UI ALB는 Kubernetes Ingress와 AWS Load Balancer Controller가 관리한다.

## 비용 기준

Admin Ingress를 활성화하면 Public ALB 1개, ALB LCU, internet-facing ALB public IPv4 비용이 발생한다. ACM public certificate는 비용이 없고, AWS Load Balancer Controller pod는 기존 EKS node 위에서 실행되므로 별도 고정 비용이 없다.

Admin Ingress를 비활성화하거나 Hub를 destroy하면 ALB 관련 비용을 줄일 수 있다. 최신 계산 기준은 `docs/ops/15_aws_cost_baseline.md`를 따른다.
