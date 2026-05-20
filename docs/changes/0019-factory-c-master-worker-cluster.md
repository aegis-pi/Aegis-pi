# 0019. factory-c Windows VirtualBox master/worker cluster

상태: accepted
결정일: 2026-05-20

## 기존 계획

초기 `factory-c` 초안은 단일 VM 또는 단일 노드 K3s 테스트베드를 가정했다.

## 변경된 실제 기준

`factory-c`는 Windows VirtualBox 위의 2-node K3s 클러스터로 구성한다.

```text
factory-c-master: control-plane
factory-c-worker: worker, dummy generator/publisher 대상 노드
```

VirtualBox NAT 어댑터만 사용하면 master/worker가 같은 `10.0.2.15`로 등록되는 문제가 있으므로, host-only `enp0s8` 대역을 K3s node-ip와 flannel 인터페이스로 고정한다.

```text
factory-c-master: 192.168.56.10
factory-c-worker: 192.168.56.20
flannel-iface: enp0s8
```

## 변경 이유

M5 테스트베드는 멀티 factory 흐름뿐 아니라 최소한의 master/worker 배치, worker hostPath outbox, Hub ArgoCD 배포 대상 분리를 검증해야 한다. 단일 노드보다 2-node 구성이 실제 운영형 Spoke와의 차이를 설명하기 쉽다.

## 영향

- `configs/runtime/runtime-config.yaml`의 `factory-c` topology는 `two-node`다.
- `factory-c-worker`에 `aegis.workload-node=true`와 dummy 입력 label을 유지한다.
- `edge-iot-publisher`는 worker hostPath `/var/lib/aegis/outbox`를 mount한다.
- VirtualBox 네트워크 문제 진단 시 NAT IP가 아니라 host-only IP와 flannel 설정을 우선 확인한다.

## 검증

2026-05-20 기준 중복 `10.0.2.15` 등록으로 인한 Flannel/CoreDNS 장애를 `enp0s8` 고정 IP와 `flannel-iface` 지정으로 해결했다. 이후 `edge-iot-publisher` DNS resolution과 AWS IoT Core publish가 정상화됐다.
