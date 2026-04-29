# 목표 확장 아키텍처

상태: draft
기준일: 2026-04-29

## 목적

현재 완료된 `factory-a` Safe-Edge 기준선을 기반으로, 이후 Aegis-Pi가 확장할 목표 Hub/Spoke 구조를 정리한다.

## 현재와 목표의 경계

현재 완료:

```text
factory-a 로컬 Safe-Edge 기준선
```

후속 목표:

```text
AWS EKS Hub
factory-a / factory-b / factory-c 멀티 Spoke
중앙 배포 / 중앙 수집 / Risk Twin 관제
```

## 목표 구조

```text
AWS EKS Hub
    ├── factory-a  Raspberry Pi 3-node K3s, 운영형
    ├── factory-b  Mac mini VM K3s, 테스트베드형
    └── factory-c  Windows VM K3s, 테스트베드형
```

Hub와 각 Spoke는 하나의 단일 Kubernetes cluster가 아니라 독립 cluster로 운영한다.

## 목표 제어 평면

```text
GitHub Push
    -> GitHub Actions
    -> ECR
    -> ArgoCD
    -> Tailscale
    -> 각 Spoke rollout
```

확장 조건:

- `factory-a` GitOps 기준선이 안정적으로 유지될 것
- 공장별 values 구조가 정리될 것
- ArgoCD가 각 Spoke cluster에 접근 가능할 것
- 운영형과 테스트베드형 sync 정책을 분리할 것

## 목표 데이터 평면

```text
Edge input
    -> local Safe-Edge workloads
    -> InfluxDB / Kubernetes API
    -> Edge Agent
    -> AWS IoT Core
    -> S3
    -> Risk Normalizer
    -> Risk Score Engine
    -> Grafana / Risk Twin Dashboard
```

확장 조건:

- 현재 InfluxDB 기반 로컬 관제에서 표준 input schema를 분리할 것
- `edge-agent` 이미지를 만들고 `factory-a`에서는 real mode, `factory-b/c`에서는 dummy mode로 공통 송신 로직을 재사용할 것
- IoT Core topic과 S3 partition 규칙을 확정할 것
- `factory_id`, `source_type`, timestamp 기준을 고정할 것

초기 topic 기준:

```text
aegis/factory-a/sensor
aegis/factory-a/system_status
aegis/factory-b/sensor
aegis/factory-b/system_status
aegis/factory-c/sensor
aegis/factory-c/system_status
```

## 목표 Hub Namespace

```text
argocd
observability
risk
ops-support
```

역할:

| Namespace | 역할 |
| --- | --- |
| `argocd` | 멀티 Spoke 배포 제어 |
| `observability` | Grafana, AMP, Prometheus 연동 |
| `risk` | normalizer, score engine |
| `ops-support` | pipeline status 집계 |

## Factory 역할

| Factory | 역할 | 현재 상태 |
| --- | --- | --- |
| `factory-a` | 실제 운영형 Safe-Edge | 기준선 완료 |
| `factory-b` | Mac mini VM 테스트베드 | 후속 |
| `factory-c` | Windows VM 테스트베드 | 후속 |

## Risk Twin 목표

표현:

```text
안전
주의
위험
```

목표 입력:

```text
sensor
system_status
pipeline_status
event
```

현재 `factory-a`의 Grafana dashboard는 Risk Twin 전 단계의 로컬 관제 기준선이다. 후속 단계에서 이 값을 표준 schema와 Risk Score Engine으로 연결한다.

## 확장 우선순위

1. `factory-a` 현재 상태 문서화 완료
2. Hub EKS 기준선 구성
3. Tailscale 또는 동등한 Hub-Spoke 연결 방식 확정
4. GitHub Actions / ECR / ArgoCD ApplicationSet 구성
5. Edge Agent 구현 및 IoT Core / S3 데이터 수집 경로 구성
6. Risk Score Engine 및 dashboard 구현
7. `factory-b`, `factory-c` 테스트베드 확장

## 현재 구조로 가져오면 안 되는 것

현재 `factory-a` 문서에는 아래를 완료된 것으로 쓰지 않는다.

```text
AWS EKS Hub
IoT Core / S3
ECR
GitHub Actions
Tailscale
factory-b / factory-c
Risk Score Engine
LLM 보고서
```

이 항목들은 목표 구조 또는 후속 계획 문서에서만 관리한다.
