# Network Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - worker2 k3s-agent flannel/default route 기동 실패

### 📌 현상 요약

worker2 재부팅 후 default route 부재와 flannel interface 자동 선택 문제로 `k3s-agent`가 올라오지 않았다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker2, master, worker1
- 네임스페이스: kube-system, metallb-system, longhorn-system
- 관련 컴포넌트/버전: K3s agent, flannel, MetalLB speaker, Longhorn CSI, systemd-timesyncd
- 발생 시각: 2026-04-29

### 🔁 재현 순서

1. worker2를 재부팅한다.
2. worker2에 default route가 없는 상태를 만든다.
3. `systemctl status k3s-agent`와 log를 확인한다.
4. MetalLB speaker와 Longhorn CSI 상태를 확인한다.

### ✅ 기대 동작

worker2의 `k3s-agent`가 `eth0` 기반 flannel 경로로 정상 기동하고 Node가 Ready가 되어야 한다.

### ❌ 실제 동작

```text
worker2: NotReady
k3s-agent: activating 반복
flannel exited: failed to get default interface: unable to find default route
certificate not valid before 경고
MetalLB speaker CrashLoopBackOff
Longhorn CSI CrashLoopBackOff
```

### 🔍 시도한 것들

- [x] 세 노드 K3s 실행 옵션에 `--flannel-iface eth0` 명시
- [x] systemd time sync 활성화
- [x] worker2에 service CIDR route 복구 service 추가
- [x] MetalLB speaker와 Longhorn CSI Pod 재생성
- [x] `safe-edge-preflight-repair.sh --check/--repair` 경량 복구 스크립트 추가

### 🚨 심각도

상

### 🗂️ 영역

Network, K3s / Kubernetes, Storage / Longhorn, LoadBalancer / MetalLB

### 💡 해결 방법

**근본 원인:**

flannel은 기본 인터페이스를 자동 선택하려고 했지만 worker2에 default route가 없어 실패했다. 동시에 노드별 flannel public IP가 `wlan0`와 `eth0`로 섞일 위험이 있었다.

**해결 방법:**

master/worker 모두 K3s 실행 옵션에 `--flannel-iface eth0`를 명시한다. 시간 동기화와 worker2 service CIDR route 복구 service를 적용하고, 이전 네트워크 상태에서 CrashLoopBackOff가 된 Pod는 재생성한다.

**재발 방지:**

K3s CNI interface는 dual NIC 환경에서 자동 선택에 맡기지 않는다. OS baseline에 flannel iface, time sync, service CIDR route 점검을 포함한다.

## 🐛 트러블슈팅 리포트 - `start_test.yml` Tailscale 검증 실패와 master `wlan0` 인터넷 단절

### 📌 현상 요약

`start_test.yml`의 Tailscale 검증이 실패했고, 원인은 master `wlan0` 단절로 인한 인터넷/default route/DNS 부재였다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Tailscale, NetworkManager, Ansible `start_test.yml`, wlan0
- 발생 시각: 2026-05-08

### 🔁 재현 순서

1. master의 `wlan0` Wi-Fi 연결이 끊긴 상태를 만든다.
2. `scripts/ansible/playbooks/start_test.yml`을 실행한다.
3. Tailscale 검증 task와 master network 상태를 확인한다.

### ✅ 기대 동작

master가 `wlan0` default route를 통해 Tailscale control plane에 접근하고, Tailscale hostname/IP 검증이 통과해야 한다.

### ❌ 실제 동작

```text
Tailscale is not connected as expected on factory-a master
tailscale status --self: NoState / logged out
ping 8.8.8.8: Network is unreachable
getent hosts controlplane.tailscale.com: Temporary failure in name resolution
wlan0: disconnected
```

### 🔍 시도한 것들

- [x] master `nmcli dev status`, `ip route`, DNS 상태 확인
- [x] Wi-Fi profile 삭제 후 재생성
- [x] `wlan0` route metric과 default route 정책 복구
- [x] `tailscaled` 재시작
- [x] `start_test.yml` 재검증

### 🚨 심각도

상

### 🗂️ 영역

Network, Automation / Script

### 💡 해결 방법

**근본 원인:**

factory-a master의 인터넷 경로는 `wlan0` default route에 의존한다. `wlan0` 연결이 끊기면 DNS와 Tailscale control plane 접근이 모두 실패한다.

**해결 방법:**

기존 Wi-Fi profile을 삭제하고 재생성한 뒤 `wlan0`에 DHCP default route와 DNS를 복구한다. 이후 `tailscaled`를 재시작하고 Tailscale IP를 확인한다.

**재발 방지:**

Tailscale 검증 실패 시 Tailscale 자체보다 먼저 `wlan0`, default route, DNS, `controlplane.tailscale.com` 접근성을 확인한다.

## 🐛 트러블슈팅 리포트 - worker1 `eth0` IPv4 미할당과 NetworkManager connection profile 삭제 후 단절

### 📌 현상 요약

worker1 `eth0` 장치는 UP 상태였지만 IPv4가 없었고, NetworkManager profile 삭제 후 `nmcli connection up eth0`도 실패했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Raspberry Pi 5, NetworkManager, eth0 static IP
- 발생 시각: 2026-05-08

### 🔁 재현 순서

1. worker1에서 `ip addr` 또는 `ifconfig`로 `eth0` 상태를 확인한다.
2. `nmcli con show`에서 Ethernet profile을 확인한다.
3. 자동 생성된 `Wired connection 1`을 삭제한다.
4. `nmcli connection up eth0`을 실행한다.

### ✅ 기대 동작

`eth0`에 static IP `10.10.10.11/24`가 할당되고 profile 이름과 device 이름이 일치해야 한다.

### ❌ 실제 동작

```text
eth0 장치는 UP/RUNNING이나 IPv4 없음
nmcli connection up eth0
Error: unknown connection 'eth0'
```

### 🔍 시도한 것들

- [x] device와 connection profile 차이 정리
- [x] `nmcli con show`로 profile/device 매핑 확인
- [x] `eth0` 이름의 Ethernet profile 생성
- [x] static IP, `never-default yes`, autoconnect 설정
- [x] master에서 ping과 `kubectl get nodes -o wide` 확인

### 🚨 심각도

상

### 🗂️ 영역

Network, OS / Raspberry Pi

### 💡 해결 방법

**근본 원인:**

`eth0`는 물리 장치 이름이고 `nmcli connection up <name>`의 `<name>`은 NetworkManager connection profile 이름이다. profile이 없으면 `eth0` 장치가 있어도 connection up이 실패한다.

**해결 방법:**

`eth0`라는 이름의 Ethernet profile을 새로 만들고 `10.10.10.11/24`, `ipv4.never-default yes`, `connection.autoconnect yes`를 설정한다.

**재발 방지:**

새 노드 추가 시 device name과 profile name을 `eth0`로 통일한다. profile 삭제 전에는 반드시 `nmcli con show`로 매핑을 확인한다.

## 🐛 트러블슈팅 리포트 - factory-a `eth0`/`wlan0` 역할 고정과 `/24` 정상화 접근 경로 변경

### 📌 현상 요약

factory-a dual NIC 역할을 정리하면서 `eth0`를 `/8`에서 `/24`로 정상화하자 기존에 가능하던 `10.10.10.x` 직접 접근 경로가 달라졌다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: NetworkManager, eth0, wlan0, Tailscale, K3s flannel
- 발생 시각: 2026-05-08

### 🔁 재현 순서

1. master `eth0`가 `10.10.10.10/8`처럼 넓은 prefix로 잡힌 상태를 확인한다.
2. `eth0`를 `10.10.10.10/24`로 정상화한다.
3. `eth0`에는 default gateway를 두지 않고 `wlan0`에 default route를 둔다.
4. 로컬 작업 머신에서 `10.10.10.10/11/12` 직접 SSH/ping을 시도한다.
5. master Tailscale IP 또는 각 node `wlan0` IP로 운영 접근을 시도한다.

### ✅ 기대 동작

`eth0`는 K3s 내부망 `10.10.10.0/24` 전용으로 동작하고, `wlan0`만 인터넷 default route와 DNS를 담당해야 한다.

### ❌ 실제 동작

`/24` 정상화 후 로컬 작업 머신이 `10.10.10.0/24`에 직접 붙어 있지 않으면 `10.10.10.x` 직접 접근이 더 이상 되지 않을 수 있다. 이는 장애가 아니라 과거의 잘못 넓은 `/8` route에 기대던 접근 방식이 사라진 것이다.

### 🔍 시도한 것들

- [x] 세 노드 최종 IP 역할 정리
- [x] `eth0` profile을 static `/24`, `never-default yes`, DNS 무시로 설정
- [x] `wlan0` profile을 DHCP default route와 DNS 담당으로 설정
- [x] route metric 기준 정리
- [x] master Tailscale IP와 worker `wlan0` IP 기반 운영 접근 경로 정리
- [x] `kubectl get nodes -o wide`에서 INTERNAL-IP가 `10.10.10.x`인지 확인

### 🚨 심각도

상

### 🗂️ 영역

Network, Architecture, K3s / Kubernetes, Operations / DR

### 💡 해결 방법

**근본 원인:**

과거 master `eth0`가 `10.10.10.10/8`로 잡혀 `10.0.0.0/8` 전체를 eth0로 보내는 위험한 route를 만들었다. `/24`로 정상화하면 내부망은 올바르게 좁아지지만, 로컬 작업 머신이 해당 대역에 직접 연결되어 있지 않을 경우 기존 직접 접근이 끊긴다.

**해결 방법:**

factory-a 네트워크 역할을 아래처럼 고정한다.

```text
eth0:
  K3s 내부망 전용
  10.10.10.0/24
  default gateway 없음
  DNS 없음
  never-default yes
  route metric 500

wlan0:
  외부 인터넷
  DNS
  Tailscale control plane
  package/image pull
  default route 있음
  route metric 100
```

운영 접근은 master Tailscale IP 또는 각 노드 `wlan0` IP를 사용한다. 내부 클러스터 통신은 `10.10.10.0/24` eth0로 유지한다.

**재발 방지:**

OS baseline에서 NetworkManager profile을 표준화한다. `eth0`에 default route/DNS를 두지 않고, `wlan0`가 인터넷 경로를 담당한다는 원칙을 아키텍처 문서와 운영 Runbook에 명시한다.

