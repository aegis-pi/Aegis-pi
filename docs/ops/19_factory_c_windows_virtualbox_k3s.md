# Factory C Windows VirtualBox K3s Runbook

상태: draft
기준일: 2026-05-06

## 목적

Windows 호스트에서 VirtualBox 기반 Linux VM을 만들고 `factory-c` 테스트베드형 Spoke K3s를 구성한다.

이 문서는 `docs/issues/M5_vm-spoke-expansion.md`의 Issue 2 실행 사전이다. 목표는 Hub/ArgoCD 연결 전, 독립 VM 안에서 `factory-c` 단일 노드 K3s가 재부팅 후에도 `Ready` 상태로 복구되는 기준선을 만드는 것이다.

## 범위

포함:

- VirtualBox VM 생성 기준
- Ubuntu Server 또는 Debian 계열 guest OS 설치 기준
- K3s 단일 노드 설치
- `factory-c` hostname, label, 환경 기준 적용
- kubeconfig 확인
- Windows host 재부팅 후 VM/K3s 복구 기준 확인

제외:

- Longhorn
- NFS 또는 cold storage
- 실센서, 카메라, 마이크 의존 구성
- 운영형 failover/failback 구성
- Tailscale 연결
- ArgoCD cluster 등록
- Dummy mode `edge-agent` 또는 Dummy Sensor 배포

## 권장 VM 기준

| 항목 | 값 |
| --- | --- |
| VM 이름 | `factory-c` |
| Host | Windows |
| VM tool | VirtualBox |
| Guest OS | Ubuntu Server LTS 또는 Debian stable |
| CPU | 2 vCPU |
| Memory | 4GiB |
| Disk | 40GiB |
| Network | NAT 또는 Bridged Adapter |
| Kubernetes | K3s single-node |

초기 로컬 검증은 NAT로 충분하다. Host 또는 같은 LAN에서 직접 SSH 접근이 필요하면 Bridged Adapter를 사용한다. Hub EKS, ArgoCD, Tailscale 연결 단계에서는 Tailscale IP를 K3s API endpoint 기준으로 사용한다.

## VirtualBox VM 생성

1. VirtualBox에서 새 VM을 만든다.
2. 이름은 `factory-c`로 둔다.
3. Type은 Linux, Version은 Ubuntu 64-bit 또는 Debian 64-bit로 둔다.
4. CPU 2개, memory 4096MiB, disk 40GiB로 만든다.
5. Ubuntu Server LTS 또는 Debian ISO를 optical drive에 연결한다.
6. Network는 우선 NAT로 둔다.
7. VM을 시작하고 guest OS를 설치한다.

Guest OS 설치 중 사용자는 아래 기준을 적용한다.

```text
hostname: factory-c
user: 운영자가 정한 일반 사용자
ssh: enabled
```

비밀번호, SSH private key, token은 문서에 기록하지 않는다.

## Guest OS 기본 확인

VM 내부에서 실행한다.

```bash
hostnamectl
ip addr
systemctl status ssh
```

필요하면 hostname을 고정한다.

```bash
sudo hostnamectl set-hostname factory-c
```

기본 패키지를 갱신한다.

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y curl ca-certificates
```

## K3s 설치

단일 노드 K3s로 설치한다.

```bash
curl -sfL https://get.k3s.io | sh -
```

설치 후 상태를 확인한다.

```bash
sudo systemctl status k3s
sudo kubectl get nodes -o wide
sudo kubectl get pods -A
```

일반 사용자로 `kubectl`을 실행하려면 kubeconfig를 복사한다.

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown "$USER:$USER" ~/.kube/config
chmod 600 ~/.kube/config
kubectl get nodes -o wide
```

## Factory C 기준 적용

노드 이름을 확인한다.

```bash
kubectl get nodes
```

노드가 `factory-c`로 보이면 아래 label을 적용한다.

```bash
kubectl label node factory-c aegis.factory-id=factory-c --overwrite
kubectl label node factory-c aegis.environment-type=vm-windows --overwrite
kubectl label node factory-c aegis.input-module-type=dummy --overwrite
kubectl label node factory-c aegis.spoke-type=testbed --overwrite
```

label을 확인한다.

```bash
kubectl get node factory-c --show-labels
```

`factory-c`의 환경 기준은 아래 값으로 고정한다.

```text
factory_id: factory-c
environment_type: vm-windows
input_module_type: dummy
spoke_type: testbed
```

## Kubeconfig 보관 기준

Hub 연결 전에는 VM 내부 kubeconfig만 확인한다.

후속 Tailscale 연결 후 외부에서 사용할 kubeconfig는 별도 파일로 만든다.

```text
factory-c.kubeconfig
server: https://<factory-c-tailscale-ip>:6443
```

`factory-c.kubeconfig`에는 인증 정보가 포함될 수 있으므로 repository에 커밋하지 않는다.

## 재부팅 검증

VM을 재부팅한다.

```bash
sudo reboot
```

재접속 후 확인한다.

```bash
systemctl is-active k3s
kubectl get nodes -o wide
kubectl get pods -A
kubectl get node factory-c --show-labels
```

Windows host 재부팅 후에는 아래 순서로 확인한다.

1. Windows 부팅 후 VirtualBox에서 `factory-c` VM 시작
2. VM guest OS 부팅 완료 확인
3. SSH 또는 VM console로 접속
4. K3s 상태 확인

정상 기준:

```text
k3s: active
factory-c node: Ready
aegis.factory-id=factory-c
aegis.environment-type=vm-windows
aegis.input-module-type=dummy
aegis.spoke-type=testbed
```

## 후속 TODO

- Tailscale 설치 및 `factory-c` auth key로 tailnet 참여
- Tailscale IP 기준 kubeconfig 생성
- EKS Hub 또는 운영자 로컬에서 `factory-c.kubeconfig`로 `kubectl get nodes` 확인
- ArgoCD에 `factory-c` cluster 등록
- `envs/factory-c/values.yaml` 작성
- Dummy mode `edge-agent` 또는 Dummy Sensor 배포

## 완료 체크리스트

- [ ] VirtualBox VM `factory-c` 생성
- [ ] Guest OS 설치 및 SSH 활성화
- [ ] K3s single-node 설치
- [ ] `kubectl get nodes`에서 `factory-c` Ready 확인
- [ ] K3s version 기록
- [ ] `factory-c` label 적용
- [ ] VM 재부팅 후 K3s 자동 복구 확인
- [ ] Windows host 재부팅 후 VM/K3s 복구 방식 확인
- [ ] 민감 정보가 문서와 repository에 남지 않았는지 확인
