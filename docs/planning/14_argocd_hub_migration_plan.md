# ArgoCD Hub Migration Plan

상태: draft
기준일: 2026-05-09

## 목적

`factory-a` 로컬 ArgoCD가 관리하던 배포 ownership을 EKS Hub ArgoCD 중심으로 옮기는 경우의 장단점, 장애 시나리오, 확인 사항, 예상 일정을 정리한다.

이 문서는 즉시 실행 절차가 아니라, M3 배포 파이프라인 설계 전후에 ArgoCD 운영 모델을 결정하기 위한 계획 문서다.

## 목표 방향

실무 운영 기준으로는 Hub ArgoCD 중심 구조를 목표로 둔다.

```text
목표:
  EKS Hub ArgoCD가 factory-a / factory-b / factory-c 배포를 중앙 관리

전환:
  factory-a local ArgoCD는 즉시 제거하지 않고 전환 기간 동안 유지
```

전환 후 목표 구조:

```text
GitHub Actions
  -> ECR
  -> manifest / values update
  -> EKS Hub ArgoCD
  -> Tailscale
  -> factory-a / factory-b / factory-c K3s rollout
```

## 현재 구조

```text
factory-a local ArgoCD
  -> monitoring
  -> ai-apps
  -> 기존 Safe-Edge baseline

EKS Hub ArgoCD
  -> factory-a-log-adapter
  -> edge-iot-publisher
  -> dummy-data-generator
  -> factory-a/b/c 공통 spoke component
```

`factory-a` 로컬 ArgoCD는 기존 Safe-Edge 기준선을 구축하고 검증하는 데 사용했다.

## 2026-05-13 멘토링 반영: CI/CD가 필요한 이유

### 기존 초안

기존 문서는 `factory-a` local ArgoCD를 Hub ArgoCD 중심으로 이관할 때의 장단점, 장애 시나리오, 전환 단계를 비교하는 데 집중했다. 이 비교 구조는 유지한다.

### 변경 이유

멘토링에서는 ArgoCD를 어디에 둘지보다, Aegis-Pi가 지속적인 CI/CD가 필요한 시스템인지 먼저 설명해야 한다는 피드백이 있었다.

### 보강 방향

Aegis-Pi의 CD 대상은 단순한 샘플 애플리케이션이 아니라 Edge AI와 데이터 수집 컴포넌트다. M6에서 일일 운영 리포트 초안이 추가되면, S3에 쌓인 사고 이미지와 이상 이벤트, Risk Score 결과를 바탕으로 Edge AI의 실패/불확실 사례와 설정 보정 후보를 찾게 된다.

```text
Edge AI 추론 / 센서 이벤트
  -> S3 raw / processed / latest status
  -> Risk Score + 일일 운영 리포트
  -> 모델/설정 업데이트 후보
  -> 운영자 승인
  -> GitHub Actions / ECR / Hub ArgoCD
  -> factory-a/b/c rollout
```

이 흐름 때문에 ArgoCD는 "배포 도구를 하나 더 둔 것"이 아니라, 운영 피드백을 Edge 워크로드 개선으로 연결하는 GitOps 제어 지점이다. MVP에서는 자동 재학습이나 자동 교체가 아니라, 운영자 승인 후 GitOps 배포까지를 범위로 둔다.

## 변경 후 구조

```text
EKS Hub ArgoCD
  -> factory-a Safe-Edge baseline
  -> factory-a Edge data-plane
  -> factory-b testbed workload
  -> factory-c testbed workload
  -> 공통 spoke component
```

`factory-a` local ArgoCD는 전환 완료 후 제거하거나 비활성화한다.

## 장점

### 운영 지점 단순화

```text
ArgoCD UI 하나
ApplicationSet 기준 하나
배포 상태 확인 지점 하나
GitHub Actions -> ArgoCD 흐름 하나
```

공장별 Local ArgoCD와 Hub ArgoCD 사이의 ownership 충돌을 줄인다.

### M3 배포 파이프라인과 정합성

M3 목표는 GitHub Actions, ECR, ArgoCD, factory rollout을 하나의 흐름으로 연결하는 것이다.

```text
GitHub Actions
  -> image build / ECR push
  -> Helm values update
  -> Hub ArgoCD sync
```

Hub ArgoCD 중심이면 ApplicationSet으로 `factory-a/b/c`를 같은 패턴으로 관리하기 쉽다.

### 멀티 factory 확장성

```text
factory-a: 운영형 Spoke
factory-b: Mac mini VM testbed Spoke
factory-c: Windows VM testbed Spoke
```

각 factory를 중앙 ApplicationSet과 values 구조로 관리할 수 있다.

### 운영 복잡도 감소

Hybrid ArgoCD를 유지하면 아래 질문이 계속 생긴다.

```text
이 리소스는 local ArgoCD가 관리하는가?
Hub ArgoCD가 관리하는가?
Prune은 어느 ArgoCD에서 허용하는가?
장애 시 어느 ArgoCD 상태를 기준으로 판단하는가?
```

Hub 중심으로 이관하면 이 경계 관리 비용을 줄일 수 있다.

## 단점과 감수해야 할 점

### 중앙 연결 장애 시 CD 중단

아래 장애 중 하나가 발생하면 Hub ArgoCD가 factory K3s API에 접근하지 못한다.

```text
EKS Hub 장애
Hub ArgoCD 장애
Tailscale 장애
factory 인터넷 장애
AWS 계정/리전 문제
```

이 경우 새 배포, rollback, sync, self-heal은 연결 복구 전까지 중단된다.

단, 이미 실행 중인 공장 workload는 계속 동작한다.

```text
K3s runtime은 계속 동작
기존 Deployment / Pod는 계속 실행
Longhorn / InfluxDB / local workload는 계속 운영
Kubernetes scheduler 기반 failover는 계속 동작
```

### 중앙 설정 실수의 영향 범위 증가

Hub ApplicationSet 또는 values 설정이 잘못되면 여러 factory에 동시에 영향을 줄 수 있다.

예시:

```text
잘못된 image tag
잘못된 namespace target
잘못된 prune 설정
잘못된 values override
잘못된 ApplicationSet generator
```

운영형 `factory-a`와 테스트베드 `factory-b/c`의 sync policy를 분리해야 한다.

### factory-a 로컬 자율 GitOps 약화

Hub/Tailscale 장애 중에는 `factory-a` 내부에서 GitOps 기반 새 배포를 수행할 수 없다.

현재 판단상 `factory-a`는 안정화 후 자주 CD할 대상이 아니므로, 이 단점은 MVP에서는 수용 가능성이 있다.

## 장애 시나리오 평가

| 시나리오 | 영향 | 운영 판단 |
| --- | --- | --- |
| Hub 정상, 모든 factory 연결 정상 | 중앙 배포/관측 정상 | Hub ArgoCD 중심 구조가 가장 단순 |
| Tailscale 장애 | Hub ArgoCD가 factory sync 불가 | 기존 workload는 계속 실행, 변경은 복구 후 진행 |
| EKS Hub 장애 | 모든 factory CD 중단 | runtime 영향은 제한적, 배포 변경은 중단 |
| factory 인터넷 장애 | 해당 factory만 중앙 CD 중단 | local workload 유지, 연결 복구 후 sync |
| 잘못된 Hub ApplicationSet 배포 | 여러 factory 동시 영향 가능 | factory별 sync policy와 승인 정책 필요 |
| factory-a 긴급 배포 필요 | Hub 연결 없으면 곤란 | 실제 긴급 CD 필요성이 낮은지 운영 기록 필요 |

## 전환 전략

Local ArgoCD를 즉시 제거하지 않는다.

```text
1단계: 병행 준비
  - factory-a local ArgoCD는 기존 baseline 유지
  - Hub ArgoCD는 신규 Edge data-plane 또는 영향 적은 workload부터 관리

2단계: Hub 관리 범위 확대
  - Hub ArgoCD에서 factory-a 기존 workload diff 확인
  - manual sync로 일부 workload 이관
  - prune / self-heal은 초기 비활성 또는 제한

3단계: local ArgoCD 비활성화
  - local ArgoCD auto-sync 중지
  - Hub ArgoCD 기준으로 Sync/Healthy 확인
  - rollback 절차 검증

4단계: local ArgoCD 제거 또는 보관
  - 필요성이 낮으면 제거
  - 불확실하면 read-only 또는 비활성 상태로 일정 기간 보관
```

## 예상 일정

| 범위 | 예상 기간 |
| --- | --- |
| 빠른 이관 | 1~2일 |
| 검증 포함 안정 이관 | 3~5일 |
| 문서/롤백/운영 절차 포함 | 1주일 |

실무 계획에는 1주일을 잡고, 실제 구현은 3~5일 완료를 목표로 한다.

## 권장 작업 일정

### Day 1: 현황 inventory

```text
local ArgoCD Application 목록 확인
local ArgoCD가 관리 중인 namespace/resource 정리
Git repo/path/values 구조 확인
Hub ArgoCD에서 factory-a cluster 접근 확인
Tailscale 경로와 kubeconfig 확인
```

### Day 2: Hub ArgoCD Application 구성

```text
factory-a Application 또는 ApplicationSet 생성
sync policy 보수적으로 설정
prune 비활성 또는 제한
dry-run / diff 중심 확인
local ArgoCD와 ownership 충돌 확인
```

### Day 3: 부분 이관

```text
factory-a-log-adapter / edge-iot-publisher 또는 영향 적은 workload부터 Hub ArgoCD sync
기존 workload 이관 후보 검토
Pod 재생성 여부 확인
Service IP / PVC / Secret 영향 확인
```

### Day 4: local ArgoCD 비활성화 리허설

```text
local ArgoCD auto-sync 중지
Hub ArgoCD 기준 OutOfSync / Healthy 확인
rollback 테스트
Tailscale 일시 장애 시 기존 workload 유지 확인
```

### Day 5: 문서화 및 정리

```text
운영 절차 갱신
rollback 절차 기록
local ArgoCD 제거 여부 결정
제거 시 argocd namespace cleanup 계획 작성
```

## 변경 전 확인 사항

### local ArgoCD inventory

```text
Application 목록
AppProject 목록
Repository 설정
자동 sync 여부
prune / self-heal 여부
관리 namespace
관리 cluster resource
```

### factory-a 리소스 영향

특히 아래 리소스는 재생성되면 안 된다.

```text
Longhorn PVC
InfluxDB PVC
MetalLB LoadBalancer IP
Kubernetes Secret
Service type / static IP
node affinity / toleration
failback 관련 설정
```

### Hub ArgoCD 접근

```text
Hub ArgoCD -> Tailscale -> factory-a K3s API 접근
factory-a cluster secret
RBAC 권한 범위
TLS serverName / CA 설정
sync dry-run 가능 여부
```

### 정책

```text
factory-a 운영형 sync policy
factory-b/c 테스트베드 sync policy
prune 허용 범위
self-heal 허용 범위
rollback 방식
장애 시 변경 freeze 기준
```

## 권장 sync policy

### factory-a

```text
초기: manual sync
초기: prune disabled
초기: self-heal disabled 또는 제한
검증 후: 제한적 auto-sync 검토
```

### factory-b/c

```text
auto-sync 허용 가능
prune은 초기 제한 후 검토
self-heal 허용 가능
테스트베드 기준 빠른 반복 배포 허용
```

## Rollback 기준

이관 중 문제가 생기면 아래 순서로 복구한다.

```text
1. Hub ArgoCD sync 중지
2. 문제 Application rollback 또는 이전 values로 되돌림
3. local ArgoCD auto-sync 재활성화 여부 판단
4. PVC / Service / Secret 손상 여부 확인
5. factory-a start_test 또는 핵심 smoke test 실행
```

## 최종 판단

MVP와 M3 배포 파이프라인 기준으로는 Hub ArgoCD 중심 구조가 더 단순하다.

다만 `factory-a` local ArgoCD는 이미 검증된 운영 구성 요소이므로 즉시 제거하지 않는다. 신규 cloud integration workload부터 Hub ArgoCD로 관리하고, 일정 기간 운영 후 local ArgoCD 필요성이 낮다고 확인되면 기존 Safe-Edge baseline까지 Hub ArgoCD로 이관한다.

요약:

```text
목표 구조: Hub ArgoCD 중심 CD
전환 방식: factory-a local ArgoCD 단계적 이관
계획 기간: 1주일
구현 목표: 3~5일
핵심 안전장치: manual sync, prune 제한, PVC/Secret/Service 영향 확인
```
