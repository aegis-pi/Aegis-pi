# Architecture ADR Backlog

상태: draft
기준일: 2026-05-09

## 목적

이 문서는 대화 중 나온 아키텍처 질문과 쟁점을 나중에 Architecture Decision Record로 전환하기 위해 임시로 모아 둔다.

`12_two_vpc_mvp_architecture_decision.md`는 현재 논의에서 합의된 방향을 정리하고, 이 문서는 아직 ADR로 분리해 남길 가치가 있는 질문과 검토 포인트를 정리한다.

## 관련 기존 문서

현재 비슷한 판단과 수정 후보는 아래 문서에 흩어져 있다.

| 문서 | 관련 내용 |
| --- | --- |
| `docs/planning/05_decision_rationale.md` | K3s + Edge Agent + IoT Core, S3 raw data lake, EKS Risk Service, Dashboard 방향 같은 주요 선택 이유 |
| `docs/planning/07_dashboard_vpc_extension_plan.md` | Dashboard VPC와 Processing VPC 분리, Dashboard가 Tailscale/ArgoCD/EKS API에 직접 접근하지 않는 기준 |
| `docs/planning/09_m1_eks_vpc_decision_record.md` | 기존 Hub EKS/VPC MVP 기준, public/private subnet, EKS endpoint, Terraform root 분리 |
| `docs/planning/12_two_vpc_mvp_architecture_decision.md` | 1번 Data/Dashboard VPC, 2번 Control/Management VPC 배치 합의 |
| `docs/issues/edit.md` | 기존 issue 문서에 나중에 반영할 데이터 플레인/Edge Agent 수정 후보 |

## ADR 후보 목록

| 후보 ID | 질문 | 현재 정리 상태 | 관련 문서 |
| --- | --- | --- | --- |
| ADR-CAND-001 | VPC를 하나로 갈지, 2개 이상으로 나눌지 | 2 VPC MVP 방향으로 정리. 1 VPC는 가능하지만 제어/데이터 경계가 섞이는 대안으로 기록 필요 | `12_two_vpc_mvp_architecture_decision.md`, `09_m1_eks_vpc_decision_record.md` |
| ADR-CAND-002 | 하나의 VPC로 간다면 3티어인지 4티어인지 | 네트워크 구조는 3티어로 보는 것이 타당. 논리적으로 제어/서비스 처리 계층이 갈릴 수 있음 | `12_two_vpc_mvp_architecture_decision.md` |
| ADR-CAND-003 | 2 VPC 구조에서 각 VPC에 어떤 리소스를 둘지 | 1번 Data/Dashboard, 2번 Control/Management로 정리. Dashboard와 Grafana를 다른 성격으로 분리 | `12_two_vpc_mvp_architecture_decision.md`, `07_dashboard_vpc_extension_plan.md` |
| ADR-CAND-004 | Dashboard Web/API를 Control VPC에 둘지 Data/Dashboard VPC에 둘지 | 사용자-facing Dashboard는 Data/Dashboard VPC 쪽이 자연스럽다는 방향. Dashboard API의 역할 경계는 추가 명세 필요 | `12_two_vpc_mvp_architecture_decision.md` |
| ADR-CAND-005 | Dashboard Web은 public subnet에 둘지 private subnet에 둘지 | 서버형 Web이면 private app subnet, public에는 ALB/WAF만. 정적 SPA면 S3/CloudFront 가능 | `12_two_vpc_mvp_architecture_decision.md` |
| ADR-CAND-006 | Grafana는 어느 VPC에 둘지, 무엇을 관측하는지 | Grafana는 Control/Management VPC에 두고 Hub EKS/AMP 운영 관측 도구로 사용. 사용자 Dashboard와 분리 | `12_two_vpc_mvp_architecture_decision.md`, `docs/ops/17_hub_grafana_amp.md` |
| ADR-CAND-007 | 공장 로컬 ArgoCD와 Hub ArgoCD의 역할을 어떻게 나눌지 | 초기 검토안은 factory-a 로컬 ArgoCD와 EKS Hub ArgoCD의 ownership 분리였다. 최신 목표는 ADR-CAND-013의 Hub ArgoCD 중심 이관이며, Local ArgoCD는 전환 기간에만 유지 | `README.md`, `00_current_architecture.md`, `M3_deploy-pipeline.md`, `14_argocd_hub_migration_plan.md` |
| ADR-CAND-008 | ArgoCD와 Tailscale은 같은 영역에 있어야 하는지 | 둘 다 Hub-Spoke 제어 plane이므로 Control/Management VPC에 둔다 | `12_two_vpc_mvp_architecture_decision.md`, `M2_mesh-vpn-hub-spoke.md` |
| ADR-CAND-009 | Tailscale 등록 기기 탈취 또는 IP 유출 시 피해 범위를 어떻게 줄일지 | MVP는 Tailscale 유지. 공장별 tag/ACL, 시스템/운영자 권한 분리, K8s RBAC 최소화, DB 접근망 확장 금지 필요 | `12_two_vpc_mvp_architecture_decision.md`, `M2_mesh-vpn-hub-spoke.md` |
| ADR-CAND-010 | ArgoCD, Grafana, Risk Engine을 한 컴퓨트 영역에 둘지 분리할지 | Risk Engine은 Data/Dashboard VPC로 분리. Grafana/ArgoCD는 Control VPC. 현재 EKS 기반에서는 EC2 단일 배치가 아니라 역할별 workload 배치로 해석 | `12_two_vpc_mvp_architecture_decision.md` |
| ADR-CAND-011 | Fleet Controller 개념을 도입할지 | 현재 프로젝트 범위에 없는 개념으로 제외. 공장 목록/설정은 runtime config, Helm values, ApplicationSet, Dashboard API 조회 로직으로 우선 처리 | `12_two_vpc_mvp_architecture_decision.md` |
| ADR-CAND-012 | VPC 간 직접 연결을 둘지 관리형 서비스/IAM 계약으로 연결할지 | MVP는 직접 연결을 약하게 유지하고 S3/DynamoDB/AMP 같은 관리형 서비스를 우선. 필요 시 Peering/TGW/PrivateLink 후속 검토 | `12_two_vpc_mvp_architecture_decision.md`, `07_dashboard_vpc_extension_plan.md` |
| ADR-CAND-013 | factory local ArgoCD를 Hub ArgoCD 중심으로 이관할지 | 실무 운영 기준으로는 Hub ArgoCD 중심이 단순하다. factory-a local ArgoCD는 즉시 제거하지 않고 단계적으로 이관하는 방향 | `14_argocd_hub_migration_plan.md` |

## ADR-CAND-001: VPC 개수

### 질문

VPC를 하나로 구성할지, 2개 이상으로 나눌지.

### 대화 중 나온 관점

하나의 VPC로도 MVP 구성은 가능하다. 하지만 ArgoCD/Tailscale/EKS Hub 같은 제어 plane과 Risk Engine/Event Processor/DB 같은 데이터 plane이 같은 private app tier에 섞인다.

2 VPC 구조는 작업 분담과 보안 경계를 명확히 한다.

```text
1번 VPC: Data / Dashboard
2번 VPC: Control / Management
```

3 VPC 구조는 외부 공개 웹/프론트 또는 별도 관제 UI 영역을 더 분리하는 장기 확장안으로 남긴다.

### ADR로 남길 때 결정해야 할 것

```text
MVP에서 실제 Terraform root를 몇 개로 나눌지
각 VPC의 CIDR, subnet, NAT, endpoint 기준
VPC 간 직접 통신 허용 여부
3 VPC 전환 조건
```

## ADR-CAND-002: 단일 VPC일 때 티어 구조

### 질문

하나의 VPC로 구성하면 3티어인지 4티어인지.

### 대화 중 나온 관점

네트워크 구조는 3티어로 보는 것이 맞다.

```text
Public subnet
  - ALB
  - NAT Gateway

Private App subnet
  - ArgoCD
  - Tailscale
  - Grafana
  - Dashboard API
  - Risk Engine

Private Data subnet
  - RDS
  - Redis
  - OpenSearch
```

다만 Private App 안에 운영 제어 성격과 서비스 처리 성격이 함께 있으므로 논리적으로는 4계층처럼 해석될 수 있다.

### ADR로 남길 때 결정해야 할 것

```text
단일 VPC 대안을 문서상 fallback으로만 둘지
논리 계층 분리를 subnet으로 표현할지 namespace/security group으로 표현할지
```

## ADR-CAND-003: 2 VPC 리소스 배치

### 질문

2 VPC로 나눌 경우 각 VPC에 어떤 리소스를 둘지.

### 대화 중 나온 관점

최신 논의 기준은 아래다.

```text
1번 VPC: Data / Dashboard VPC
  - Dashboard Web
  - Dashboard Backend/API
  - Event Processor
  - Risk Engine
  - Replay Builder
  - Near-miss Aggregator
  - AI / analytics worker
  - RDS
  - Redis
  - OpenSearch

2번 VPC: Control / Management VPC
  - EKS Hub
  - ArgoCD
  - Tailscale
  - Prometheus Agent
  - Grafana
  - AWS Load Balancer Controller
```

### ADR로 남길 때 결정해야 할 것

```text
Grafana와 Dashboard의 역할 분리 기준
Dashboard API가 읽는 저장소
Risk Engine과 Dashboard API의 호출 관계
```

## ADR-CAND-004: Dashboard Backend/API 위치

### 질문

Dashboard Backend/API가 실제 웹 대시보드의 백엔드라면 Control VPC에 두는 것이 맞는지.

### 대화 중 나온 관점

Dashboard Backend/API가 사용자-facing Dashboard의 조회 API라면 Control VPC보다 Data / Dashboard VPC에 두는 편이 자연스럽다.

Control VPC에는 ArgoCD/Tailscale 같은 민감한 제어 컴포넌트가 있으므로, 사용자-facing 대시보드와 섞지 않는다.

### ADR로 남길 때 결정해야 할 것

```text
Dashboard Backend/API의 책임 범위
Dashboard API가 읽는 데이터 원천
Dashboard API가 write 권한을 가질지 여부
Dashboard API와 Risk Engine을 같은 서비스로 둘지 분리할지
```

## ADR-CAND-005: Dashboard Web subnet 배치

### 질문

3티어 구성에서 Web은 public subnet에 두는지, private subnet에 두는지.

### 대화 중 나온 관점

서버형 Web이면 private app subnet에 두고 public subnet에는 ALB/WAF만 둔다.

```text
Public subnet
  - ALB
  - WAF

Private App subnet
  - Dashboard Web
  - Dashboard Backend/API
```

정적 SPA라면 VPC 내부에 둘 필요가 없다.

```text
CloudFront
  -> S3 static site
  -> Dashboard API
```

### ADR로 남길 때 결정해야 할 것

```text
Dashboard Web 구현 형태: 서버형 Web 또는 정적 SPA
CloudFront 도입 시점
API 인증 방식
ALB와 API Gateway 중 어떤 entry를 사용할지
```

## ADR-CAND-006: Grafana 역할과 위치

### 질문

클라우드 Grafana가 관측하는 대상은 무엇이고 어느 VPC에 두는 것이 맞는지.

### 대화 중 나온 관점

현재 클라우드 Grafana는 Hub EKS 운영 관측 도구다.

```text
Hub EKS
  -> Prometheus Agent
  -> AMP
  -> Grafana
```

현재 대상:

```text
Prometheus Agent 자체
Kubernetes API server
EKS node metrics
prometheus.io/scrape=true annotation이 붙은 Hub 내부 Pod
```

현재 직접 보지 않는 대상:

```text
factory-a InfluxDB 센서 데이터
Risk Engine 결과
Dashboard latest status
공장별 Risk Score
```

따라서 Grafana는 Control / Management VPC에 둔다.

### ADR로 남길 때 결정해야 할 것

```text
Data / Dashboard VPC workload metric을 AMP로 보낼지
Grafana dashboard 범위를 Hub 운영 관측으로 제한할지
Data service 관측까지 포함할지
Grafana Admin UI 외부 접근 방식을 어떻게 제한할지
```

## ADR-CAND-007: Local ArgoCD와 Hub ArgoCD ownership 분리 검토안

### 질문

공장 내부 ArgoCD와 EKS Hub ArgoCD를 어떤 역할로 나눌지.

이 항목은 초기 hybrid 검토안을 기록한 것이다. 최신 목표는 `ADR-CAND-013`과 `docs/planning/14_argocd_hub_migration_plan.md`의 Hub ArgoCD 중심 이관 방향을 따른다.

### 대화 중 나온 관점

초기 검토 기준에서는 ArgoCD가 하나만 있는 구조가 아니었다.

공장 내부에는 이미 `factory-a` 로컬 자율 운영을 위한 ArgoCD가 있다. 이 ArgoCD는 기존 Safe-Edge 기준선의 GitOps 배포를 담당한다.

EKS Hub에도 ArgoCD를 둔다. Hub ArgoCD는 중앙에서 Edge Agent 같은 클라우드 연동 컴포넌트와 후속 멀티 factory 공통 spoke component를 배포하기 위한 역할이다.

```text
factory-a local ArgoCD
  - factory-a 로컬 자율 운영
  - 기존 Safe-Edge workload 관리
  - Hub / Tailscale 장애와 무관하게 공장 내부 운영 유지

EKS Hub ArgoCD
  - Edge Agent 같은 클라우드 연동 컴포넌트 배포
  - factory-a/b/c로 확장될 공통 spoke component 관리
  - Tailscale 경유로 spoke K3s cluster 접근
```

따라서 초기 검토안에서의 "ArgoCD 2개"는 중복 배치가 아니라 역할이 다른 2계층 GitOps 구조로 보았다.

중요한 기준은 두 ArgoCD가 같은 리소스를 동시에 관리하지 않는 것이다.

예시 ownership:

```text
factory-a local ArgoCD owns:
  - monitoring
  - ai-apps
  - 기존 Safe-Edge app
  - factory-a 로컬 생존형 운영 기준

EKS Hub ArgoCD owns:
  - edge-agent
  - cloud telemetry sender
  - dummy/testbed workload
  - 후속 factory-b/c 공통 spoke component
  - 중앙 배포 파이프라인 검증용 앱
```

namespace 또는 path 기준으로 경계를 나누는 방향이 필요하다.

예시 namespace 경계:

```text
factory-a local ArgoCD:
  - monitoring
  - ai-apps
  - argocd
  - longhorn-system

EKS Hub ArgoCD:
  - edge-system
  - aegis-edge
  - cloud-agent
```

예시 repo/path 경계:

```text
safe-edge-config-main:
  - factory-a local ArgoCD source
  - monitoring / ai-apps / local Safe-Edge baseline

aegis-pi 또는 별도 deploy repo:
  - Hub ArgoCD source
  - edge-agent / spoke components / ApplicationSet
```

AZ별 독립 ArgoCD를 두는 DR 구조는 별도 문제다. 이 후보의 핵심은 factory-a local ArgoCD와 Hub ArgoCD의 ownership 분리였다.

최신 확정 방향에서는 이 hybrid ownership을 장기 운영 모델로 두지 않는다. `factory-a` Local ArgoCD는 전환 기간 동안 유지하고, 기존 workload를 단계적으로 Hub ArgoCD로 이관한 뒤 제거 또는 비활성화한다.

### ADR로 남길 때 결정해야 할 것

```text
local ArgoCD가 관리하는 namespace / resource 목록
Hub ArgoCD가 관리하는 namespace / resource 목록
두 ArgoCD가 같은 리소스를 관리하지 않도록 막는 규칙
Git repo를 분리할지, 같은 repo 안에서 path를 분리할지
Hub ArgoCD가 factory-a에 배포할 수 있는 최소 RBAC 범위
Hub 또는 Tailscale 장애 시 local ArgoCD 운영 지속 기준
ArgoCD HA chart 옵션 적용 시점은 별도 후속 검토
```

## ADR-CAND-008: ArgoCD와 Tailscale 영역

### 질문

ArgoCD와 Tailscale은 같은 영역에 있어야 하는지.

### 대화 중 나온 관점

둘 다 Hub-Spoke 제어 plane이다.

```text
ArgoCD
  -> Tailscale
  -> factory-a / factory-b / factory-c K3s API
```

따라서 둘 다 Control / Management VPC에 둔다. 같은 VPC/보안 영역에 둔다는 의미이지, 같은 Pod나 같은 인스턴스에 둔다는 의미는 아니다.

### ADR로 남길 때 결정해야 할 것

```text
Tailscale Operator 방식 유지 여부
factory별 egress service naming
ArgoCD cluster secret 관리 방식
Tailscale 장애 시 ArgoCD 배포 중단 정책
```

## ADR-CAND-009: Tailscale 탈취/유출 피해 범위

### 질문

Tailscale 등록 기기 탈취 또는 IP 유출 시 피해 범위를 어떻게 줄일지.

### 대화 중 나온 관점

MVP는 Tailscale을 유지하되, 최소 권한과 범위 분리가 필요하다.

필요한 원칙:

```text
factory별 tag / ACL 분리
운영자 단말과 시스템 노드 권한 분리
Tailscale Connector 전용화
Kubernetes API RBAC 최소화
DB / 분석 저장소 직접 접근 차단
Dashboard / Risk Engine 접근을 Tailscale에 의존시키지 않기
```

### ADR로 남길 때 결정해야 할 것

```text
Tailnet ACL 정책
tag:aegis-hub, tag:factory-a/b/c 권한 범위
ArgoCD용 ServiceAccount 권한 범위
운영자 단말 접근 정책
키 회전 / revoke 절차
```

## ADR-CAND-010: 역할별 workload 분리

### 질문

ArgoCD, Grafana, Risk Engine을 같은 컴퓨트 영역에 둘지 분리할지.

### 대화 중 나온 관점

초기 검증에서는 같이 둘 수 있지만 최종 방향은 역할 기준 분리다.

```text
ArgoCD + Tailscale: Control / Management
Grafana: Control / Management observability
Risk Engine: Data / Dashboard processing
```

현재 repo는 EKS 기반이므로 "한 EC2 안에 모두 배치"보다는 EKS workload와 VPC 역할 분리로 해석하는 편이 맞다.

### ADR로 남길 때 결정해야 할 것

```text
Risk Engine을 별도 EKS cluster에 둘지 ECS/Lambda로 둘지
Data / Dashboard VPC의 compute 방식
Control VPC EKS와 Data VPC compute의 배포 책임 경계
```

## ADR-CAND-011: Fleet Controller 제외

### 질문

Fleet Controller가 무엇이고 현재 범위에 포함되는지.

### 대화 중 나온 관점

Fleet Controller는 현재 프로젝트에 명시된 컴포넌트가 아니다. 따라서 MVP 범위에서 제외한다.

우선 아래 조합으로 대체한다.

```text
configs/runtime/runtime-config.yaml
Helm values
ArgoCD ApplicationSet
Dashboard API 조회 로직
```

### ADR로 남길 때 결정해야 할 것

```text
공장 등록/비활성화/정책 변경을 UI에서 다룰 필요가 생기는 시점
runtime-config.yaml을 DB로 승격할 조건
별도 Fleet 관리 서비스 도입 조건
```

## ADR-CAND-012: VPC 간 연결 방식

### 질문

Data / Dashboard VPC와 Control / Management VPC를 직접 연결할지.

### 대화 중 나온 관점

MVP에서는 VPC 간 직접 통신보다 관리형 서비스와 IAM 계약을 우선한다.

```text
Data service metrics
  -> AMP
  -> Control VPC Grafana가 조회

Risk 결과
  -> S3 latest / processed 또는 DynamoDB
  -> Dashboard API가 조회
```

직접 통신은 후속 검토다.

```text
VPC Peering
Transit Gateway
PrivateLink
API Gateway + VPC Link
```

### ADR로 남길 때 결정해야 할 것

```text
Dashboard API가 Data VPC 내부 저장소를 직접 조회할지
Control VPC가 Data VPC 내부 API를 호출할 필요가 있는지
관리형 저장소만으로 MVP 요구를 만족하는지
```

## ADR-CAND-013: Local ArgoCD를 Hub ArgoCD 중심으로 이관

### 질문

공장 내부 Local ArgoCD를 장기 운영 구조로 유지할지, EKS Hub ArgoCD 중심 구조로 이관할지.

### 대화 중 나온 관점

Hybrid ArgoCD는 공장 자율 GitOps 측면에서는 장점이 있지만 운영 복잡도가 증가한다.

```text
repo/path ownership 분리
namespace ownership 충돌 방지
local ArgoCD와 Hub ArgoCD 상태 동시 확인
공장별 ArgoCD 업그레이드/계정/접근 관리
장애 시 어느 ArgoCD가 문제인지 판단 필요
```

현재 `factory-a`는 Safe-Edge baseline이 안정화되면 자주 CD할 대상이 아니다. Hub나 Tailscale이 끊겨도 기존 Pod와 K3s runtime은 계속 동작한다. 중앙 연결 장애 중 급하게 공장 내부에 새 배포를 해야 할 가능성이 낮다면, Local ArgoCD 유지 가치보다 운영 복잡도가 더 클 수 있다.

따라서 실무 운영 기준으로는 Hub ArgoCD 중심 구조가 더 단순하다.

다만 `factory-a` local ArgoCD는 이미 검증된 운영 구성 요소이므로 즉시 제거하지 않고, 신규 Edge Agent부터 Hub ArgoCD로 관리한 뒤 기존 Safe-Edge baseline을 단계적으로 이관하는 방향이 안전하다.

### 관련 계획 문서

```text
docs/planning/14_argocd_hub_migration_plan.md
```

### ADR로 남길 때 결정해야 할 것

```text
Hub ArgoCD 중심 구조를 최종 목표로 확정할지
factory-a local ArgoCD 제거 시점
factory-a Safe-Edge baseline 이관 순서
factory-b/c는 Hub ArgoCD만 사용할지
운영형 factory-a와 테스트베드 factory-b/c sync policy 차이
Hub/Tailscale 장애 시 변경 freeze 원칙
local ArgoCD rollback 보존 기간
```
