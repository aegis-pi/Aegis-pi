# Environments

이 디렉터리는 Hub와 각 공장 Spoke에 적용할 환경별 배포 값을 둔다.

현재 `factory-a`에는 `charts/aegis-spoke` Helm chart에 주입하는 실제 values가 있다. `factory-b/c`는 GitOps 저장소의 factory별 values를 ApplicationSet 입력으로 쓰는 운영 흐름이며, 이 repo의 하위 README는 각 테스트베드 역할과 외부 GitOps 값 기준을 설명한다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `hub/` | AWS EKS Hub 환경 설명. 실제 Hub 생성 값은 `infra/hub` Terraform 변수와 `scripts/ansible/inventory/group_vars/hub_eks.yml`을 기준으로 한다 |
| `factory-a/` | 운영형 Raspberry Pi Spoke Helm values. `factory-a-log-adapter`와 `edge-iot-publisher` 이미지/IoT Secret/outbox 기준을 둔다 |
| `factory-b/` | Mac mini VM 테스트베드 Spoke 설명. 표준 values는 GitOps repo ApplicationSet 입력을 따른다 |
| `factory-c/` | Windows VM 테스트베드 Spoke 설명. 표준 values는 GitOps repo ApplicationSet 입력을 따른다 |

## 기준

- 공통 배포 템플릿은 `charts/`에 둔다.
- 환경별 차이는 이 디렉터리의 values로 분리한다.
- Hub ArgoCD ApplicationSet은 `scripts/ansible/templates/aegis-spoke-applicationset.yaml.j2`와 `scripts/ansible/inventory/group_vars/hub_eks.yml`의 `gitops_applicationset_values_file_glob` 기준으로 factory별 values를 찾는다.
- secret, private key, certificate 원문은 이 디렉터리에 두지 않는다.
