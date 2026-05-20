# M5. VM Spoke 확장 - `factory-b`, `factory-c`

> **마일스톤 목표**: Mac mini(`factory-b`)와 Windows VM(`factory-c`)을 테스트베드형 Spoke로 추가한다.
> M3(배포 파이프라인)과 M4(데이터 플레인)가 `factory-a` 기준으로 검증된 후 진행한다.
> VM Spoke는 실센서/Longhorn/NFS 없이 Dummy data generator 기반으로 동작한다.
> 2026-05-20 기준 `factory-b/c` 테스트베드의 dummy generator는 Kubernetes 배포물이 아니라 VM 로컬 프로세스/스크립트로 시작한다. Hub ArgoCD는 공통 `edge-iot-publisher`를 배포하고, publisher는 worker node의 hostPath outbox(`/var/lib/aegis/outbox`)를 읽어 IoT Core로 전송한다.

---

## 2026-05-13 멘토링 반영: VM Spoke 검증 목적 보강

### 기존 초안

기존 M5 초안은 Mac mini VM과 Windows VM을 각각 `factory-b`, `factory-c` 테스트베드 Spoke로 추가하는 데 집중했다.

### 변경 이유

멘토링에서는 VM Spoke가 실제 공장을 완전히 대체하는 증거가 아니라는 점을 명확히 해야 한다는 피드백이 있었다. 고객 요구사항 관점에서는 초당 데이터 크기, 성공률/실패율, 지연시간처럼 무엇을 증명할지 정의해야 한다.

### 보강 방향

`factory-b/c`는 실제 센서 정확도 검증이 아니라 멀티 factory 흐름 검증용 테스트베드로 설명한다. 핵심 검증 대상은 factory별 클러스터 식별, ApplicationSet 배포, IoT topic 분리, S3 prefix 분리, latest status 반영, Risk Score 분리 계산, Dashboard 카드 분리 표시다.

### 2026-05-20 구현 방향 보강: 로컬 dummy source + hostPath outbox

테스트베드형 Spoke의 데이터 플레인은 운영형 `factory-a`와 같은 outbox 계약을 유지하되, outbox 생산자와 저장소만 다르게 둔다.

```text
factory-a:
  factory-a-log-adapter Pod
    -> Longhorn PVC /var/lib/aegis/outbox
    -> edge-iot-publisher Pod
    -> IoT Core

factory-b/c:
  VM local dummy generator script 또는 systemd service
    -> hostPath /var/lib/aegis/outbox on worker node
    -> edge-iot-publisher Pod
    -> IoT Core
```

이 방향을 선택한 이유는 `factory-b/c`의 목적이 저장소 HA 검증이 아니라 멀티 factory 배포/수집/분리 흐름 검증이기 때문이다. 따라서 `factory-b/c`에는 Longhorn을 넣지 않고, GitOps values에서 `outbox.type: hostPath`를 선택한다. `edge-iot-publisher`는 ArgoCD가 배포하고, dummy generator는 VM 로컬에서 시나리오를 수동 전환할 수 있게 한다.

---

## Issue 1 - [Spoke/K3s] Mac mini VM K3s 구성 (`factory-b`)

### 🎯 목표 (What & Why)

Mac mini(M4, 24GB)에 VM을 구성하고 K3s를 설치하여 `factory-b` Spoke 기반을 만든다.  
VM 기반 Spoke는 파이프라인 검증에 집중하므로 Longhorn, NFS, 버퍼링 구조는 제외한다.

### ✅ 완료 조건 (Definition of Done)

- [x] Mac mini에서 VM 구성 방식 결정 및 적용
  - 방식 예: UTM, Multipass, OrbStack 등
- [x] VM 스펙 결정 (CPU, 메모리, 디스크)
- [x] VM 내부 Ubuntu 또는 Debian 기반 OS 설치
- [x] K3s 2-node 경량 클러스터 설치
  - 제외 항목: Longhorn, NFS 티어링, 실센서 의존 구성
- [x] master node taint 유지
- [x] worker node에 workload label 적용
- [x] `factory-b` 기본 레이블 및 환경 설정 적용
  - `environment_type: vm-mac`
  - `input_module_type: dummy`
- [x] K3s 정상 동작 확인 (`kubectl get nodes`)

### 🔍 Acceptance Criteria

- `kubectl get nodes`에서 `factory-b` master/worker node `Ready` 상태
- master node에 `node-role.kubernetes.io/control-plane:NoSchedule` taint 유지
- worker node에 `aegis.workload-node=true` label 적용
- K3s 버전 확인 및 기록
- VM 재부팅 후에도 K3s 자동 시작 확인

---

## Issue 2 - [Spoke/K3s] Windows VM K3s 구성 (`factory-c`)

### 🎯 목표 (What & Why)

Windows 환경에 VM을 구성하고 K3s를 설치하여 `factory-c` Spoke 기반을 만든다.  
Windows + Linux VM 조합의 호환성과 K3s 동작을 검증하는 것이 이 이슈의 핵심이다.

### ✅ 완료 조건 (Definition of Done)

- [x] Windows 환경에서 VM 구성 방식 결정 및 적용
  - 방식 예: WSL2, Hyper-V, VirtualBox, VMware 등
- [x] VM 내부 Linux OS 설치 (Ubuntu 또는 Debian 권장)
- [x] K3s 2-node 경량 클러스터 설치
  - 제외 항목: `factory-b`와 동일 (`factory-a` 운영형 구성 제외)
- [x] master node taint 유지
- [x] worker node에 workload label 적용
- [x] `factory-c` 기본 레이블 및 환경 설정 적용
  - `environment_type: vm-windows`
  - `input_module_type: dummy`
- [x] K3s 정상 동작 확인
- [ ] Windows 호스트 재부팅 후 VM 및 K3s 복구 방식 확인

### 🔍 Acceptance Criteria

- `kubectl get nodes`에서 `factory-c` master/worker node `Ready` 상태
- master node에 `node-role.kubernetes.io/control-plane:NoSchedule` taint 유지
- worker node에 `aegis.workload-node=true` label 적용
- VM 구성 방식 및 K3s 버전 기록
- VM 재시작 후 K3s 자동 복구 확인

---

## Issue 3 - [Spoke/Tailscale] `factory-b`, `factory-c` Tailscale 참여 및 Hub 연결

### 🎯 목표 (What & Why)

두 VM Spoke를 Tailscale 네트워크에 참여시키고 Hub ArgoCD에서 접근 가능하게 한다.  
테스트베드형 Spoke는 운영형보다 상대적으로 넓은 접근 허용 범위를 가진다.

### ✅ 완료 조건 (Definition of Done)

- [x] `factory-b` VM에 Tailscale 설치 및 네트워크 참여
  - M2에서 발급한 `factory-b` Auth Key 사용
- [x] `factory-c` VM에 Tailscale 설치 및 네트워크 참여
  - M2에서 발급한 `factory-c` Auth Key 사용
- [x] Tailscale Admin 콘솔에서 두 노드 `Connected` 확인
- [x] EKS Hub에서 두 Spoke Tailscale IP로 K3s API 접근 확인
- [x] kubeconfig Tailscale IP 기반으로 각각 생성
  - `factory-b.kubeconfig`
  - `factory-c.kubeconfig`
- [x] EKS 환경에서 두 kubeconfig로 `kubectl get nodes` 성공

### 🔍 Acceptance Criteria

- EKS에서 `factory-b`, `factory-c` kubeconfig로 K3s API 접근 성공
- Tailscale Admin 콘솔에서 3개 Spoke 모두 `Connected` 상태

---

## Issue 4 - [배포/ArgoCD] ApplicationSet에 `factory-b`, `factory-c` 추가

### 🎯 목표 (What & Why)

M3에서 구성한 ApplicationSet에 `factory-b`, `factory-c` Spoke를 추가하여  
3개 공장 모두 중앙 Hub에서 배포 관리되는 구조를 완성한다.

### ✅ 완료 조건 (Definition of Done)

- [x] ArgoCD에 `factory-b`, `factory-c` 클러스터 등록
  - `argocd cluster add` 수동 실행이 아니라 `scripts/ansible/inventory/group_vars/hub_eks.yml`의 `aegis_spokes`에 각 공장 항목을 추가한다.
  - `hub_tailscale_bootstrap.yml`이 각 Spoke의 `argocd-manager` RBAC/token과 Hub ArgoCD cluster Secret을 생성한다.
  - `hub_tailscale_verify.yml`로 egress Service와 cluster Secret을 검증한다.
- [x] `factory-b`, `factory-c` values 파일 준비 및 검증
  - `environment_type`, `input_module_type`, 이미지/배포 대상 경로 반영
  - `factory-b/c`는 `outbox.type: hostPath`, `outbox.path: /var/lib/aegis/outbox` 기준
  - IoT Secret 준비 전에는 `edgeIotPublisher.enabled: false`로 Application 생성/sync만 먼저 확인 가능
- [x] ArgoCD ApplicationSet에 `factory-b`, `factory-c` values 경로 추가
- [x] ApplicationSet에서 `aegis-spoke-factory-b`, `aegis-spoke-factory-c` Application 자동 생성 확인

### 🔍 Acceptance Criteria

- ArgoCD UI에서 3개 Application 모두 확인
  - `aegis-spoke-factory-a` (운영형)
  - `aegis-spoke-factory-b` (테스트베드형)
  - `aegis-spoke-factory-c` (테스트베드형)
- `factory-b`, `factory-c` 클러스터가 ArgoCD 배포 대상으로 정상 등록됨
- ApplicationSet에서 두 Application이 자동 생성됨 확인

### 완료 기록 (2026-05-20)

- aegis-pi-gitops chart: `outbox.type: pvc|hostPath` 분기 구현 (commit `04f90b2`, remote push 완료)
  - `_helpers.tpl`: `aegis-spoke.outboxVolumeSource` helper 추가
  - `outbox-pvc.yaml`: `outbox.type == pvc`일 때만 생성
  - `edge-iot-publisher`, `factory-a-log-adapter`: helper 사용으로 전환
  - `envs/factory-a/values.yaml`: `outbox.type: pvc` 명시
  - `envs/factory-b/values.yaml`: `outbox.type: hostPath`, `placement.nodeSelector: aegis.workload-node=true`, `edgeIotPublisher.iot.secretName: aws-iot-factory-b-cert`
  - `envs/factory-c/values.yaml`: `outbox.type: hostPath`, `placement.nodeSelector: aegis.workload-node=true`, `edgeIotPublisher.iot.secretName: aws-iot-factory-c-cert`
- helm lint factory-a/b/c 모두 통과
- factory-b render: PVC 유지 확인 / factory-b/c publisher 활성화 render: PVC 없음, hostPath 확인

### 참고: factory-c-worker K3s node-ip 수정 (2026-05-20)

factory-c는 VirtualBox NAT 구조로 master/worker 모두 `10.0.2.15`로 K3s에 등록되는 문제가 있었다.
worker의 host-only 인터페이스(`enp0s8`) IP `192.168.56.20`은 netplan에 static으로 고정되어 있음을 확인했다.

```bash
# factory-c-worker에서 적용
sudo mkdir -p /etc/rancher/k3s
echo "node-ip: 192.168.56.20" | sudo tee /etc/rancher/k3s/config.yaml
sudo systemctl restart k3s-agent
```

적용 후 `kubectl get nodes -o wide`에서 `factory-c-worker` INTERNAL-IP가 `192.168.56.20`으로 갱신됨 확인.
단, factory-c master API server가 worker kubelet(`192.168.56.20:10250`)에 프록시할 때 여전히 502가 나는 케이스가 있다.
kubectl logs/exec는 이 경로를 쓰므로 불편하지만, pod 배포/스케줄링/outbox write에는 영향 없다.
kubelet 로그 프록시 문제 근본 원인은 추후 확인한다 (kubelet 인증서 SAN에 신규 IP 미포함 가능성).

---

## Issue 5 - [Spoke/Dummy Generator] 로컬 Dummy data generator 구현 및 실행

### 🎯 목표 (What & Why)

VM 환경에서 실센서 없이 표준 입력 스키마에 맞는 더미 canonical JSON을 생성하는 Dummy data generator를 구현한다.
IoT Core 전송은 M4에서 만든 공통 `edge-iot-publisher`를 재사용한다.
시나리오별(정상/주의/위험) 값 생성과 수동 전환이 가능해야 한다.

초기 구현은 Kubernetes Deployment가 아니라 VM 로컬 script 또는 systemd service로 둔다. 로컬 generator는 worker node의 `/var/lib/aegis/outbox`에 canonical JSON 파일을 쓰고, ArgoCD가 배포한 `edge-iot-publisher`가 같은 hostPath를 mount해 전송한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Dummy data generator 구현
  - 표준 입력 스키마 준수
  - `environment_type`: `vm-mac` / `vm-windows` 자동 설정
  - `input_module_type: dummy` 명시
- [ ] 시나리오 모드 구현 (수동 전환 방식)
  - `normal`: 정상 범위 값 생성
  - `warning`: 주의 범위 값 생성
  - `danger`: 위험 범위 값 생성
  - 구체 수치는 `docs/ops/03_test_checklist.md` 기반 테스트 후 보정
- [ ] 시나리오 전환 방법 구현 (예: CLI 인자, 환경변수, 로컬 config 파일)
- [ ] 공통 `edge-iot-publisher`와 같은 local spool/outbox 계약 사용
- [x] `factory-b/c` worker node에 `/var/lib/aegis/outbox` 생성 및 권한 설정
- [x] Helm chart가 `outbox.type: hostPath`일 때 PVC를 만들지 않고 hostPath volume을 mount하도록 수정
- [ ] IoT Core 연결 및 메시지 전송은 `edge-iot-publisher`로 처리
- [ ] `factory-b`, `factory-c`에서 로컬 generator 실행 또는 systemd 등록

### 🔍 Acceptance Criteria

- `factory-b`, `factory-c` worker node의 `/var/lib/aegis/outbox`에 더미 canonical JSON 파일 생성 확인
- ArgoCD에서 `factory-b`, `factory-c` Application `Synced` 확인
- IoT Secret 준비 후 `edge-iot-publisher` 파드 `Running` 확인
- ArgoCD에서 `factory-b`, `factory-c` Application `Synced` + `Healthy` 확인
- IoT Core에서 두 공장의 더미 메시지 수신 확인
- S3 raw에서 `raw/factory-b/...`, `raw/factory-c/...` prefix 분리 적재 확인
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

VM 로컬 Dummy data generator에서 생성된 데이터가 `factory-a`와 동일한 전송 계층으로
IoT Core → S3까지 흐르는지 확인한다.  
3개 Spoke 모두 Hub에서 배포/수집 가능한 상태를 완성한다.

> 실행 전 확인:
> M4의 Lambda data processor가 `factory_id` 기준으로 다중 공장을 식별하고,
> Grafana/Hub에서 3개 공장 상태를 구분해 조회할 수 있어야 한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] `factory-b` local dummy generator → hostPath outbox → `edge-iot-publisher` → IoT Core → S3 적재 확인
  - 경로: `s3://bucket/factory-b/...`
- [ ] `factory-c` local dummy generator → hostPath outbox → `edge-iot-publisher` → IoT Core → S3 적재 확인
  - 경로: `s3://bucket/factory-c/...`
- [ ] S3에서 3개 공장 데이터가 독립 경로에 분리 적재 확인
- [ ] `pipeline_status` 집계 대상에 `factory-b`, `factory-c` 추가

### 🔍 Acceptance Criteria

- S3 콘솔에서 `factory-a/`, `factory-b/`, `factory-c/` 경로에 각각 데이터 적재 확인
- 3개 공장 `pipeline_status` 집계 결과 확인 가능
- Grafana 또는 Hub 관제 기준에서 3개 공장 상태가 분리 표시됨
- Dummy data generator 중지 시 해당 공장 `pipeline_status` 이상 판정 확인
