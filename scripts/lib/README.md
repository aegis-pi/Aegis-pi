# scripts/lib

상태: source of truth
기준일: 2026-05-21

## 목적

`scripts/build/`, `scripts/destroy/`, `scripts/ops/` 스크립트가 공통으로 source하는 Shell 함수 라이브러리다.
직접 실행하지 않는다. 진입점은 각 하위 디렉터리의 스크립트다.

## 파일

| 파일 | 역할 |
| --- | --- |
| `aws-mfa.sh` | AWS MFA 세션 획득 및 검증. `aegis_ensure_aws_mfa [OTP]` 함수 제공. OTP를 인수로 받으면 자동 사용, 없으면 대화형 입력 |
| `config.sh` | `REPO_ROOT`, `AEGIS_REGION` 등 공통 환경변수 설정. 모든 스크립트가 가장 먼저 source한다 |
| `terraform.sh` | Terraform init/plan/apply/destroy 래퍼. `aegis_terraform_apply_root <dir>`, `aegis_terraform_destroy_root <dir>` 함수 제공 |

## 사용법

각 스크립트 상단에서 source한다.

```bash
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${REPO_ROOT}/scripts/lib/aws-mfa.sh"
source "${REPO_ROOT}/scripts/lib/config.sh"
source "${REPO_ROOT}/scripts/lib/terraform.sh"
```

## 주의

- AWS 자격증명이나 비밀값은 이 파일에 저장하지 않는다.
- 함수 변경 시 `scripts/build/`, `scripts/destroy/`의 모든 스크립트에 영향을 준다.
