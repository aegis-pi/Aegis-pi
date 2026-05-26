# K3s / Kubernetes Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - K3s master INTERNAL-IP Wi-Fi 대역 오인식

### 📌 현상 요약

K3s master의 `INTERNAL-IP`가 내부망 `10.10.10.x`가 아니라 Wi-Fi 대역 `192.168.0.x`로 표시됐다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: kube-system
- 관련 컴포넌트/버전: K3s, flannel, Raspberry Pi dual NIC
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. K3s server를 기본 설정으로 설치한다.
2. `kubectl get nodes -o wide`를 실행한다.
3. master `INTERNAL-IP`를 확인한다.

### ✅ 기대 동작

master와 worker의 `INTERNAL-IP`는 K3s 내부망 `10.10.10.10/11/12`로 잡혀야 한다.

### ❌ 실제 동작

```text
master Ready control-plane 192.168.0.45
```

### 🔍 시도한 것들

- [x] K3s server 설치 인자에 `--node-ip 10.10.10.10` 추가
- [x] `--advertise-address 10.10.10.10` 추가
- [x] worker join 시 각 worker의 `--node-ip` 명시
- [x] `kubectl get nodes -o wide` 재확인

### 🚨 심각도

상

### 🗂️ 영역

K3s / Kubernetes, Network

### 💡 해결 방법

**근본 원인:**

K3s가 다중 NIC 환경에서 기본 인터페이스를 자동 선택하면서 Wi-Fi IP를 node IP로 사용했다.

**해결 방법:**

K3s server는 `--node-ip 10.10.10.10 --advertise-address 10.10.10.10`을 사용하고, worker agent도 각 노드의 내부망 IP를 `--node-ip`로 명시한다.

**재발 방지:**

K3s 설치 스크립트와 Ansible baseline에 node IP를 명시한다. dual NIC 클러스터에서는 자동 선택에 의존하지 않는다.

## 🐛 트러블슈팅 리포트 - Longhorn manager master 배치 누락

### 📌 현상 요약

Longhorn manager DaemonSet이 master에 배치되지 않아 Longhorn Node 목록에 worker만 보였다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: longhorn-system
- 관련 컴포넌트/버전: Longhorn, Kubernetes taint/toleration
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. K3s master에 control-plane taint가 있는 상태로 Longhorn을 설치한다.
2. `kubectl -n longhorn-system get ds longhorn-manager`를 확인한다.
3. Longhorn Node 목록을 확인한다.

### ✅ 기대 동작

Longhorn manager가 master, worker1, worker2 세 노드 모두에 배치되어야 한다.

### ❌ 실제 동작

```text
longhorn-manager DESIRED=2
Longhorn Node: worker1, worker2
```

### 🔍 시도한 것들

- [x] master의 `NoSchedule` taint 확인
- [x] Longhorn `taint-toleration` 설정 패치
- [x] `longhorn-manager` DaemonSet toleration 패치
- [x] Longhorn Node 목록 재확인

### 🚨 심각도

상

### 🗂️ 영역

K3s / Kubernetes, Storage / Longhorn

### 💡 해결 방법

**근본 원인:**

master에는 control-plane `NoSchedule` taint가 있고, Longhorn manager DaemonSet이 해당 taint를 toleration하지 못했다.

**해결 방법:**

Longhorn `taint-toleration` 설정과 `longhorn-manager` DaemonSet에 master/control-plane toleration을 추가한다.

**재발 방지:**

3-node edge 클러스터에서 master도 storage node로 쓸 경우 Longhorn 설치 절차에 taint/toleration 설정을 포함한다.

## 🐛 트러블슈팅 리포트 - 원격 비대화형 SSH에서 `i2cdetect` 명령 PATH 누락

### 📌 현상 요약

원격 비대화형 SSH로 `i2cdetect`를 실행하면 명령을 찾지 못했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker2
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: SSH, i2c-tools
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. master에서 worker2로 비대화형 SSH 명령을 실행한다.
2. `i2cdetect -y 1`을 호출한다.
3. 출력 오류를 확인한다.

### ✅ 기대 동작

원격 명령에서도 I2C scan이 실행되고 BME280 주소가 확인되어야 한다.

### ❌ 실제 동작

```text
bash: line 1: i2cdetect: command not found
```

### 🔍 시도한 것들

- [x] worker2에서 `i2cdetect` 설치 위치 확인
- [x] `/usr/sbin/i2cdetect -y 1` 절대 경로로 재실행
- [x] `0x76` 주소 확인

### 🚨 심각도

중

### 🗂️ 영역

K3s / Kubernetes, Automation / Script, OS / Raspberry Pi

### 💡 해결 방법

**근본 원인:**

비대화형 SSH shell의 PATH에 `/usr/sbin`이 없어 `i2cdetect`를 찾지 못했다.

**해결 방법:**

자동화 스크립트에서는 `/usr/sbin/i2cdetect`처럼 절대 경로를 사용한다.

**재발 방지:**

Ansible, SSH 원격 실행 스크립트에서는 system binary의 절대 경로를 쓰거나 PATH를 명시적으로 설정한다.

