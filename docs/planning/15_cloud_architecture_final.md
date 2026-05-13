# Cloud Architecture Final

상태: source of truth
기준일: 2026-05-09

## 목적

이 문서는 Aegis-Pi의 확정된 클라우드 아키텍처 방향과 리소스 배치를 정리한다.

범위는 Factory Spoke, Control / Management VPC, Data / Dashboard VPC, Hub ArgoCD 중심 배포, 데이터 흐름, 관측 흐름이다.

## 전체 구조

```text
Factory Spoke 영역
  - factory-a
  - factory-b
  - factory-c

2번 VPC: Control / Management VPC
  - 중앙 배포
  - Hub-Spoke 연결
  - 운영 관측

1번 VPC: Data / Dashboard VPC
  - 데이터 처리
  - Risk 계산
  - 사용자 대시보드
```

## 2026-05-13 멘토링 반영

### 기존 초안

기존 최종 아키텍처 초안은 Control / Management VPC와 Data / Dashboard VPC를 분리하고, 데이터 흐름을 IoT Core -> S3 raw -> Event Processor -> Risk Engine -> Dashboard로 설명했다.

### 변경 이유

멘토링에서는 VPC 분리는 정답이 아니라 고객 요구사항에 따른 선택이며, Dashboard의 실시간성도 수치로 정의해야 한다는 피드백이 있었다. S3 raw만으로 현재 상태를 표시한다고 설명하면 준실시간 관제 근거가 약해질 수 있다.

### 보강 방향

기존 S3 raw 흐름은 원본 보존과 재처리 경로로 유지한다. 동시에 Dashboard 현재 상태 조회를 위해 IoT Core 이후 Lambda 또는 SQS/SNS를 거쳐 latest status store를 갱신하는 경로를 추가 검토한다. Dual VPC는 고객 보안 요구와 역할 분리 요구가 있을 때 설득력 있는 목표 구조로 설명한다.

전체 연결 구조는 아래와 같다.

```text
factory-a / factory-b / factory-c
  -> K3s Spoke
  -> Tailscale 연결
  -> Control / Management VPC
      -> EKS Hub
      -> Hub ArgoCD
      -> Grafana
      -> Prometheus Agent

factory-a / factory-b / factory-c
  -> telemetry
  -> IoT Core
  -> S3 raw
  -> Data / Dashboard VPC
      -> Event Processor
      -> Risk Engine
      -> Dashboard Backend/API
      -> Dashboard Web
```

## Factory 영역

각 factory는 독립된 K3s Spoke다.

### factory-a

`factory-a`는 운영형 Safe-Edge Spoke다.

```text
factory-a
  - Raspberry Pi 3-node K3s
  - 운영형 Safe-Edge Spoke
  - monitoring
  - ai-apps
  - InfluxDB
  - local workload
  - Edge Agent 배포 대상
```

### factory-b

`factory-b`는 Mac mini VM 기반 테스트베드 Spoke다.

```text
factory-b
  - Mac mini VM K3s
  - 테스트베드 Spoke
  - dummy input
  - Edge Agent 배포 대상
```

### factory-c

`factory-c`는 Windows VM 기반 테스트베드 Spoke다.

```text
factory-c
  - Windows VM K3s
  - 테스트베드 Spoke
  - dummy input
  - Edge Agent 배포 대상
```

## ArgoCD 배치

목표 구조는 Hub ArgoCD 중심이다.

```text
EKS Hub ArgoCD
  - factory-a 배포 관리
  - factory-b 배포 관리
  - factory-c 배포 관리
  - Edge Agent 배포
  - 공통 spoke component 배포
  - ApplicationSet 기반 factory별 배포
```

`factory-a`에 기존 Local ArgoCD가 있는 경우에는 전환 기간 동안 유지한다.

전환 기간의 기준은 아래와 같다.

```text
전환 기간
  - factory-a Local ArgoCD 유지
  - 신규 Edge Agent는 Hub ArgoCD로 배포
  - 기존 workload를 단계적으로 Hub ArgoCD로 이관
  - 이관 완료 후 Local ArgoCD 제거 또는 비활성화
```

관련 세부 계획은 `docs/planning/14_argocd_hub_migration_plan.md`를 따른다.

## 2번 VPC: Control / Management VPC

2번 VPC는 중앙 배포와 운영 관측 영역이다.

### Public Subnet

```text
Public Subnet
  - NAT Gateway
  - 필요 시 Admin UI ALB
```

### Private App Subnet

```text
Private App Subnet
  - EKS Hub
  - Hub ArgoCD
  - Tailscale Operator / Connector
  - Prometheus Agent
  - Grafana
  - AWS Load Balancer Controller
```

### 배포 흐름

```text
GitHub Actions
  -> ECR
  -> Helm values / manifest update
  -> Hub ArgoCD
  -> Tailscale
  -> factory-a K3s
  -> factory-b K3s
  -> factory-c K3s
```

### Grafana

Grafana는 Control / Management VPC에 둔다.

Grafana 관측 대상은 아래 범위다.

```text
Grafana 관측 대상
  - Hub EKS
  - Prometheus Agent
  - AMP
  - Kubernetes API server
  - EKS node
  - Hub 내부 Pod
  - 필요 시 Edge Agent metrics
```

## 1번 VPC: Data / Dashboard VPC

1번 VPC는 데이터 처리와 사용자 대시보드 영역이다.

### Public Subnet

```text
Public Subnet
  - ALB
  - WAF
  - ACM
```

### Private App Subnet

```text
Private App Subnet
  - Dashboard Web
  - Dashboard Backend/API
  - Event Processor
  - Risk Engine
  - Replay Builder
  - Near-miss Aggregator
  - AI / Analytics Worker
```

### Private Data Subnet

```text
Private Data Subnet
  - RDS / PostgreSQL
  - Redis / ElastiCache
  - OpenSearch
```

### 데이터 흐름

```text
factory-a/b/c telemetry
  -> IoT Core
  -> S3 raw
  -> Event Processor
  -> Risk Engine
  -> processed / latest 저장
  -> Dashboard Backend/API
  -> Dashboard Web
```

### Dashboard Web/API 제공 범위

Dashboard Web/API가 제공하는 화면은 아래 범위다.

```text
Dashboard Web/API
  - 공장별 Risk Score
  - 공장별 latest status
  - 이벤트 목록
  - near-miss 요약
  - replay 결과
  - 센서 / AI / 장비 상태 요약
```

## 최종 리소스 배치 요약

### Factory-a

```text
Factory-a
  - Raspberry Pi K3s
  - Safe-Edge workload
  - Edge Agent
```

### Factory-b

```text
Factory-b
  - Mac mini VM K3s
  - dummy workload
  - Edge Agent
```

### Factory-c

```text
Factory-c
  - Windows VM K3s
  - dummy workload
  - Edge Agent
```

### Control / Management VPC

```text
Control / Management VPC
  - EKS Hub
  - Hub ArgoCD
  - Tailscale
  - Prometheus Agent
  - Grafana
  - AWS Load Balancer Controller
```

### Data / Dashboard VPC

```text
Data / Dashboard VPC
  - Dashboard Web
  - Dashboard Backend/API
  - Event Processor
  - Risk Engine
  - Replay Builder
  - Near-miss Aggregator
  - RDS
  - Redis
  - OpenSearch
```

## 최종 흐름

### 배포 흐름

```text
GitHub Actions
  -> ECR
  -> Hub ArgoCD
  -> Tailscale
  -> factory-a/b/c
```

### 데이터 흐름

```text
factory-a/b/c
  -> IoT Core
  -> S3 raw
  -> Event Processor
  -> Risk Engine
  -> Dashboard API
  -> Dashboard Web
```

### 관측 흐름

```text
Hub EKS / Prometheus Agent / Edge Agent metrics
  -> AMP
  -> Grafana
```
