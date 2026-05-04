# Ansible Inventory

이 디렉터리는 `factory-a` Ansible 자동화 대상과 Hub EKS dynamic inventory를 관리한다.

## 파일과 폴더

| 경로 | 내용 |
| --- | --- |
| `factory-a.ini` | `master`, `worker1`, `worker2`를 Ansible 그룹으로 정의 |
| `hub_eks_dynamic.sh` | `infra/hub` Terraform output을 읽어 `hub_eks` localhost inventory를 생성 |
| `group_vars/` | `factory_a`, `hub_eks` 그룹에 적용할 공통 변수 |

## 기준

- IP, 서비스 주소, 워크로드 이름은 변수 파일에서 관리한다.
- SSH 비밀번호는 파일에 저장하지 않고 playbook prompt로만 입력한다.
- Hub EKS bootstrap은 EC2 SSH가 아니라 AWS IAM kubeconfig와 Kubernetes API를 사용한다.
