# Environments

이 디렉터리는 Hub와 각 공장 Spoke에 적용할 환경별 배포 값을 둔다.

현재는 README 중심의 placeholder이며, M3 이후 Helm values와 ApplicationSet 입력값이 추가될 예정이다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `hub/` | AWS EKS Hub 환경 values와 배포 설정 |
| `factory-a/` | 운영형 Raspberry Pi Spoke 환경 values |
| `factory-b/` | Mac mini VM 테스트베드 Spoke 환경 values |
| `factory-c/` | Windows VM 테스트베드 Spoke 환경 values |

## 기준

- 공통 배포 템플릿은 `charts/`에 둔다.
- 환경별 차이는 이 디렉터리의 values로 분리한다.
- secret, private key, certificate 원문은 이 디렉터리에 두지 않는다.
