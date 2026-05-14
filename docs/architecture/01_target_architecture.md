# 목표 확장 아키텍처

상태: draft
기준일: 2026-05-04

## 목적

현재 완료된 `factory-a` Safe-Edge 기준선을 기반으로, 이후 Aegis-Pi가 확장할 목표 Hub/Spoke 구조를 정리한다.

## 최신 기준

2026-05-09 기준 확정된 클라우드 리소스 배치와 VPC 명명은 `docs/planning/15_cloud_architecture_final.md`를 source of truth로 한다.

이 문서는 기존 목표 Hub/Spoke 구조를 설명하는 보조 문서다. 최신 기준의 VPC 경계는 아래와 같다.

```text
1번 VPC: Data / Dashboard VPC
2번 VPC: Control / Management VPC
Factory Spoke: factory-a / factory-b / factory-c
```

## 현재와 목표의 경계

현재 완료:

```text
factory-a 로컬 Safe-Edge 기준선
M1 Issue 0~4 Hub EKS/VPC/namespace/ArgoCD bootstrap 및 foundation S3 기준선 검증 후 destroy
M1 Issue 5 factory-a IoT Thing/Policy/K3s Secret 생성 완료
```

후속 목표:

```text
AWS EKS Hub
1번 Data / Dashboard VPC
2번 Control / Management VPC
factory-a / factory-b / factory-c 멀티 Spoke
중앙 배포 / 중앙 수집 / Risk Twin 관제
```

구현 책임 경계:

```text
Terraform: AWS 인프라
Ansible: bootstrap / 설정 / 소프트웨어 설치
GitHub Actions: CI
GitHub + ArgoCD: CD
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
        -> IoT Rule -> S3 raw
        -> Lambda data processor -> DynamoDB LATEST/HISTORY + S3 processed
    -> Data / Dashboard VPC Web/API
```

확장 조건:

- 현재 InfluxDB 기반 로컬 관제에서 표준 input schema를 분리할 것
- `edge-agent` 이미지를 만들고 `factory-a`에서는 real mode, `factory-b/c`에서는 dummy mode로 공통 송신 로직을 재사용할 것
- IoT Core topic과 S3 partition 규칙을 확정할 것
- `factory_id`, `source_type`, timestamp 기준을 고정할 것
- Dashboard Web/API가 Spoke K3s, ArgoCD, Control / Management VPC의 EKS API, Tailscale 관리망에 직접 붙지 않도록, Edge Agent가 `system_status`, `device_status`, `workload_status`, `pipeline_heartbeat`까지 송신할 것

초기 topic 기준:

```text
aegis/factory-a/sensor
aegis/factory-a/system_status
aegis/factory-a/device_status
aegis/factory-a/workload_status
aegis/factory-a/heartbeat
aegis/factory-b/sensor
aegis/factory-b/system_status
aegis/factory-b/device_status
aegis/factory-b/workload_status
aegis/factory-b/heartbeat
aegis/factory-c/sensor
aegis/factory-c/system_status
aegis/factory-c/device_status
aegis/factory-c/workload_status
aegis/factory-c/heartbeat
```

## 목표 Data / Dashboard VPC

사용자 대시보드는 Tailscale/VPN 의존 없이 ALB, WAF, Cognito 또는 사내 IdP 인증 뒤에 제공한다.

Dashboard Web/API는 ArgoCD, Tailscale, EKS API 같은 제어 plane에 직접 접근하지 않는다. 데이터 조회는 1번 Data / Dashboard VPC의 processed data와 latest status store를 기준으로 한다.

```text
1번 Data / Dashboard VPC
    -> ALB
    -> WAF
    -> Auth
    -> Dashboard Web/API
    -> DynamoDB LATEST/HISTORY
    -> S3 processed
    -> Lambda data processor integration
```

상세 기준:

```text
docs/planning/07_dashboard_vpc_extension_plan.md
```

## 목표 Hub Namespace

```text
argocd
observability
risk
ops-support
```

이 namespace 기준선은 `scripts/ansible`의 Hub bootstrap playbook에서 관리한다. Hub EKS 자체는 `infra/hub`, S3/AMP/IoT Rule 같은 영속 리소스는 `infra/foundation` root에서 분리 관리한다. ECR은 후속 이미지 파이프라인 단계에서 추가한다.

역할:

| Namespace | 역할 |
| --- | --- |
| `argocd` | 멀티 Spoke 배포 제어 |
| `observability` | AMP, Prometheus 연동, 내부 관측 |
| `risk` | Hub 배포 검증용 또는 임시 workload. 최신 목표에서는 Risk 계산을 Lambda data processor로 분리 |
| `ops-support` | legacy pipeline status 집계 후보. 최신 목표에서는 Lambda data processor가 DynamoDB에 `pipeline_status`를 기록 |

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

현재 `factory-a`의 Grafana dashboard는 Risk Twin 전 단계의 로컬 관제 기준선이다. 후속 단계에서 이 값을 표준 schema, Lambda data processor, DynamoDB/S3 processed, Data / Dashboard VPC 관제 화면으로 연결한다.

## 확장 우선순위

1. `factory-a` 현재 상태 문서화 완료
2. Hub EKS 기준선 구성 완료, 필요 시 `infra/hub` Terraform apply와 `scripts/ansible` bootstrap 순서로 재생성
3. Hub ArgoCD Ansible bootstrap
4. Tailscale 또는 동등한 Hub-Spoke 연결 방식 확정
5. GitHub Actions / ECR / ArgoCD ApplicationSet 구성
6. Edge Agent 구현 및 IoT Core / S3 데이터 수집 경로 구성
7. 1번 Data / Dashboard VPC, Lambda data processor, DynamoDB LATEST/HISTORY, S3 processed 및 dashboard 구현
8. `factory-b`, `factory-c` 테스트베드 확장

## 현재 구조로 가져오면 안 되는 것

현재 `factory-a` 문서에는 아래를 완료된 것으로 쓰지 않는다.

```text
AWS EKS Hub
IoT Core / S3
ECR
GitHub Actions
Tailscale
Data / Dashboard VPC
factory-b / factory-c
Lambda data processor / Risk calculation
LLM 보고서
```

이 항목들은 목표 구조 또는 후속 계획 문서에서만 관리한다.

## 2026-05-14 수정 방향

목표 데이터 평면은 `docs/specs/data_storage_pipeline.md`의 Lambda/DynamoDB 기준을 따른다.

이전 `Risk Normalizer`, `Risk Score Engine`, `Event Processor`, `pipeline-status-aggregator` 표현은 별도 컨테이너 서비스가 아니라 Lambda data processor 내부 처리 단계로 해석한다.
