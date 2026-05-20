# Factory B Mac UTM K3s Runbook

상태: source of truth
기준일: 2026-05-20

## 목적

Mac mini에서 UTM 기반 Linux VM 2대를 만들고 `factory-b` 테스트베드형 Spoke K3s를 master + worker 구조로 구성한다.

이 문서는 `docs/issues/M5_vm-spoke-expansion.md`의 Issue 1 실행 기준이다. 2026-05-20 기준 `factory-b`는 Hub/ArgoCD 등록, worker1 hostPath outbox, local dummy generator, common `edge-iot-publisher`, S3 raw 적재까지 검증됐다.

## 범위

포함:

- UTM VM 생성 기준
- Ubuntu Server 또는 Debian 계열 guest OS 설치 기준
- K3s master + worker 2-node 설치
- `factory-b` hostname, label, 환경 기준 적용
- kubeconfig 확인
- VM 재부팅 후 K3s 자동 복구 확인
- Tailscale Hub 연결과 ArgoCD cluster 등록 상태 기록
- worker1 local dummy generator와 S3 raw 적재 검증 결과 연결

제외:

- Longhorn
- NFS 또는 cold storage
- 실센서, 카메라, 마이크 의존 구성
- 운영형 failover/failback 구성

## 권장 VM 기준

| 항목 | 값 |
| --- | --- |
| VM 이름 | `factory-b-master`, `factory-b-worker1` |
| Host | Mac mini |
| VM tool | UTM |
| Guest OS | Ubuntu Server LTS 또는 Debian stable |
| CPU | 2 vCPU |
| Memory | 4GiB |
| Disk | 40GiB |
| Network | UTM Shared Network 또는 Bridged |
| Kubernetes | K3s master + worker |

`factory-b-worker1`은 `aegis.workload-node=true` label을 유지하고, local dummy generator가 `/var/lib/aegis/outbox`에 canonical JSON을 쓴다. Hub ArgoCD가 배포한 `edge-iot-publisher`는 같은 hostPath를 읽어 IoT Core로 송신한다.

초기 로컬 검증은 UTM Shared Network로 충분하다. Hub EKS, ArgoCD, Tailscale 연결 단계에서는 Tailscale IP를 K3s API endpoint 기준으로 사용한다.

## UTM VM 생성

1. UTM에서 새 Virtual Machine을 만든다.
2. Virtualize를 선택한다.
3. Linux를 선택한다.
4. Ubuntu Server LTS 또는 Debian ISO를 지정한다.
5. CPU 2개, memory 4096MiB, disk 40GiB로 만든다.
6. Network는 우선 Shared Network로 둔다.
7. VM 이름은 master는 `factory-b-master`, worker는 `factory-b-worker1`로 둔다.

Guest OS 설치 중 사용자는 아래 기준을 적용한다.

```text
hostname: factory-b-master / factory-b-worker1
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
sudo hostnamectl set-hostname factory-b
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

## Factory B 기준 적용

노드 이름을 확인한다.

```bash
kubectl get nodes
```

노드가 `factory-b`로 보이면 아래 label을 적용한다.

```bash
kubectl label node factory-b aegis.factory-id=factory-b --overwrite
kubectl label node factory-b aegis.environment-type=vm-mac --overwrite
kubectl label node factory-b aegis.input-module-type=dummy --overwrite
kubectl label node factory-b aegis.spoke-type=testbed --overwrite
```

label을 확인한다.

```bash
kubectl get node factory-b --show-labels
```

`factory-b`의 환경 기준은 아래 값으로 고정한다.

```text
factory_id: factory-b
environment_type: vm-mac
input_module_type: dummy
spoke_type: testbed
```

## Kubeconfig 보관 기준

Hub 연결 전에는 VM 내부 kubeconfig만 확인한다.

후속 Tailscale 연결 후 외부에서 사용할 kubeconfig는 별도 파일로 만든다.

```text
factory-b.kubeconfig
server: https://<factory-b-tailscale-ip>:6443
```

`factory-b.kubeconfig`에는 인증 정보가 포함될 수 있으므로 repository에 커밋하지 않는다.

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
kubectl get node factory-b --show-labels
```

정상 기준:

```text
k3s: active
factory-b node: Ready
aegis.factory-id=factory-b
aegis.environment-type=vm-mac
aegis.input-module-type=dummy
aegis.spoke-type=testbed
```

## 완료 상태

- Tailscale 설치 및 `factory-b` auth key로 tailnet 참여 완료
- Tailscale IP 기준 kubeconfig 생성 완료
- EKS Hub와 운영자 로컬에서 `factory-b` K3s API 접근 확인
- ArgoCD에 `factory-b` cluster 등록 완료
- `envs/factory-b/values.yaml` 작성 및 hostPath outbox 적용 완료
- local dummy generator와 common `edge-iot-publisher` 기반 S3 raw 적재 검증 완료

## 완료 체크리스트

- [x] UTM VM `factory-b-master`, `factory-b-worker1` 생성
- [x] Guest OS 설치 및 SSH 활성화
- [x] K3s master + worker 설치
- [x] `kubectl get nodes`에서 master/worker Ready 확인
- [x] K3s version 기록
- [x] `factory-b` label 적용
- [x] VM 재부팅 후 K3s 자동 복구 확인
- [x] 민감 정보가 문서와 repository에 남지 않았는지 확인
