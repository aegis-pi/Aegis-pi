# Charts

이 디렉터리는 Aegis-Pi Kubernetes 리소스를 배포하기 위한 Helm chart를 둔다.

## 하위 폴더

| 경로 | 역할 |
| --- | --- |
| `aegis-hub/` | AWS EKS Hub 쪽 공통 컴포넌트 배포 차트 |
| `aegis-spoke/` | `factory-a`, `factory-b`, `factory-c` Spoke 쪽 공통 애플리케이션 배포 차트 |

## 기준

- 공통 chart는 `charts/`에 둔다.
- 공장별 값은 `envs/` 아래 values 파일로 분리하는 방향을 따른다.
