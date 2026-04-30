# Hub Platform Layer

이 Terraform root는 이미 생성된 Hub EKS 클러스터 위의 Kubernetes 리소스를 관리한다.

현재 최소 분리 기준에서는 namespace와 기본 LimitRange만 이곳에서 만든다. ArgoCD, Prometheus, Grafana처럼 클러스터 안에 배포되는 플랫폼 컴포넌트도 이후 이 root에서 관리한다.

## 책임 범위

```text
infra/hub       VPC, subnet, NAT Gateway, EKS cluster, node group
infra/platform  Kubernetes namespace, LimitRange, 이후 ArgoCD/관측 컴포넌트
```

`infra/platform`은 `infra/hub`에서 만든 `AEGIS-EKS` 클러스터를 AWS data source로 조회한다. 따라서 Hub EKS가 없는 상태에서는 `terraform plan`과 `terraform apply`가 실패한다.

## 적용 순서

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/hub
terraform apply
aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS

cd ../platform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

## 삭제 순서

Kubernetes 리소스가 EKS API에 의존하므로 삭제는 platform을 먼저 내리고 hub를 나중에 내린다.

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/infra/platform
terraform destroy

cd ../hub
terraform destroy
```

Hub를 먼저 destroy하면 platform state에는 리소스가 남아 있지만 EKS API가 없어져 정리가 꼬일 수 있다.
