# M2. Mesh VPN + Hub-Spoke 연결

> **마일스톤 목표**: Tailscale을 기반으로 EKS Hub와 `factory-a` Spoke를 연결한다.  
> Hub(M1)와 Spoke(M0)가 모두 구성된 상태에서 진행하며,  
> 이 마일스톤이 완료되어야 ArgoCD 기반 배포(M3)와 데이터 플레인(M4)이 가능해진다.

---

## 수정 이력

| 날짜 | 버전 | 내용 |
| --- | --- | --- |
| 2026-05-04 | rev-20260504-01 | Issue 3에 ArgoCD UI Tailscale private access 전환과 EKS API endpoint CIDR 축소 기준을 추가 |

---

## Issue 1 - [Mesh/Tailscale] 계정 및 Spoke별 키 발급 정책 수립

### 🎯 목표 (What & Why)

Tailscale 네트워크의 인증/키 관리 정책을 먼저 수립한다.  
키가 Spoke별로 분리 발급되어야 개별 Spoke의 접근을 독립적으로 제어할 수 있다.  
정책 없이 키를 나누면 이후 운영 중 Tailscale 장애 대응이 어려워진다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Tailscale 계정 생성 및 Tailnet 구성
- [ ] Spoke별 Auth Key 발급 방식 결정
  - `factory-a`, `factory-b`, `factory-c`, EKS Hub 각각 별도 키
- [ ] Reusable Key vs One-time Key 정책 결정 및 기록
- [ ] 키 보관 방법 결정 (Secret, 환경변수 등)
- [ ] Tailscale 장애 시 대응 원칙 기록
  - 운영형(`factory-a`): 배포 중단, 보수 판단
  - 테스트베드형(`factory-b`, `factory-c`): 검증 중단, 재시도
- [ ] 접근 정책을 Mesh VPN 관련 문서에 반영

### 🔍 Acceptance Criteria

- Tailscale Admin 콘솔에서 Tailnet 생성 확인
- 각 환경별 Auth Key 생성 확인
- 키 관리 정책 문서화 완료

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
