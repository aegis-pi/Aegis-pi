# LoadBalancer / MetalLB Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - K3s ServiceLB와 MetalLB 역할 충돌

### 📌 현상 요약

K3s 기본 ServiceLB가 이미 LoadBalancer를 처리하고 있어 MetalLB 설치를 보류했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: kube-system
- 관련 컴포넌트/버전: K3s ServiceLB, Traefik, MetalLB
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. K3s 기본 설치 상태에서 Service 목록을 확인한다.
2. Traefik Service의 `EXTERNAL-IP`를 확인한다.
3. MetalLB 설치 여부를 검토한다.

### ✅ 기대 동작

LoadBalancer controller는 하나의 기준으로 운영되어야 한다.

### ❌ 실제 동작

```text
traefik LoadBalancer external IP:
10.10.10.10, 10.10.10.11, 10.10.10.12
```

K3s ServiceLB가 이미 LoadBalancer 역할을 수행하고 있었다.

### 🔍 시도한 것들

- [x] K3s ServiceLB 동작 확인
- [x] MetalLB 후보 IP 대역 ping 확인
- [x] 초기 단계에서는 MetalLB 설치 보류

### 🚨 심각도

중

### 🗂️ 영역

LoadBalancer / MetalLB, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

K3s ServiceLB와 MetalLB는 모두 LoadBalancer Service의 외부 노출을 담당할 수 있어 역할이 겹친다.

**해결 방법:**

초기에는 K3s ServiceLB를 유지하고, MetalLB 전환 시점에 ServiceLB 비활성화 계획을 먼저 수립한다.

**재발 방지:**

LoadBalancer controller 선택은 설계 결정으로 문서화한다. 동시에 두 controller를 운영하지 않는다.

## 🐛 트러블슈팅 리포트 - Longhorn UI LoadBalancer 노출 필요

### 📌 현상 요약

Longhorn UI가 ClusterIP로만 존재해 내부망에서 직접 접근할 수 없었다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: longhorn-system
- 관련 컴포넌트/버전: Longhorn UI, K3s ServiceLB
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. Longhorn 설치 후 `longhorn-frontend` Service를 확인한다.
2. Host PC에서 Longhorn UI에 접근한다.
3. 별도 LoadBalancer Service를 생성한다.

### ✅ 기대 동작

내부 독립망에서 Longhorn UI에 접근할 수 있어야 한다.

### ❌ 실제 동작

```text
longhorn-frontend ClusterIP 80/TCP
```

기본 Service는 ClusterIP라 외부 접근 경로가 없었다.

### 🔍 시도한 것들

- [x] `longhorn-frontend`를 LoadBalancer Service로 expose
- [x] `10.10.10.11:8080`, `10.10.10.12:8080` HTTP 200 확인
- [x] master IP 접근 실패 원인 확인

### 🚨 심각도

중

### 🗂️ 영역

LoadBalancer / MetalLB, Storage / Longhorn

### 💡 해결 방법

**근본 원인:**

Longhorn UI는 기본적으로 ClusterIP로만 노출된다.

**해결 방법:**

내부망 접근용 LoadBalancer Service를 별도로 생성한다. 단, 인증 없이 UI가 노출될 수 있으므로 인터넷 공개 경로로 사용하지 않는다.

**재발 방지:**

대시보드 노출 기준에 내부망 전용 IP/포트와 보안 주의사항을 함께 기록한다.

## 🐛 트러블슈팅 리포트 - K3s ServiceLB에서 MetalLB 전환 이슈

### 📌 현상 요약

서비스별 고정 IP 운영을 위해 K3s ServiceLB에서 MetalLB로 전환했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: kube-system, metallb-system
- 관련 컴포넌트/버전: K3s ServiceLB, MetalLB v0.15.3
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. K3s ServiceLB로 LoadBalancer Service를 운영한다.
2. 서비스별 고정 IP 요구사항을 정한다.
3. K3s server 실행 인자에 `--disable servicelb`를 추가한다.
4. MetalLB manifest와 IP pool을 적용한다.

### ✅ 기대 동작

LoadBalancer Service가 MetalLB IP pool에서 고정 IP를 할당받아야 한다.

### ❌ 실제 동작

전환 전에는 K3s ServiceLB가 노드 IP 기반으로 Service를 노출했고, 서비스별 고정 IP 관리가 어려웠다.

### 🔍 시도한 것들

- [x] K3s ServiceLB 비활성화
- [x] MetalLB v0.15.3 설치
- [x] `IPAddressPool`, `L2Advertisement` 생성
- [x] `.200` Argo CD 예약, `.201-.250` pool 구성

### 🚨 심각도

상

### 🗂️ 영역

LoadBalancer / MetalLB, K3s / Kubernetes, Network

### 💡 해결 방법

**근본 원인:**

K3s ServiceLB는 간단한 노출에는 충분하지만 서비스별 고정 IP 운영에는 MetalLB가 더 적합했다.

**해결 방법:**

K3s server에 `--disable servicelb`를 추가하고 MetalLB를 단일 LoadBalancer controller로 구성한다.

**재발 방지:**

IP pool, 예약 IP, 서비스별 고정 IP 할당 대장을 운영한다.

## 🐛 트러블슈팅 리포트 - MetalLB IP 충돌과 어노테이션 충돌

### 📌 현상 요약

Longhorn UI에 고정 IP를 할당하려 했지만 Traefik IP 점유와 MetalLB 어노테이션 충돌로 실패했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: kube-system, longhorn-system
- 관련 컴포넌트/버전: MetalLB, Traefik, Longhorn UI
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. MetalLB 설치 후 Traefik과 Longhorn LoadBalancer Service를 확인한다.
2. Longhorn UI에 `10.10.10.201` 고정 IP를 할당한다.
3. Service event와 annotation을 확인한다.

### ✅ 기대 동작

Longhorn UI는 `10.10.10.201`, Traefik은 별도 IP를 사용해야 한다.

### ❌ 실제 동작

```text
address also in use by kube-system/traefik
service can not have both metallb.io/loadBalancerIPs and svc.Spec.LoadBalancerIP
```

### 🔍 시도한 것들

- [x] Traefik을 `10.10.10.202`로 이동
- [x] Longhorn Service의 deprecated annotation 제거
- [x] `spec.loadBalancerIP` 제거
- [x] 현재 MetalLB annotation만 남김
- [x] HTTP 응답 확인

### 🚨 심각도

상

### 🗂️ 영역

LoadBalancer / MetalLB, Network, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

MetalLB pool 첫 IP를 Traefik이 자동으로 점유했고, Longhorn Service에는 새/구 annotation과 `spec.loadBalancerIP`가 함께 설정되어 있었다.

**해결 방법:**

서비스별 고정 IP를 명확히 재할당하고, MetalLB annotation은 `metallb.io/loadBalancerIPs` 하나만 사용한다.

**재발 방지:**

IPAM 대장과 Kubernetes Service annotation 표준을 유지한다. deprecated annotation과 `spec.loadBalancerIP` 혼용을 금지한다.

## 🐛 트러블슈팅 리포트 - Grafana IP와 Traefik IP 충돌 위험

### 📌 현상 요약

Grafana 예정 IP와 Traefik LoadBalancer IP가 겹칠 가능성이 있어 사전에 Traefik IP를 변경했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: kube-system, monitoring
- 관련 컴포넌트/버전: MetalLB, Traefik, Grafana
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. Grafana 접속 IP를 `10.10.10.202`로 계획한다.
2. Traefik Service의 LoadBalancer IP를 확인한다.
3. IP 충돌 가능성을 확인한다.

### ✅ 기대 동작

Grafana와 Traefik은 서로 다른 고정 IP를 사용해야 한다.

### ❌ 실제 동작

Traefik이 Grafana 예정 IP와 같은 `10.10.10.202`를 사용할 수 있는 상태였다.

### 🔍 시도한 것들

- [x] Traefik annotation을 `10.10.10.203`으로 변경
- [x] Grafana 예정 IP `10.10.10.202` 확보
- [x] Service IP 재확인

### 🚨 심각도

중

### 🗂️ 영역

LoadBalancer / MetalLB, Monitoring / Grafana / InfluxDB, Network

### 💡 해결 방법

**근본 원인:**

MetalLB 고정 IP를 서비스별로 관리하지 않으면 대시보드와 ingress controller 간 IP 충돌이 발생할 수 있다.

**해결 방법:**

Traefik을 `10.10.10.203`, Grafana를 `10.10.10.202`로 분리한다.

**재발 방지:**

클러스터 서비스 IP registry를 문서화하고 새 LoadBalancer Service 생성 전 예약 여부를 확인한다.

