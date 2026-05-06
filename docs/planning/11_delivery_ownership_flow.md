# Delivery Ownership Flow

상태: source of truth
기준일: 2026-05-04

## 목적

Aegis-Pi의 인프라 생성, 클러스터/소프트웨어 설정, CI, CD의 책임 경계를 고정한다.

앞으로 모든 신규 작업은 이 흐름을 먼저 확인하고, 구현 방식이 이 경계와 충돌하지 않는지 검토한 뒤 진행한다.

## 최종 기준

```text
Terraform:
  cloud infrastructure

Ansible:
  post-infrastructure bootstrap
  cluster configuration
  software installation
  operational verification

GitHub Actions:
  CI
  image build
  test
  push to registry
  manifest/value update

GitHub + ArgoCD:
  CD
  GitOps source of truth
  Application / ApplicationSet sync
  runtime deployment drift control
```

## 책임 경계

| 영역 | 도구 | 담당 |
| --- | --- | --- |
| Cloud infrastructure | Terraform | VPC, subnet, NAT Gateway, EKS, IAM, OIDC, S3, ECR, AMP, IoT Core, Dashboard VPC 같은 AWS 리소스 |
| Cluster bootstrap | Ansible | kubeconfig 갱신, namespace, LimitRange, Helm chart 설치, ArgoCD 설치, Tailscale bootstrap, 검증 |
| Software configuration | Ansible | 클러스터 위 초기 설정, 운영 도구 설치, Secret 주입 절차, bootstrap 후 health check |
| CI | GitHub Actions | lint, test, image build, vulnerability scan, ECR push, values/manifest update PR 또는 commit |
| CD | GitHub + ArgoCD | Git repository의 Application, ApplicationSet, Helm values를 기준으로 실제 클러스터에 sync |

## 적용 순서

```text
1. Terraform apply
   - AWS 인프라 생성
   - EKS, IAM, 네트워크, 관리형 서비스 준비

2. Ansible bootstrap
   - EKS 접근 설정
   - namespace / LimitRange / ArgoCD / 운영 소프트웨어 설치
   - 설치 결과 검증

3. GitHub Actions CI
   - 코드 변경 검증
   - 컨테이너 이미지 빌드
   - ECR push
   - Helm values 또는 manifest 갱신

4. GitHub + ArgoCD CD
   - Git 변경 감지
   - Application / ApplicationSet sync
   - Spoke 또는 Hub workload 배포
```

## 금지 및 예외 기준

- Terraform으로 Kubernetes 내부 애플리케이션 Helm release를 장기 운영하지 않는다.
- Terraform은 AWS 인프라의 source of truth로 유지한다.
- Ansible은 EKS worker node SSH를 기본으로 사용하지 않는다. EKS bootstrap은 `localhost`에서 Kubernetes API를 대상으로 실행한다.
- GitHub Actions는 운영 클러스터에 직접 `kubectl apply`를 수행하지 않는다. 예외가 필요하면 문서에 사유를 남긴다.
- ArgoCD UI 클릭으로 만든 설정은 장기 운영 기준이 아니다. 반복 적용할 설정은 Git에 남긴다.
- Secret 값, MFA OTP, Access Key, Session Token은 Git과 문서에 기록하지 않는다.

## 현재 Hub 기준

```text
Terraform:
  infra/hub
  infra/foundation

Ansible:
  scripts/ansible/inventory/hub_eks_dynamic.sh
  scripts/ansible/playbooks/hub_argocd_bootstrap.yml
  scripts/ansible/playbooks/hub_argocd_verify.yml

CI:
  .github/workflows/*  (M3에서 추가)

CD:
  GitHub repository
  ArgoCD Application / ApplicationSet  (M2/M3에서 추가)
```

## 작업 전 확인 체크

- 새 AWS 리소스인가? 그러면 Terraform으로 구현한다.
- EKS 위에 설치되는 설정/소프트웨어인가? 그러면 Ansible bootstrap 또는 ArgoCD GitOps 대상인지 먼저 나눈다.
- 빌드/테스트/이미지 push인가? 그러면 GitHub Actions로 구현한다.
- 실제 배포 상태를 유지해야 하는 애플리케이션인가? 그러면 GitHub repository와 ArgoCD CD로 관리한다.
- AWS 비용이 발생하는 리소스나 상시 실행 경로가 추가되는가? 그러면 `docs/ops/15_aws_cost_baseline.md`를 함께 갱신한다.
- 어느 영역인지 애매하면 이 문서를 먼저 업데이트하거나 decision record를 추가한다.
