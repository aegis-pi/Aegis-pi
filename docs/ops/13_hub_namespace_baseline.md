# Hub Namespace Baseline

상태: Terraform root 분리 완료, 다음 platform apply 대기
기준일: 2026-04-30

## 목적

Hub EKS 내부 기능을 namespace 단위로 분리해 ArgoCD, 관측, Risk 계산, 운영 보조 기능의 배포 경계를 명확히 한다.

## Namespace

| Namespace | 역할 |
| --- | --- |
| `argocd` | Hub에서 Spoke 배포 제어 |
| `observability` | Grafana, AMP 연동 메트릭 관제 |
| `risk` | Risk Score Engine, 정규화 서비스 |
| `ops-support` | `pipeline_status` 집계 보조 기능 |

## Terraform 관리

Namespace는 `infra/platform/namespaces.tf`에서 관리한다.

```text
kubernetes_namespace_v1.hub
kubernetes_limit_range_v1.hub_default
```

각 namespace에는 `default-limits` LimitRange를 적용한다.

| 항목 | 값 |
| --- | --- |
| default request CPU | `100m` |
| default request memory | `128Mi` |
| default limit CPU | `500m` |
| default limit memory | `512Mi` |

## 검증

```bash
kubectl get namespaces argocd observability risk ops-support
kubectl get limitrange -A
```

2026-04-30 확인 결과:

```text
argocd          Active
observability   Active
risk            Active
ops-support     Active
```

각 namespace에 `default-limits` LimitRange가 생성되어 있다.

이후 최소 분리 작업에서 테스트용 Hub EKS를 destroy했기 때문에 현재 AWS에는 namespace가 남아 있지 않다. 재생성 순서는 `infra/hub` apply 후 `infra/platform` apply다.
