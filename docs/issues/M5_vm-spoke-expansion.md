# M5. VM Spoke 확장 - `factory-b`, `factory-c`

> **마일스톤 목표**: Mac mini(`factory-b`)와 Windows VM(`factory-c`)을 테스트베드형 Spoke로 추가한다.  
> M3(배포 파이프라인)과 M4(데이터 플레인)가 `factory-a` 기준으로 검증된 후 진행한다.  
> VM Spoke는 실센서/Longhorn/NFS 없이 Dummy Sensor 기반으로 동작한다.

---

## Issue 1 - [Spoke/K3s] Mac mini VM K3s 구성 (`factory-b`)

### 🎯 목표 (What & Why)

Mac mini(M4, 24GB)에 VM을 구성하고 K3s를 설치하여 `factory-b` Spoke 기반을 만든다.  
VM 기반 Spoke는 파이프라인 검증에 집중하므로 Longhorn, NFS, 버퍼링 구조는 제외한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Mac mini에서 VM 구성 방식 결정 및 적용
  - 방식 예: UTM, Multipass, OrbStack 등
- [ ] VM 스펙 결정 (CPU, 메모리, 디스크)
- [ ] VM 내부 Ubuntu 또는 Debian 기반 OS 설치
- [ ] K3s 단일 노드 또는 경량 클러스터 설치
  - 제외 항목: Longhorn, NFS 티어링, 실센서 의존 구성
- [ ] `factory-b` 기본 레이블 및 환경 설정 적용
  - `environment_type: vm-mac`
  - `input_module_type: dummy`
- [ ] K3s 정상 동작 확인 (`kubectl get nodes`)

### 🔍 Acceptance Criteria

- `kubectl get nodes`에서 `factory-b` 노드 `Ready` 상태
- K3s 버전 확인 및 기록
- VM 재부팅 후에도 K3s 자동 시작 확인

---

## Issue 2 - [Spoke/K3s] Windows VM K3s 구성 (`factory-c`)

### 🎯 목표 (What & Why)

Windows 환경에 VM을 구성하고 K3s를 설치하여 `factory-c` Spoke 기반을 만든다.  
Windows + Linux VM 조합의 호환성과 K3s 동작을 검증하는 것이 이 이슈의 핵심이다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Windows 환경에서 VM 구성 방식 결정 및 적용
  - 방식 예: WSL2, Hyper-V, VirtualBox, VMware 등
- [ ] VM 내부 Linux OS 설치 (Ubuntu 또는 Debian 권장)
- [ ] K3s 단일 노드 또는 경량 클러스터 설치
  - 제외 항목: `factory-b`와 동일 (`factory-a` 운영형 구성 제외)
- [ ] `factory-c` 기본 레이블 및 환경 설정 적용
  - `environment_type: vm-windows`
  - `input_module_type: dummy`
- [ ] K3s 정상 동작 확인
- [ ] Windows 호스트 재부팅 후 VM 및 K3s 복구 방식 확인

### 🔍 Acceptance Criteria

- `kubectl get nodes`에서 `factory-c` 노드 `Ready` 상태
- VM 구성 방식 및 K3s 버전 기록
- VM 재시작 후 K3s 자동 복구 확인

---

## Issue 3 - [Spoke/Tailscale] `factory-b`, `factory-c` Tailscale 참여 및 Hub 연결

### 🎯 목표 (What & Why)

두 VM Spoke를 Tailscale 네트워크에 참여시키고 Hub ArgoCD에서 접근 가능하게 한다.  
테스트베드형 Spoke는 운영형보다 상대적으로 넓은 접근 허용 범위를 가진다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `factory-b` VM에 Tailscale 설치 및 네트워크 참여
  - M2에서 발급한 `factory-b` Auth Key 사용
- [ ] `factory-c` VM에 Tailscale 설치 및 네트워크 참여
  - M2에서 발급한 `factory-c` Auth Key 사용
- [ ] Tailscale Admin 콘솔에서 두 노드 `Connected` 확인
- [ ] EKS Hub에서 두 Spoke Tailscale IP로 `ping` 성공
- [ ] kubeconfig Tailscale IP 기반으로 각각 생성
  - `factory-b.kubeconfig`
  - `factory-c.kubeconfig`
- [ ] EKS 환경에서 두 kubeconfig로 `kubectl get nodes` 성공

### 🔍 Acceptance Criteria

- EKS에서 `factory-b`, `factory-c` kubeconfig로 K3s API 접근 성공
- Tailscale Admin 콘솔에서 3개 Spoke 모두 `Connected` 상태

---

## Issue 4 - [배포/ArgoCD] ApplicationSet에 `factory-b`, `factory-c` 추가

### 🎯 목표 (What & Why)

M3에서 구성한 ApplicationSet에 `factory-b`, `factory-c` Spoke를 추가하여  
3개 공장 모두 중앙 Hub에서 배포 관리되는 구조를 완성한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] ArgoCD에 `factory-b`, `factory-c` 클러스터 등록
  ```bash
  argocd cluster add factory-b --kubeconfig factory-b.kubeconfig
  argocd cluster add factory-c --kubeconfig factory-c.kubeconfig
  ```
- [ ] `factory-b`, `factory-c` values 파일 준비 및 검증
  - `environment_type`, `input_module_type`, 이미지/배포 대상 경로 반영
- [ ] ArgoCD ApplicationSet에 `factory-b`, `factory-c` values 경로 추가
- [ ] ApplicationSet에서 `aegis-spoke-factory-b`, `aegis-spoke-factory-c` Application 자동 생성 확인

### 🔍 Acceptance Criteria

- ArgoCD UI에서 3개 Application 모두 확인
  - `aegis-spoke-factory-a` (운영형)
  - `aegis-spoke-factory-b` (테스트베드형)
  - `aegis-spoke-factory-c` (테스트베드형)
- `factory-b`, `factory-c` 클러스터가 ArgoCD 배포 대상으로 정상 등록됨
- ApplicationSet에서 두 Application이 자동 생성됨 확인

---

## Issue 5 - [Spoke/Dummy Sensor] Dummy Sensor 모듈 구현 및 배포

### 🎯 목표 (What & Why)

VM 환경에서 실센서 없이 표준 입력 스키마에 맞는 더미 데이터를 생성하여 IoT Core로 전송하는 Dummy Sensor 모듈을 구현한다.  
시나리오별(정상/주의/위험) 값 생성과 수동 전환이 가능해야 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Dummy Sensor 모듈 구현
  - 표준 입력 스키마 준수
  - `environment_type`: `vm-mac` / `vm-windows` 자동 설정
  - `input_module_type: dummy` 명시
- [ ] 시나리오 모드 구현 (수동 전환 방식)
  - `normal`: 정상 범위 값 생성
  - `warning`: 주의 범위 값 생성
  - `danger`: 위험 범위 값 생성
  - 구체 수치는 `docs/ops/test_checklist.md` 기반 테스트 후 보정
- [ ] 시나리오 전환 방법 구현 (예: 환경변수, ConfigMap)
- [ ] IoT Core 연결 및 메시지 전송 로직 (Edge Agent와 동일 방식)
- [ ] `factory-b`, `factory-c`에 각각 배포

### 🔍 Acceptance Criteria

- `factory-b`, `factory-c` K3s에서 Dummy Sensor 파드 `Running`
- ArgoCD에서 `factory-b`, `factory-c` Application `Synced` + `Healthy` 확인
- IoT Core에서 두 공장의 더미 메시지 수신 확인
- 시나리오 전환 후 생성되는 값의 범위 변화 확인

---

## Issue 6 - [배포/ArgoCD] 테스트베드형 동기화 정책 및 자동 롤백 적용

### 🎯 목표 (What & Why)

`factory-b`, `factory-c`에 운영형(`factory-a`)과 차별화된 배포 정책을 적용한다.  
테스트베드형은 빠른 반영과 자동 롤백을 허용하여 검증 사이클을 단축한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 테스트베드형 Sync 정책 적용
  - 자동 Sync (운영형보다 빠른 주기)
  - Self-heal 활성화
- [ ] 배포 실패 시 자동 롤백 설정
  - 운영형은 수동 확인 / 테스트베드형은 자동 롤백
- [ ] 정책 차이가 ArgoCD ApplicationSet에 명확히 반영됨 확인
- [ ] 정책 내용을 배포 파이프라인 관련 문서에 반영

### 🔍 Acceptance Criteria

- 의도적으로 잘못된 이미지 배포 후 `factory-b` 자동 롤백 확인
- `factory-a`는 동일 상황에서 자동 롤백 없이 `Degraded` 상태 유지
- ArgoCD UI에서 두 Spoke의 동기화 정책 차이 확인 가능

---

## Issue 7 - [검증/데이터] `factory-b`, `factory-c` 데이터 플레인 연결 확인

### 🎯 목표 (What & Why)

Dummy Sensor에서 생성된 데이터가 `factory-a`와 동일한 파이프라인으로  
IoT Core → S3까지 흐르는지 확인한다.  
3개 Spoke 모두 Hub에서 배포/수집 가능한 상태를 완성한다.

> 실행 전 확인:
> M4의 `pipeline-status-aggregator`가 `factory_id` 기준으로 다중 공장을 식별하고,
> Grafana/Hub에서 3개 공장 상태를 구분해 조회할 수 있어야 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `factory-b` 더미 데이터 → IoT Core → S3 적재 확인
  - 경로: `s3://bucket/factory-b/...`
- [ ] `factory-c` 더미 데이터 → IoT Core → S3 적재 확인
  - 경로: `s3://bucket/factory-c/...`
- [ ] S3에서 3개 공장 데이터가 독립 경로에 분리 적재 확인
- [ ] `pipeline_status` 집계 대상에 `factory-b`, `factory-c` 추가

### 🔍 Acceptance Criteria

- S3 콘솔에서 `factory-a/`, `factory-b/`, `factory-c/` 경로에 각각 데이터 적재 확인
- 3개 공장 `pipeline_status` 집계 결과 확인 가능
- Grafana 또는 Hub 관제 기준에서 3개 공장 상태가 분리 표시됨
- Dummy Sensor 중지 시 해당 공장 `pipeline_status` 이상 판정 확인
