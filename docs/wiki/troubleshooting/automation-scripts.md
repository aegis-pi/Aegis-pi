# Automation / Script Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - K3s 설치 중 `curl | sudo -S` 비밀번호 입력 실패

### 📌 현상 요약

K3s 설치 스크립트를 `curl | sudo -S ... sh -` 형태로 실행하자 sudo 비밀번호 입력이 실패했다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: K3s install script, sudo, SSH shell
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. 원격 SSH 세션에서 K3s 설치 명령을 파이프라인으로 실행한다.
2. `curl -sfL https://get.k3s.io | sudo -S ... sh -` 형태로 sudo 비밀번호를 입력하려 한다.
3. 설치 로그를 확인한다.

### ✅ 기대 동작

sudo 인증 후 K3s install script가 정상 실행되어야 한다.

### ❌ 실제 동작

```text
sudo: 3 incorrect password attempts
```

### 🔍 시도한 것들

- [x] 같은 SSH 세션에서 먼저 `sudo -v` 실행
- [x] sudo credential cache 갱신 후 설치 명령 재실행
- [x] `sudo env ... sh -` 형태로 실행

### 🚨 심각도

중

### 🗂️ 영역

Automation / Script, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

파이프라인에서 `sudo`의 표준입력이 설치 스크립트 스트림과 연결되어 비밀번호 입력을 정상적으로 받지 못했다.

**해결 방법:**

원격 SSH 세션에서 먼저 `sudo -v`로 sudo 인증을 갱신한 뒤 같은 세션에서 K3s 설치 명령을 실행한다.

**재발 방지:**

자동화 스크립트에서 `curl | sudo -S` 패턴을 피하고, sudo 인증 갱신 단계와 설치 실행 단계를 분리한다.

## 🐛 트러블슈팅 리포트 - ai-apps 배포 중 대용량 이미지 pull 지연

### 📌 현상 요약

AI/Audio 이미지가 커서 장애 복구 또는 최초 배포 시 image pull 시간이 RTO에 큰 영향을 줬다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1, worker2
- 네임스페이스: ai-apps
- 관련 컴포넌트/버전: safe-edge-ai, safe-edge-audio, containerd, Argo CD
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. `safe-edge-ai`와 `safe-edge-audio`를 새 노드에 배포한다.
2. Pod event에서 image pull 시간을 확인한다.
3. 장애 테스트 중 failover 대상 노드에 이미지가 없는 상태를 만든다.

### ✅ 기대 동작

failover 대상 노드에서 Pod가 빠르게 시작되어야 한다.

### ❌ 실제 동작

```text
safe-edge-ai:v6: 약 3분 22초
safe-edge-audio:v2: 약 5분 34초
```

### 🔍 시도한 것들

- [x] 이미지 크기와 pull 시간 기록
- [x] failover 테스트에서 pull 지연 영향 확인
- [x] worker1/worker2 대상 image pre-pull DaemonSet 추가
- [x] AI/Audio 앱에 `imagePullPolicy: IfNotPresent` 적용

### 🚨 심각도

중

### 🗂️ 영역

Automation / Script, AI / Hardware, Operations / DR

### 💡 해결 방법

**근본 원인:**

Edge 환경의 네트워크와 이미지 크기 때문에 최초 pull 시간이 길어지고 장애 복구 시간이 늘어났다.

**해결 방법:**

worker1/worker2에서 image pre-pull DaemonSet을 실행하고, 운영 Pod는 `IfNotPresent`를 사용해 로컬 캐시를 우선한다.

**재발 방지:**

같은 태그를 덮어쓰지 말고 새 이미지 태그로 배포한다. 복구 대상 노드에는 운영 이미지를 사전에 준비한다.

## 🐛 트러블슈팅 리포트 - `argocd --core` argocd-cm ConfigMap 조회 실패

### 📌 현상 요약

`argocd --core` 실행 시 실제 ConfigMap이 있는데도 `argocd-cm`을 찾지 못했다.

### 🖥️ 환경 정보

- 클러스터: Hub EKS 또는 K3s 관리 클러스터
- 노드: 해당 없음
- 네임스페이스: argocd
- 관련 컴포넌트/버전: Argo CD CLI, kubeconfig
- 발생 시각: 2026-05-21

### 🔁 재현 순서

1. kubeconfig current namespace가 `default`인 상태로 둔다.
2. `argocd --core app get ...`를 실행한다.
3. 오류 메시지를 확인한다.

### ✅ 기대 동작

Argo CD CLI가 `argocd/argocd-cm`을 찾아 Application을 조회해야 한다.

### ❌ 실제 동작

```text
{"level":"fatal","msg":"configmap \"argocd-cm\" not found"}
```

### 🔍 시도한 것들

- [x] current context namespace 확인
- [x] 임시 kubeconfig 생성
- [x] 임시 kubeconfig의 current namespace를 `argocd`로 설정
- [x] 원본 kubeconfig 수정 없이 `argocd --core` 실행

### 🚨 심각도

중

### 🗂️ 영역

Automation / Script, GitOps / Argo CD

### 💡 해결 방법

**근본 원인:**

`argocd --core`는 kubeconfig current context의 namespace에서 `argocd-cm`을 찾는다.

**해결 방법:**

스크립트에서 임시 kubeconfig를 만들고 current namespace를 `argocd`로 설정한 뒤 `argocd --core`를 실행한다.

**재발 방지:**

Argo CD CLI 자동화에서는 원본 kubeconfig에 의존하지 말고 namespace가 설정된 임시 kubeconfig를 사용한다.

## 🐛 트러블슈팅 리포트 - Hub 재생성 후 build/register 스크립트 선택 혼동

### 📌 현상 요약

Hub만 삭제/재생성한 뒤 IoT build와 Spoke register 중 어떤 스크립트를 다시 실행해야 하는지 혼동이 있었다.

### 🖥️ 환경 정보

- 클러스터: Hub EKS, factory-a/b/c Spoke
- 노드: 해당 없음
- 네임스페이스: argocd, observability 등
- 관련 컴포넌트/버전: build scripts, Argo CD, IoT Thing/Certificate
- 발생 시각: 2026-05-21

### 🔁 재현 순서

1. Hub를 삭제 후 재생성한다.
2. IoT Thing/certificate와 Spoke K3s Secret은 남아 있다.
3. `build-iot-*`, `register-spoke-*`, dummy generator 스크립트 중 재실행 대상을 판단한다.

### ✅ 기대 동작

Hub-only rebuild 후 필요한 최소 절차만 실행되어야 한다.

### ❌ 실제 동작

IoT 자산이 남아 있는데도 `build-iot-factory-a.sh`를 다시 실행해야 하는지 혼동될 수 있다.

### 🔍 시도한 것들

- [x] Hub-only rebuild 표준 순서 정리
- [x] Spoke register 스크립트 분리
- [x] dummy generator 재시작 절차 정리
- [x] Tailnet UI 연결 스크립트는 필요 시에만 실행하도록 분리

### 🚨 심각도

중

### 🗂️ 영역

Automation / Script, GitOps / Argo CD, Operations / DR

### 💡 해결 방법

**근본 원인:**

Hub 재생성 범위와 foundation/IoT/Spoke 영구 자산의 수명주기가 다르다.

**해결 방법:**

Hub-only 데이터 수집 유지 rebuild 표준 순서는 `build-hub.sh`, `build-admin-ui-after-ns.sh`, `HUB_ONLY_RECONNECT=true register-spoke-factory-a/b/c.sh`로 둔다. 이 흐름에서는 dummy generator와 data-pipeline을 유지하며, `build-hub.sh`가 SlowCollector EKS access binding을 자동 복구한다.

**재발 방지:**

시스템 재구축 SOP에 Hub, IoT, Spoke, dummy generator의 책임 경계를 명시한다.

## 🐛 트러블슈팅 리포트 - `manage-dummy-generators.sh` 권한, 원격 shell, 서비스 상태 혼동

### 📌 현상 요약

factory-b/c dummy generator 관리 스크립트 실행 중 SSH password prompt, Permission denied, 원격 shell quote 오류, legacy publisher service 상태 혼동이 발생했다.

### 🖥️ 환경 정보

- 클러스터: factory-b/c VM K3s
- 노드: factory master, worker VM
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: SSH ProxyJump, systemd, dummy generator
- 발생 시각: 2026-05-21

### 🔁 재현 순서

1. 운영 PC에서 `manage-dummy-generators.sh`를 실행한다.
2. 스크립트가 master를 ProxyJump로 거쳐 worker에 접속한다.
3. worker에서 `sudo systemctl ...`을 실행한다.

### ✅ 기대 동작

ProxyJump 경로로 worker에 접속하고 generator systemd unit 상태를 제어해야 한다.

### ❌ 실제 동작

```text
Permission denied, please try again.
oosnim@192.168.128.11: Permission denied (publickey,password).
```

### 🔍 시도한 것들

- [x] 접속 경로를 `local PC -> factory master -> factory worker -> sudo systemctl`로 정리
- [x] master와 worker 각각의 SSH 인증 필요성 확인
- [x] ProxyJump 기반 `ssh-copy-id` 절차 정리
- [x] nested SSH/here-doc quote 오류는 ProxyJump 단일 원격 명령 방식으로 정리
- [x] legacy local publisher service 미존재가 정상임을 정리

### 🚨 심각도

중

### 🗂️ 영역

Automation / Script, Network, Operations / DR

### 💡 해결 방법

**근본 원인:**

운영 PC에서 worker VM으로 직접 닿지 않아 master를 ProxyJump로 거치며, master/worker SSH 인증과 worker sudo 인증이 각각 필요했다.

**해결 방법:**

운영 PC에서 master와 worker에 SSH key 인증을 구성한다. worker key 등록은 ProxyJump를 통해 수행한다.

**재발 방지:**

dummy generator 운영 문서에 ProxyJump 경로, SSH key 등록, systemd generator 구조를 함께 기록한다.
