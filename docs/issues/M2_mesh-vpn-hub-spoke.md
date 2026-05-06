# M2. Mesh VPN + Hub-Spoke 연결

> **마일스톤 목표**: Tailscale을 기반으로 EKS Hub와 `factory-a` Spoke를 연결한다.  
> Hub(M1)와 Spoke(M0)가 모두 구성된 상태에서 진행하며,  
> 이 마일스톤이 완료되어야 ArgoCD 기반 배포(M3)와 데이터 플레인(M4)이 가능해진다.

---

## 수정 이력

| 날짜 | 버전 | 내용 |
| --- | --- | --- |
| 2026-05-04 | rev-20260504-01 | Issue 3에 ArgoCD UI Tailscale private access 전환과 EKS API endpoint CIDR 축소 기준을 추가 |
| 2026-05-06 | rev-20260506-01 | Issue 1 Tailscale Tailnet/Auth Key 정책, 키 보관 방식, 장애 대응 원칙을 문서화 |
| 2026-05-06 | rev-20260506-02 | Tailscale Hub-Spoke 실제 진행 절차 runbook 참조를 추가 |

---

## Issue 1 - [Mesh/Tailscale] 계정 및 Spoke별 키 발급 정책 수립

### 🎯 목표 (What & Why)

Tailscale 네트워크의 인증/키 관리 정책을 먼저 수립한다.  
키가 Spoke별로 분리 발급되어야 개별 Spoke의 접근을 독립적으로 제어할 수 있다.  
정책 없이 키를 나누면 이후 운영 중 Tailscale 장애 대응이 어려워진다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Tailscale 계정 생성 및 Tailnet 구성
- [x] Spoke별 Auth Key 발급 방식 결정
  - `factory-a`, `factory-b`, `factory-c`, EKS Hub 각각 별도 키
- [x] Reusable Key vs One-time Key 정책 결정 및 기록
- [x] 키 보관 방법 결정 (Secret, 환경변수 등)
- [x] Tailscale 장애 시 대응 원칙 기록
  - 운영형(`factory-a`): 배포 중단, 보수 판단
  - 테스트베드형(`factory-b`, `factory-c`): 검증 중단, 재시도
- [x] 접근 정책을 Mesh VPN 관련 문서에 반영

### 🔍 Acceptance Criteria

- Tailscale Admin 콘솔에서 Tailnet 생성 확인
- 각 환경별 Auth Key 생성 확인
- 키 관리 정책 문서화 완료

### 진행 상태

- 상태: 정책 수립 완료, Tailnet 생성 및 실제 Auth Key 발급 대기
- 정책 문서: `infra/mesh-vpn/README.md`
- 실행 절차: `docs/ops/20_tailscale_hub_spoke_runbook.md`
- 실제 키 값, Tailnet 이름, 계정 이메일, Secret 값은 issue/document에 기록하지 않는다.
- Tailnet 생성과 Auth Key 발급은 Tailscale Admin 콘솔에서 수행한 뒤 이 섹션과 `MASTER_CHECKLIST.md`를 갱신한다.

### 실행 절차 문서

Tailscale Admin Console 설정, OAuth client 생성, Spoke별 Auth Key 생성, Hub EKS Tailscale Operator 설치, Spoke Tailnet 참여, Tailscale IP 기반 kubeconfig 생성, ArgoCD cluster 등록 순서는 `docs/ops/20_tailscale_hub_spoke_runbook.md`를 따른다.

이 issue 본문에는 정책과 완료 상태만 남기고, 실제 실행 명령과 순서는 runbook에서 관리한다. secret 값은 runbook, issue, evidence, Git 어디에도 기록하지 않는다.

### 정책 결정

#### Tailnet 기준

- Aegis-Pi 전용 Tailnet을 사용한다.
- Tailscale은 Hub가 Spoke K3s API에 접근하고 ArgoCD가 배포를 제어하기 위한 운영/제어망이다.
- 관리자 대시보드 접근망은 Tailscale이 아니라 Dashboard VPC로 분리한다.
- Tailnet device 이름은 공장/역할을 바로 식별할 수 있게 아래 기준으로 둔다.
  - `factory-a-master`
  - `factory-b`
  - `factory-c`
  - `aegis-hub`

#### Auth Key 발급 단위

환경별로 Auth Key를 분리한다. 한 키를 여러 공장 또는 Hub에 재사용하지 않는다.

| 대상 | 용도 | 기본 키 유형 | 태그/식별 기준 | 비고 |
| --- | --- | --- | --- | --- |
| `factory-a` | 운영형 Raspberry Pi master | One-off, pre-approved, tagged | `tag:aegis-spoke-prod`, `tag:factory-a` | 초기 M2에서는 master만 참여한다. Worker 노드는 제외한다. |
| `factory-b` | Mac VM 테스트베드 | One-off 우선, VM 재생성 반복 시 short-lived reusable 허용 | `tag:aegis-spoke-testbed`, `tag:factory-b` | reusable 사용 시 7일 이하 만료 후 즉시 revoke한다. |
| `factory-c` | Windows VM 테스트베드 | One-off 우선, VM 재생성 반복 시 short-lived reusable 허용 | `tag:aegis-spoke-testbed`, `tag:factory-c` | reusable 사용 시 7일 이하 만료 후 즉시 revoke한다. |
| EKS Hub | ArgoCD/운영 제어망 | Issue 3 운영 방식 결정 후 발급 | `tag:aegis-hub` | Operator/DaemonSet/Subnet Router 방식 결정 전 실제 발급하지 않는다. |

#### One-off vs Reusable 원칙

- 기본값은 One-off Auth Key다.
- 운영형 `factory-a`에는 reusable key를 사용하지 않는다.
- 테스트베드형 `factory-b`, `factory-c`는 VM 삭제/재생성이 반복되는 동안에만 short-lived reusable key를 허용한다.
- reusable key는 7일 이하 만료로 만들고, VM bootstrap이 끝나면 즉시 revoke한다.
- EKS Hub는 Issue 3에서 운영 방식을 먼저 결정한다. 장기 실행 Subnet Router라면 one-off key를 쓰고, Kubernetes workload로 반복 생성되는 구조라면 Tailscale OAuth client 또는 짧은 수명의 key 발급 자동화를 검토한다.

#### 키 보관 원칙

- Auth Key, OAuth client secret, kubeconfig credential은 Git에 커밋하지 않는다.
- issue, README, evidence, screenshot, command output에 secret 값을 남기지 않는다.
- 로컬 임시 보관이 필요하면 repository 밖의 사용자 전용 경로에 둔다.
  - 예: `~/.aegis/secrets/tailscale/`
- Hub Kubernetes에서 사용할 값은 수동 생성 Kubernetes Secret 또는 후속 External Secrets/SOPS/SealedSecrets 후보로 관리한다.
- `.env`, `*.key`, `*tailscale*secret*`, `factory-*.kubeconfig`는 커밋 금지 대상으로 유지한다.

#### 접근 정책 초안

- Hub/ArgoCD 계층은 Spoke K3s API `tcp/6443`에 접근할 수 있어야 한다.
- 운영자 로컬 장비는 필요 시 Spoke SSH `tcp/22`와 K3s API `tcp/6443`에 접근한다.
- Spoke 간 직접 접근은 기본적으로 허용하지 않는다.
- Spoke에서 Hub/EKS/ArgoCD admin API로 직접 접근하는 흐름은 만들지 않는다.
- Dashboard VPC, Dashboard Web/API는 Tailscale, EKS API, ArgoCD API, Spoke K3s API에 접근하지 않는다.

#### 장애 대응 원칙

- `factory-a` 운영형: Tailscale 장애 시 ArgoCD 배포와 원격 운영을 중단한다. 로컬 Safe-Edge workload는 계속 운영하고, 복구 전까지 수동 배포/변경을 보류한다.
- `factory-b`, `factory-c` 테스트베드형: Tailscale 장애 시 해당 테스트를 중단하고 VM/Tailscale 재참여 후 재시도한다. 테스트 데이터 누락은 실패 evidence로 기록한다.
- Hub Tailscale 장애: 신규 Sync/검증은 중단한다. 이미 배포된 Spoke workload는 유지되며, 복구 후 ArgoCD cluster connection과 test Application sync를 다시 확인한다.

### GitHub Issue Comment Draft

- 상태: 부분 완료
- 진행 요약: Tailnet/Auth Key 발급 정책, one-off/reusable 사용 기준, secret 보관 방식, 운영형/테스트베드형 장애 대응 원칙을 문서화했다.
- 변경/확인: `docs/issues/M2_mesh-vpn-hub-spoke.md`, `infra/mesh-vpn/README.md`
- 검증: 정책 문서화는 완료했지만 Tailscale Admin 콘솔에서 Tailnet 생성과 실제 Auth Key 발급은 아직 수행하지 않았다.
- 후속: Tailscale Admin 콘솔에서 Aegis-Pi 전용 Tailnet을 만들고 `factory-a`, `factory-b`, `factory-c`, EKS Hub용 키를 정책에 맞게 발급한다. 실제 키 값은 문서와 Git에 기록하지 않는다.

---

## Issue 2 - [Mesh/Tailscale] `factory-a` Master Tailscale 참여 및 확인

### 🎯 목표 (What & Why)

`factory-a` K3s 클러스터의 Master 노드를 Tailscale 네트워크에 참여시킨다.  
Worker 노드는 초기 Mesh 참여 대상에서 제외하고, Master 중심 접근 정책을 유지한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Master 노드에 Tailscale 설치
- [ ] Auth Key로 Tailscale 네트워크 참여 (`tailscale up --authkey=...`)
- [ ] Tailscale IP 확인 및 기록 (`tailscale ip`)
- [ ] Tailscale Admin 콘솔에서 `factory-a` Master 노드 확인
- [ ] Tailscale IP로 Master SSH 접근 가능 확인

### 🔍 Acceptance Criteria

- Tailscale Admin 콘솔에서 `factory-a` Master 노드 `Connected` 상태
- 외부 환경(Host PC 또는 로컬)에서 Tailscale IP로 `ping` 응답
- Tailscale IP로 SSH 접근 성공

---

## Issue 3 - [Mesh/Tailscale] EKS Hub Tailscale 참여 및 확인

### 🎯 목표 (What & Why)

EKS Hub가 Tailscale 네트워크에 참여하여 각 Spoke Master에 도달할 수 있는 경로를 확보한다.  
EKS 환경에서는 Operator, DaemonSet, 또는 별도 Subnet Router 중 하나의 운영 방식을 먼저 결정해야 하며,  
이 결정이 이후 kubeconfig 접근 방식과 ArgoCD 연결 구조의 기준이 된다.

이 이슈에서 ArgoCD UI 접근 경로도 함께 정리한다. M1에서는 사용자가 로컬 PC에서 `kubectl port-forward`로 접속하고, M2 이후에는 public LoadBalancer 없이 Tailscale 기반 private access로 접근하는 것을 목표로 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] EKS 환경에서 Tailscale 운영 방식 결정 및 적용
  - 방식 예: Tailscale Operator, DaemonSet, 또는 별도 EC2 Subnet Router
- [ ] 선택한 방식의 장단점과 운영 기준 기록
- [ ] EKS Hub Tailscale 네트워크 참여
- [ ] Tailscale Admin 콘솔에서 EKS Hub 노드 확인
- [ ] EKS → `factory-a` Master Tailscale IP `ping` 성공
- [ ] ArgoCD UI 접근 경로를 Tailscale 기반 private access로 정리
- [ ] ArgoCD public `LoadBalancer`를 만들지 않는 기준 유지
- [ ] EKS API endpoint public CIDR `0.0.0.0/0` 축소 기준 수립

### 🔍 Acceptance Criteria

- 선택한 운영 방식이 문서에 명시되어 있음
- Tailscale Admin 콘솔에서 EKS Hub `Connected` 상태
- EKS 파드 내부에서 `factory-a` Master Tailscale IP `ping` 성공
- 사용자 로컬에서 Tailscale 경유로 ArgoCD UI 접근 가능
- EKS API endpoint 접근 범위가 MVP bootstrap 기준보다 좁아짐

---

## Issue 4 - [Mesh/Tailscale] kubeconfig Tailscale IP 기반 구성

### 🎯 목표 (What & Why)

ArgoCD가 `factory-a` K3s API에 접근할 수 있도록 kubeconfig를 Tailscale IP 기반으로 구성한다.  
이름 기반 주소는 후속 전환 시에만 사용하고, 현재는 Tailscale IP를 기준으로 한다.

> 실행 전 확인:
> K3s API 서버 인증서가 Tailscale IP 접속을 허용하는지 먼저 검증한다.
> 필요하면 API 서버 인증서 SAN 설정 또는 접근 방식을 조정한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `factory-a` K3s API 서버 인증서의 Tailscale IP 허용 여부 확인
- [ ] `factory-a` K3s API 서버 주소를 Tailscale IP로 교체한 kubeconfig 생성
  - 예: `server: https://<tailscale-ip>:6443`
- [ ] kubeconfig 유효성 확인
  - `kubectl --kubeconfig=factory-a.kubeconfig get nodes`
- [ ] kubeconfig 파일 보안 보관 방법 결정 (Secret 또는 파일)
- [ ] EKS 환경에서 해당 kubeconfig로 `factory-a` K3s API 접근 확인

### 🔍 Acceptance Criteria

- Tailscale IP 기반 K3s API 접속 시 TLS/인증서 오류 없이 `kubectl get nodes` 성공
- EKS 환경에서 `factory-a` kubeconfig로 `kubectl get nodes` 성공
- 응답 결과에 `master`, `worker-1`, `worker-2` 노드 확인

---

## Issue 5 - [배포/ArgoCD] `factory-a` Spoke 클러스터 등록

### 🎯 목표 (What & Why)

ArgoCD가 `factory-a` K3s 클러스터를 배포 대상으로 인식하게 한다.  
이 등록이 완료되어야 ArgoCD에서 Application/ApplicationSet을 생성해 Spoke에 배포할 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] ArgoCD CLI로 `factory-a` 클러스터 등록
  ```bash
  argocd cluster add factory-a --kubeconfig factory-a.kubeconfig
  ```
- [ ] ArgoCD UI에서 `factory-a` 클러스터 확인
- [ ] ArgoCD에서 `factory-a` 클러스터 상태 `Successful` 확인
- [ ] 클러스터 이름 및 레이블 규칙 기록 (추후 ApplicationSet 자동화 기반)

### 🔍 Acceptance Criteria

- ArgoCD UI Clusters 탭에서 `factory-a` 클러스터 확인
- 클러스터 상태 `Connection Status: Successful`
- ArgoCD에서 `factory-a`로 테스트 Application 배포 가능

---

## Issue 6 - [검증/ArgoCD] Hub → `factory-a` K3s API 접근 및 Sync 확인

### 🎯 목표 (What & Why)

Hub ArgoCD가 `factory-a` Spoke를 실제로 바라보고 Sync가 동작하는지 end-to-end로 검증한다.  
이 확인이 완료되어야 M2 마일스톤이 완료되고 M3(배포 파이프라인), M4(데이터 플레인)로 넘어갈 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 테스트용 최소 Application 정의
  - 예: 단순 Deployment + Service 형태의 `nginx` 또는 동등 수준 앱
  - 별도 테스트 namespace 사용
- [ ] ArgoCD에서 `factory-a` 대상 테스트 Application 생성
- [ ] ArgoCD Sync 동작 확인 (`Synced` 상태 전환)
- [ ] `factory-a` K3s에 테스트 리소스 배포 확인
  - `kubectl --kubeconfig=factory-a.kubeconfig get pods`
- [ ] Tailscale 연결이 끊어진 상태에서 ArgoCD Sync 실패 동작 확인 (장애 대응 검증)
- [ ] M2 완료 기준 및 결과를 Mesh VPN 관련 문서에 반영

### 🔍 Acceptance Criteria

- ArgoCD에서 `factory-a` 대상 Application `Synced` + `Healthy` 확인
- 테스트용 Application이 `factory-a`에 실제 배포되어 `Running` 확인
- `factory-a` K3s에 테스트 파드 배포 확인
- Tailscale 차단 시 ArgoCD에서 `Unknown` 또는 `OutOfSync` 상태 전환 확인
