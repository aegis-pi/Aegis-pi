# MVP 2 VPC Architecture Decision

상태: draft
기준일: 2026-05-09

## 목적

MVP 이후 클라우드 확장 구조를 논의하면서 나온 VPC 분리, Dashboard 위치, Grafana 역할, ArgoCD 구성, Tailscale 유지 범위를 정리한다.

이 문서는 현재 구현을 즉시 변경하는 실행 문서가 아니라, M3 배포 파이프라인과 M4~M6 데이터/대시보드 구현 전에 경계를 맞추기 위한 설계 기준이다.

## 결론

MVP 확장 방향은 2 VPC 구조를 기준으로 한다.

```text
1번 VPC: Data / Dashboard VPC
2번 VPC: Control / Management VPC
```

핵심 배치는 아래와 같다.

| 영역 | 역할 | 주요 리소스 |
| --- | --- | --- |
| 1번 VPC | 데이터 처리 결과 조회, 위험도 표시, 사용자 관제 화면 | Dashboard Web, Dashboard Backend/API, Lambda data processor 연동, DynamoDB LATEST/HISTORY, S3 processed, Replay Builder, Near-miss Aggregator |
| 2번 VPC | 중앙 제어, 배포, Hub-Spoke 연결, 운영 관측 | EKS Hub, ArgoCD, Tailscale, Prometheus Agent, Grafana, AWS Load Balancer Controller |

Grafana는 2번 Control / Management VPC에 둔다. 현재 클라우드 Grafana는 사용자용 Risk Twin 대시보드가 아니라 Hub EKS와 AMP 메트릭을 보는 운영자용 observability 도구이기 때문이다.

Dashboard Web/API는 1번 Data / Dashboard VPC에 둔다. Dashboard는 최종 사용자 또는 본사 관제 담당자가 보는 제품 화면이므로 ArgoCD/Tailscale 같은 제어 plane과 분리한다.

## 2026-05-13 멘토링 반영

### 기존 초안

기존 문서는 MVP 이후 확장 구조를 2 VPC 기준으로 정리했다. Dashboard는 사용자-facing 제품 화면이고, ArgoCD/Tailscale/EKS API 같은 제어 plane과 분리한다는 판단을 담았다.

### 변경 이유

멘토링에서는 2 VPC가 항상 정답이 아니라 고객 요구사항에 따라 선택되는 구조라는 피드백이 있었다. 사용자 역할, 접근 권한, 보안 감사, 개인정보 보호 요구가 분리될 때 2 VPC가 더 설득력 있다.

### 보강 방향

기존 2 VPC 목표 구조는 유지한다. 다만 초기 MVP에서는 하나의 VPC 안에서 subnet, security group, IAM으로 분리하는 방식도 가능하다는 점을 함께 설명한다. Aegis-Pi의 2 VPC는 고객 보안 요구가 강화되는 경우를 고려한 목표 구조로 둔다.

## 1번 VPC: Data / Dashboard VPC

1번 VPC는 공장 데이터 수집 이후의 처리, 저장, 분석, 조회 화면을 담당한다.

### 역할

```text
IoT Core / S3 raw 수신 이후 처리
Lambda data processor 기반 데이터 정규화와 위험도 계산
이벤트 / near-miss 집계
Replay 데이터 생성
Dashboard 화면과 조회 API 제공
분석용 저장소 관리
```

### 리소스 배치

```text
Public subnet
  - ALB
  - WAF
  - ACM certificate endpoint
  - NAT Gateway

Private App subnet
  - Dashboard Web
  - Dashboard Backend/API
  - Lambda data processor integration
  - Replay Builder
  - Near-miss Aggregator
  - AI / analytics worker

Private Data subnet
  - DynamoDB LATEST/HISTORY access
  - S3 processed access
  - RDS / PostgreSQL (후속)
  - Redis / ElastiCache (후속)
  - OpenSearch (후속)
```

### Dashboard Web 위치

서버형 Dashboard Web이면 private app subnet에 둔다.

예시:

```text
Next.js SSR
Node server
Django / Spring web app
EKS / ECS 위에서 동작하는 frontend container
```

이 경우 public subnet에는 ALB/WAF만 두고, ALB가 private app subnet의 Dashboard Web/API로 라우팅한다.

정적 SPA라면 VPC 안에 둘 필요가 없다.

예시:

```text
React / Vite static build
S3 + CloudFront + WAF
```

이 경우 Dashboard Web은 S3/CloudFront로 제공하고, Dashboard Backend/API만 1번 VPC private app subnet에 둔다.

MVP에서는 구현 단순성을 위해 아래 중 하나를 선택한다.

| 방식 | 배치 | 판단 |
| --- | --- | --- |
| 서버형 Web | ALB -> private Dashboard Web/API | 초기 통합 배포가 쉽다 |
| 정적 SPA | CloudFront/S3 -> private Dashboard API | 프론트/백 분리가 명확하다 |

현재 설계 논의 기준에서는 서버형 Web일 가능성을 열어 두고, public subnet에는 ALB/WAF만 둔다.

## 2번 VPC: Control / Management VPC

2번 VPC는 중앙 제어와 운영 관측을 담당한다.

### 역할

```text
GitOps 기반 배포 제어
Hub-Spoke 연결
factory-a / factory-b / factory-c K3s 접근
Hub EKS 운영 관측
ArgoCD / Grafana 운영 UI 제공
```

### 리소스 배치

```text
Public subnet
  - NAT Gateway
  - 필요 시 Admin UI ALB

Private App subnet
  - EKS Hub worker nodes
  - ArgoCD
  - Tailscale Operator / Connector
  - Prometheus Agent
  - Grafana
  - AWS Load Balancer Controller
```

현재 repo의 `infra/hub`는 이 2번 VPC의 초기 구현에 해당한다.

## Grafana 역할

클라우드 Grafana는 사용자용 Dashboard가 아니다.

현재 기준의 수집 흐름은 아래와 같다.

```text
Hub EKS
  -> Prometheus Agent
  -> AMP
  -> Grafana
```

현재 Grafana가 보는 대상:

```text
Prometheus Agent 자체
Kubernetes API server
EKS node metrics
prometheus.io/scrape: "true" annotation이 붙은 Hub 내부 Pod
```

현재 Grafana가 직접 보지 않는 대상:

```text
factory-a InfluxDB 센서 데이터
factory-a AI detection / audio detection 데이터
Lambda data processor Risk 계산 결과
Dashboard latest status
공장별 Risk Score
```

따라서 Grafana는 2번 VPC에 두고, 1번 VPC의 Dashboard와 역할을 분리한다.

```text
Grafana: 운영자/개발자용 시스템 관측 화면
Dashboard Web/API: 본사 관리자 또는 사용자용 제품 화면
```

1번 VPC 서비스의 운영 메트릭도 필요하면 AMP로 remote_write하고, Grafana는 AMP를 통해 조회한다. Grafana가 1번 VPC의 DB, Redis, OpenSearch에 직접 붙는 구조는 MVP에서 피한다.

## Dashboard Backend/API 경계

Dashboard Backend/API는 1번 VPC에 둔다.

다만 역할을 명확히 나눈다.

Dashboard Backend/API가 담당하는 것:

```text
공장별 최신 risk score 조회
latest status 조회
processed result 조회
이벤트 목록 조회
Dashboard Web에 필요한 요약 데이터 제공
```

Dashboard Backend/API가 담당하지 않는 것:

```text
raw 데이터 정규화
위험도 계산
event processing
replay 생성
near-miss aggregation
```

위 처리는 Data / Analytics workload로 분리한다.

```text
Lambda data processor
Replay Builder
Near-miss Aggregator
AI / analytics worker
```

## ArgoCD 구성

목표 구조는 Hub ArgoCD 중심이다.

2번 Control / Management VPC의 EKS Hub 안에 Hub ArgoCD를 두고, 이 ArgoCD가 `factory-a`, `factory-b`, `factory-c`의 Edge data-plane workload와 공통 spoke component 배포를 관리한다.

기준:

```text
Hub ArgoCD
factory-a / factory-b / factory-c 배포 관리
ApplicationSet 기반 factory별 배포
EKS multi-AZ node group과 Kubernetes scheduling으로 가용성 확보
필요 시 ArgoCD chart HA 옵션 검토
Git repository와 Helm values를 source of truth로 유지
```

`factory-a`에 기존 Local ArgoCD가 있는 경우에는 전환 기간 동안 유지한다.

전환 기간의 기준:

```text
factory-a Local ArgoCD 유지
신규 Edge data-plane은 Hub ArgoCD로 배포
기존 workload를 단계적으로 Hub ArgoCD로 이관
이관 완료 후 Local ArgoCD 제거 또는 비활성화
```

장기 목표는 공장별 Local ArgoCD를 계속 늘리는 구조가 아니라 Hub ArgoCD 중심 운영이다. 세부 이관 계획은 `docs/planning/14_argocd_hub_migration_plan.md`를 따른다.

가용영역별로 독립 ArgoCD를 두는 방식은 MVP 기준에서는 사용하지 않는다.

DR은 ArgoCD 인스턴스를 여러 개 두는 방식보다, Git/Terraform/Ansible로 재현 가능하게 만드는 쪽을 우선한다.

## Tailscale 구성

MVP는 Tailscale을 유지한다.

Tailscale은 2번 Control / Management VPC의 Hub-Spoke 제어망으로 본다.

```text
ArgoCD
  -> Tailscale
  -> factory-a / factory-b / factory-c K3s API
```

대체 방식인 Site-to-Site VPN, Transit Gateway, Direct Connect, self-hosted WireGuard는 운영 복잡도가 높으므로 MVP 이후에 검토한다.

MVP에서 지킬 원칙:

```text
factory별 tag / ACL 분리
운영자 단말과 시스템 노드 권한 분리
ArgoCD용 Kubernetes 권한 최소화
Tailscale 경로를 DB / 분석 저장소 접근망으로 확장하지 않기
Dashboard / Lambda data processor 접근을 Tailscale에 의존시키지 않기
```

## VPC 간 연결 원칙

MVP에서는 1번 VPC와 2번 VPC를 직접 강하게 연결하지 않는다.

우선순위는 아래와 같다.

```text
1. 관리형 서비스와 IAM 권한으로 경계 연결
2. S3 / DynamoDB / AMP 같은 공유 계약 사용
3. 직접 DB 접근이나 private service 호출은 후순위
```

권장 흐름:

```text
factory telemetry
  -> IoT Core
      -> IoT Rule -> S3 raw
      -> Lambda data processor
          -> DynamoDB LATEST/HISTORY
          -> S3 processed
  -> 1번 VPC Dashboard API가 조회

Hub / Data service metrics
  -> AMP
  -> 2번 VPC Grafana가 조회
```

직접 통신이 필요해지면 후속 단계에서 아래 중 하나를 검토한다.

```text
VPC Peering
Transit Gateway
PrivateLink
API Gateway + VPC Link
```

MVP에서는 Dashboard API가 2번 VPC의 ArgoCD, Grafana, EKS API, Tailscale에 직접 접근하지 않는다.

## 1 VPC 대안 정리

하나의 VPC로도 MVP 구성은 가능하다.

이 경우 네트워크 구조는 3티어로 본다.

```text
Public subnet
  - ALB
  - NAT Gateway

Private App subnet
  - ArgoCD
  - Tailscale
  - Grafana
  - Dashboard Backend/API
  - Lambda data processor integration

Private Data subnet
  - RDS
  - Redis
  - OpenSearch
```

다만 하나의 private app tier 안에 제어 plane과 Dashboard/API plane이 섞인다. 보안 경계, 작업 분담, 장기 확장성을 고려하면 2 VPC 구조가 더 적합하다.

## 현재 범위에서 제외하는 항목

아래 항목은 현재 명시된 범위가 아니므로 MVP 설계에서 제외한다.

```text
Fleet Controller 별도 서비스
공장별 Local ArgoCD 장기 운영 모델
가용영역별 독립 ArgoCD 2개 운영
Dashboard VPC와 Control VPC 간 상시 private DB 직접 연결
Tailscale 대체망 즉시 구현
```

Fleet Controller라는 별도 서비스는 현재 프로젝트 범위에 없다. 공장 목록과 설정은 우선 `configs/runtime/runtime-config.yaml`, Helm values, ArgoCD ApplicationSet, Dashboard API 조회 로직으로 처리한다. 이후 공장 등록/정책 변경을 UI에서 직접 관리해야 할 때 별도 서비스 도입을 재검토한다.

## 후속 작업

1. `infra/hub`를 2번 Control / Management VPC로 명확히 명명한다.
2. 1번 Data / Dashboard VPC Terraform root를 새로 설계한다.
3. Dashboard Web이 서버형인지 정적 SPA인지 확정한다.
4. Dashboard Backend/API와 Lambda data processor의 저장소 계약을 API 수준으로 문서화한다.
5. Data / Dashboard VPC의 저장소 후보를 확정한다.
   - MVP: DynamoDB LATEST/HISTORY, S3 `processed/`
   - 후속: RDS, Redis, OpenSearch
6. 1번 VPC workload의 메트릭을 AMP로 보낼지 결정한다.
7. ArgoCD HA 옵션은 M3/M4 이후 운영 안정화 단계에서 검토한다.

## 2026-05-14 수정 방향

이 문서의 이전 `Event Processor`와 `Risk Engine` 표현은 최신 MVP 기준에서 별도 장기 실행 서비스가 아니다.

최신 기준은 `docs/specs/data_storage_pipeline.md`를 따른다.

```text
IoT Core
  -> IoT Rule -> S3 raw
  -> Lambda data processor
      -> DynamoDB LATEST
      -> DynamoDB HISTORY
      -> S3 processed
Dashboard Backend/API
  -> DynamoDB + S3 processed read-only 조회
```

따라서 M3 Issue 2 ECR 범위에는 `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator`를 포함하지 않는다.
