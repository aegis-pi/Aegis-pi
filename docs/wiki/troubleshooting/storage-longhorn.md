# Storage / Longhorn Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - Longhorn 데이터 경로 없음

### 📌 현상 요약

Longhorn 설치 전 세 노드 모두 `/var/lib/longhorn` 경로가 없어 사전 확인이 실패했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: longhorn-system
- 관련 컴포넌트/버전: Longhorn
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. Longhorn 설치 전 노드 데이터 경로를 확인한다.
2. `df -h /var/lib/longhorn`을 실행한다.

### ✅ 기대 동작

Longhorn 기본 데이터 경로가 존재하고 디스크 용량을 확인할 수 있어야 한다.

### ❌ 실제 동작

```text
df: /var/lib/longhorn: No such file or directory
```

### 🔍 시도한 것들

- [x] 세 노드에 `/var/lib/longhorn` 생성
- [x] `df -h /var/lib/longhorn` 재확인

### 🚨 심각도

중

### 🗂️ 영역

Storage / Longhorn, OS / Raspberry Pi

### 💡 해결 방법

**근본 원인:**

Longhorn 설치 전 기본 데이터 경로가 아직 생성되지 않았다.

**해결 방법:**

세 노드에서 `sudo mkdir -p /var/lib/longhorn`을 실행하고 실제 디스크가 기대한 파티션에 매핑되는지 확인한다.

**재발 방지:**

Longhorn 설치 전 노드 준비 체크리스트에 데이터 경로 생성과 `df` 확인을 포함한다.

## 🐛 트러블슈팅 리포트 - Longhorn KernelModulesLoaded 조건 False

### 📌 현상 요약

Longhorn Node 조건에서 `KernelModulesLoaded=False`가 표시됐다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: longhorn-system
- 관련 컴포넌트/버전: Longhorn, Linux kernel module `dm_crypt`
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. Longhorn 설치 후 Node 조건을 확인한다.
2. `KernelModulesLoaded` 상태와 메시지를 확인한다.

### ✅ 기대 동작

Longhorn이 요구하는 kernel module이 로드되어 Node 조건이 `True`여야 한다.

### ❌ 실제 동작

```text
KernelModulesLoaded=False
Kernel modules [dm_crypt] are not loaded
```

### 🔍 시도한 것들

- [x] 세 노드에서 `dm_crypt` 로드
- [x] `/etc/modules-load.d/longhorn.conf`에 자동 로드 설정
- [x] `longhorn-manager` DaemonSet 재시작
- [x] Node 조건 재확인

### 🚨 심각도

상

### 🗂️ 영역

Storage / Longhorn, OS / Raspberry Pi

### 💡 해결 방법

**근본 원인:**

Longhorn이 필요로 하는 `dm_crypt` kernel module이 로드되어 있지 않았다.

**해결 방법:**

`sudo modprobe dm_crypt`로 즉시 로드하고, `echo dm_crypt | sudo tee /etc/modules-load.d/longhorn.conf`로 부팅 시 자동 로드되도록 설정한다.

**재발 방지:**

OS baseline에 Longhorn용 kernel module 사전 로드 설정을 포함한다.

## 🐛 트러블슈팅 리포트 - Longhorn LoadBalancer Service 삭제 지연

### 📌 현상 요약

ServiceLB에서 MetalLB로 전환하는 과정에서 기존 Longhorn LoadBalancer Service 삭제가 지연됐다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: longhorn-system
- 관련 컴포넌트/버전: Kubernetes Service, K3s ServiceLB, MetalLB
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. K3s ServiceLB로 `longhorn-frontend-lb`를 생성한다.
2. ServiceLB를 비활성화하고 MetalLB로 전환한다.
3. 기존 Service를 삭제한 뒤 같은 이름으로 재생성한다.

### ✅ 기대 동작

기존 Service가 정상 삭제되고 MetalLB용 Service를 재생성할 수 있어야 한다.

### ❌ 실제 동작

```text
longhorn-frontend-lb Service가 삭제 중 상태로 남아 같은 이름 재생성이 지연됨
```

### 🔍 시도한 것들

- [x] Service finalizer 확인
- [x] `service.kubernetes.io/load-balancer-cleanup` finalizer 제거
- [x] Service 삭제와 재생성 재시도

### 🚨 심각도

중

### 🗂️ 영역

Storage / Longhorn, LoadBalancer / MetalLB, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

ServiceLB 전환 과정에서 LoadBalancer cleanup finalizer가 남아 Service 삭제 완료를 막았다.

**해결 방법:**

기존 Service의 finalizer를 제거한 뒤 삭제와 재생성을 진행한다.

**재발 방지:**

LoadBalancer controller를 전환할 때 기존 Service의 finalizer와 controller ownership을 확인한다.

## 🐛 트러블슈팅 리포트 - Longhorn RWO PVC로 인한 AI failover 차단

### 📌 현상 요약

worker2 장애 시 AI Pod가 worker1로 이동하지 못하고 Longhorn RWO PVC Multi-Attach 문제로 `ContainerCreating`에 머물렀다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1, worker2
- 네임스페이스: ai-apps, longhorn-system
- 관련 컴포넌트/버전: Longhorn RWO PVC, Kubernetes VolumeAttachment, safe-edge-integrated-ai
- 발생 시각: 2026-04-29

### 🔁 재현 순서

1. `safe-edge-integrated-ai`가 Longhorn RWO PVC를 `/app/snapshots`에 마운트한 상태로 실행된다.
2. worker2의 `k3s-agent`를 중지하거나 네트워크를 끊는다.
3. AI Pod가 worker1로 재스케줄되는지 확인한다.
4. Pod event와 Longhorn VolumeAttachment를 확인한다.

### ✅ 기대 동작

worker2 장애 시 AI Pod가 worker1에서 Running 상태로 복구되어야 한다.

### ❌ 실제 동작

```text
FailedAttachVolume
Multi-Attach error for volume "pvc-..."
Volume is already used by pod(s) safe-edge-integrated-ai-...
```

기존 worker2 Pod 또는 VolumeAttachment가 stale 상태로 남아 worker1 attach를 막았다.

### 🔍 시도한 것들

- [x] VolumeAttachment와 기존 AI Pod 상태 확인
- [x] stale writer가 살아 있을 때 force detach가 위험하다는 점 확인
- [x] AI snapshot 저장소를 Longhorn RWO PVC에서 node-local hostPath로 전환
- [x] InfluxDB 데이터는 Longhorn PVC에 유지
- [x] worker2 `k3s-agent` 중지 후 AI/audio/BME failover 재검증

### 🚨 심각도

상

### 🗂️ 영역

Storage / Longhorn, Operations / DR, AI / Hardware

### 💡 해결 방법

**근본 원인:**

Longhorn RWO PVC는 split-brain을 막기 위해 기존 writer가 사라졌다는 보장이 없으면 다른 노드 attach를 거부한다. 네트워크/agent 장애에서는 기존 worker2의 Pod, containerd, VolumeAttachment가 즉시 사라진다고 보장할 수 없다.

**해결 방법:**

AI snapshot PVC를 제거하고 `/app/snapshots`를 node-local `hostPath`인 `/var/lib/safe-edge/snapshots`로 전환했다. 장기 보존은 후속 비동기 전송 계층에서 처리한다.

**재발 방지:**

RWO PVC를 failover가 필요한 active workload의 즉시 쓰기 경로에 두지 않는다. RWO 강제 detach는 기존 writer 종료가 확실히 보장될 때만 수동으로 수행한다.

