# Configs

이 디렉터리는 애플리케이션과 런타임에서 공유할 설정 파일의 기준 구조를 둔다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `runtime/` | Risk Engine, Edge Agent, Dashboard가 참조할 런타임 설정 구조 |

## 기준

- 실제 secret, certificate, private key는 이 디렉터리에 두지 않는다.
- 공장별 배포 값은 `envs/`에 두고, 런타임 공통 설정은 이 디렉터리에서 관리한다.
