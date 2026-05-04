# Destroy Scripts

상태: source of truth
기준일: 2026-05-04

## 목적

이 디렉터리는 Aegis-Pi 리소스 삭제 진입점을 순서대로 관리한다.

새 리소스를 추가하거나 기존 리소스 삭제 방식이 바뀌면 이 디렉터리의 스크립트와 문서를 함께 업데이트한다.

## 삭제 순서

```text
1. iot factory-a
   - K3s Secret 삭제
   - IoT certificate detach/delete
   - IoT Policy 삭제
   - IoT Thing 삭제

2. hub
   - infra/hub Terraform destroy
   - EKS, VPC, node group, NAT Gateway 삭제

3. foundation
   - infra/foundation Terraform destroy
   - S3 data bucket 같은 영속 리소스
   - 기본적으로 건너뜀
```

## 파일

| 파일 | 내용 |
| --- | --- |
| `destroy-all.sh` | 전체 삭제 순서 실행. foundation은 기본 제외 |
| `destroy-iot-factory-a.sh` | `factory-a` K3s Secret과 IoT 리소스 삭제 |
| `destroy-k3s-iot-secret.sh` | K3s Secret만 삭제 |
| `destroy-hub.sh` | Hub EKS/VPC 리소스 삭제 |
| `destroy-foundation.sh` | Foundation 영속 리소스 삭제. 명시 플래그 필요 |

## 기본 전체 삭제

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
scripts/destroy/destroy-all.sh
```

MFA OTP를 인자로 넘길 수도 있다.

```bash
scripts/destroy/destroy-all.sh <MFA_OTP>
```

기본 동작:

```text
DESTROY_IOT=true
DESTROY_HUB=true
DESTROY_FOUNDATION=false
```

즉, S3 data bucket 같은 영속 리소스는 기본 삭제하지 않는다.

## Foundation까지 삭제

S3 data bucket 같은 영속 리소스까지 삭제해야 할 때만 명시한다.

```bash
DESTROY_FOUNDATION=true scripts/destroy/destroy-all.sh
```

Foundation만 삭제:

```bash
DESTROY_FOUNDATION=true scripts/destroy/destroy-foundation.sh
```

## 일부만 삭제

IoT만:

```bash
scripts/destroy/destroy-iot-factory-a.sh
```

K3s Secret만:

```bash
scripts/destroy/destroy-k3s-iot-secret.sh
```

Hub만:

```bash
scripts/destroy/destroy-hub.sh
```

## 주의

- `destroy-all.sh`는 Hub EKS와 NAT Gateway를 삭제한다.
- `destroy-foundation.sh`는 S3/ECR/AMP/IoT Core 같은 영속 리소스를 삭제하는 자리다.
- Foundation 삭제는 기본 차단되어 있으며 `DESTROY_FOUNDATION=true`가 필요하다.
- CLI로 만든 IoT 리소스는 Terraform state에 없으므로 `scripts/iot/cleanup-thing.sh` 또는 이 디렉터리의 destroy 스크립트로 정리한다.
- K3s Secret은 Terraform state에 없으므로 SSH 기반 `kubectl delete secret`로 정리한다.
