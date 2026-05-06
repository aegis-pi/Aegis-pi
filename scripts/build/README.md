# Build Scripts

상태: source of truth
기준일: 2026-05-06

## 목적

이 디렉터리는 Aegis-Pi 리소스 생성 진입점을 순서대로 관리한다.

새 리소스를 추가하거나 기존 리소스 생성 방식이 바뀌면 이 디렉터리의 스크립트와 문서를 함께 업데이트한다.

## 생성 순서

```text
1. foundation
   - infra/foundation Terraform apply
   - S3 data bucket, AMP Workspace, IoT Rule 같은 영속 리소스

2. hub
   - infra/hub Terraform apply
   - EKS, VPC, node group
   - Ansible Hub bootstrap
   - ArgoCD install/verify
   - Prometheus Agent install/verify and AMP remote_write
   - internal Grafana install/verify and AMP datasource query
   - AWS Load Balancer Controller install/verify
   - Admin UI Route53 name server file generation
   - Admin UI HTTPS Ingress prepare/verify, disabled by default until ACM is issued

3. iot factory-a
   - IoT Thing / Policy / certificate 등록
   - local secret/iot/factory-a 출력
   - K3s Secret 등록
```

## 파일

| 파일 | 내용 |
| --- | --- |
| `build-all.sh` | 전체 생성 순서 실행 |
| `build-foundation.sh` | `infra/foundation` Terraform apply |
| `build-hub.sh` | `infra/hub` Terraform apply 후 Ansible bootstrap |
| `build-iot-factory-a.sh` | `factory-a` IoT Thing/certificate 생성 및 K3s Secret 등록 |

## 전체 생성

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/build/build-all.sh
```

MFA OTP를 인자로 넘길 수도 있다.

```bash
scripts/build/build-all.sh <MFA_OTP>
```

Admin UI HTTPS Ingress까지 한 번에 켜려면 `--admin-ui`를 붙인다. 이 옵션은 내부적으로 `ADMIN_UI_INGRESS_ENABLED=true`를 설정한 뒤 기존 MFA/build 흐름을 그대로 사용한다.

```bash
scripts/build/build-all.sh --admin-ui
```

MFA OTP를 함께 넘길 수도 있다.

```bash
scripts/build/build-all.sh --admin-ui <MFA_OTP>
```

## 일부만 생성

Foundation만:

```bash
scripts/build/build-foundation.sh
```

Hub만:

```bash
scripts/build/build-hub.sh
```

Hub ArgoCD Helm release가 이미 `deployed` 상태이고 chart version이 같으면 `build-hub.sh`와 `build-all.sh`는 Helm upgrade를 건너뛴다. values 변경이나 강제 재적용이 필요하면 아래처럼 실행한다.

```bash
FORCE_ARGOCD_UPGRADE=true scripts/build/build-all.sh
```

AWS Load Balancer Controller도 이미 `deployed` 상태이고 chart version이 같으면 Helm upgrade를 건너뛴다. 강제 재적용이 필요하면 아래처럼 실행한다.

```bash
FORCE_AWS_LB_CONTROLLER_UPGRADE=true scripts/build/build-hub.sh
```

Admin UI HTTPS Ingress는 기본값에서 비활성화된다. `minsoo-tech.cloud`를 Gabia에서 Route53 Hosted Zone NS로 위임하고 ACM certificate가 `ISSUED`가 된 뒤에만 `build-all.sh --admin-ui` 또는 아래처럼 환경 변수 방식으로 활성화한다.

Hub build는 Terraform apply 직후 `secret/admin-ui-nameservers.txt`를 갱신한다. Gabia에 입력할 NS는 문서에 적힌 값보다 이 파일을 우선한다.

```bash
ADMIN_UI_INGRESS_ENABLED=true scripts/build/build-hub.sh
```

IoT `factory-a`만:

```bash
scripts/build/build-iot-factory-a.sh
```

전체 생성에서 특정 단계를 건너뛰려면 환경 변수를 사용한다.

```bash
BUILD_HUB=false scripts/build/build-all.sh
```

```bash
BUILD_FOUNDATION=false BUILD_HUB=false scripts/build/build-all.sh
```

## 주의

- `build-all.sh`는 Hub EKS와 NAT Gateway를 생성할 수 있어 비용이 발생한다.
- Admin UI Ingress를 활성화하면 Public ALB와 ALB LCU, public IPv4 비용이 추가된다.
- 전체 생성 범위에 대응하는 전체 삭제는 `scripts/destroy/destroy-all.sh`로 실행한다.
- ArgoCD UI port-forward는 장기 실행 프로세스이므로 전체 build에는 포함하지 않는다.
- UI 접속은 별도로 `scripts/ops/argocd-port-forward.sh`를 실행한다.
- 인증서/private key 출력은 `secret/`에만 저장되고 Git에는 들어가지 않는다.
