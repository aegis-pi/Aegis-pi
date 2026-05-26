# Operations / DR Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - Kubernetes CronJob 기반 Failback 재생성 루프 위험

### 📌 현상 요약

worker2 복구 후 Kubernetes CronJob으로 하드웨어 의존 Pod를 자동 failback하면 재생성 루프가 발생할 수 있다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1, worker2
- 네임스페이스: monitoring, ai-apps
- 관련 컴포넌트/버전: Kubernetes CronJob, failover/failback script, BME280, AI, Audio
- 발생 시각: 2026-04-28

### 🔁 재현 순서

1. worker2 장애로 하드웨어 의존 Pod가 worker1로 failover된다.
2. worker2가 Node Ready로 돌아온다.
3. CronJob이 worker1 Pod를 삭제해 worker2 failback을 유도한다.
4. worker2 하드웨어가 아직 안정적이지 않은 상태를 만든다.

### ✅ 기대 동작

worker2가 안정화된 뒤 대상 Pod만 안전하게 failback되어야 한다.

### ❌ 실제 동작

worker2가 Kubernetes Node 관점에서 Ready여도 하드웨어 장치가 안정적이지 않으면 BME280/Audio/AI Pod가 재생성 루프에 빠질 수 있다.

### 🔍 시도한 것들

- [x] Kubernetes CronJob 방식 위험성 정리
- [x] master OS cron 기반 Kubernetes-only 외부 스크립트로 전환
- [x] worker2에 이미 대상 Pod가 있으면 skip하도록 조건 추가
- [x] worker1에 남은 대상 Pod만 삭제 후보로 제한
- [x] cooldown과 대상/제외 workload 기준 정리

### 🚨 심각도

상

### 🗂️ 영역

Operations / DR, Automation / Script, AI / Hardware

### 💡 해결 방법

**근본 원인:**

Kubernetes Node Ready는 하드웨어 장치 준비 완료를 의미하지 않는다. 준비 상태 확인 없이 Pod를 삭제하면 정상 동작 중인 Pod까지 죽이고 재생성 루프를 만들 수 있다.

**해결 방법:**

Failback은 Kubernetes CronJob이 아니라 master OS cron 기반 외부 스크립트로 처리한다. 스크립트는 worker2에 대상 Pod가 이미 있으면 아무 작업도 하지 않고, worker1에 남은 대상 Pod만 삭제 후보로 본다.

**재발 방지:**

하드웨어 의존 workload의 failback은 idempotent, cooldown, 대상 제한, skip 조건을 필수로 둔다.

## 🐛 트러블슈팅 리포트 - latest 이미지 pull로 인한 Pod 복구 실패

### 📌 현상 요약

노드 재부팅 후 `latest` 이미지가 외부 registry pull을 시도하다 DNS/네트워크 문제로 Pod 복구가 지연됐다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker2
- 네임스페이스: monitoring
- 관련 컴포넌트/버전: Kubernetes imagePullPolicy, node-exporter, Docker Hub DNS
- 발생 시각: 2026-04-29

### 🔁 재현 순서

1. worker2를 재부팅한다.
2. `latest` 태그를 사용하는 Pod를 시작한다.
3. 외부 DNS/registry 경로가 불안정한 상태를 만든다.
4. Pod event를 확인한다.

### ✅ 기대 동작

노드에 이미지가 이미 있으면 로컬 캐시로 빠르게 복구되어야 한다.

### ❌ 실제 동작

```text
ErrImagePull
ImagePullBackOff
registry-1.docker.io DNS 조회 실패 또는 image pull 실패
```

### 🔍 시도한 것들

- [x] `latest` tag와 기본 imagePullPolicy 동작 확인
- [x] monitoring Pod에 `imagePullPolicy: IfNotPresent` 적용
- [x] pre-pull 전략과 명시 버전 태그 필요성 정리

### 🚨 심각도

상

### 🗂️ 영역

Operations / DR, Automation / Script, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

`latest` tag는 imagePullPolicy가 `Always`로 해석될 수 있어 노드에 이미지가 있어도 외부 registry 접근을 시도한다.

**해결 방법:**

운영 Pod에는 `imagePullPolicy: IfNotPresent`를 명시하고, 가능한 한 명시 버전 tag를 사용한다.

**재발 방지:**

Edge 클러스터에서는 복구 경로가 외부 DNS/registry 상태에 의존하지 않도록 이미지 캐시와 tag 정책을 운영한다.

## 🐛 트러블슈팅 리포트 - 랜선 제거 테스트 상태 판정 오류 위험

### 📌 현상 요약

랜선 제거 직후 Kubernetes API의 마지막 관측값 때문에 failover/failback 성공 여부를 잘못 판단할 수 있다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker2
- 네임스페이스: monitoring, ai-apps
- 관련 컴포넌트/버전: Kubernetes Node status, failover/failback test, InfluxDB
- 발생 시각: 2026-04-28

### 🔁 재현 순서

1. worker2 랜선을 제거한다.
2. 즉시 `kubectl get nodes`와 `kubectl get pods -o wide`를 확인한다.
3. worker2 랜선을 다시 연결한다.
4. Pod 이동 시각과 데이터 공백/중복을 측정한다.

### ✅ 기대 동작

worker2 NotReady 이후 대상 Pod가 worker1로 이동하고, 복구 후 worker2로 failback되어야 한다.

### ❌ 실제 동작

랜선 제거 직후에도 `kubectl` 출력은 잠시 worker2를 `Ready` 또는 기존 Pod `Running`으로 보여줄 수 있다. 이는 성공이 아니라 마지막 관측값일 수 있다.

### 🔍 시도한 것들

- [x] 랜선 제거 시각, NotReady 전환 시각, Pod Running 전환 시각을 분리 기록
- [x] 첫 5분 동안 마지막 관측값만으로 판단하지 않도록 기준 정리
- [x] 10초 bucket count로 데이터 공백 확인
- [x] 중복 write 가능성 해석 정리

### 🚨 심각도

상

### 🗂️ 영역

Operations / DR, K3s / Kubernetes, Monitoring / Grafana / InfluxDB

### 💡 해결 방법

**근본 원인:**

Kubernetes API는 장애 직후 마지막 상태를 잠시 유지할 수 있다. 실제 네트워크 단절과 API 상태 반영에는 지연이 있다.

**해결 방법:**

테스트 판정 기준을 시간축으로 분리한다. 랜선 제거, Node NotReady, 대상 Pod worker1 Running, 랜선 재연결, 대상 Pod worker2 Running 시각을 각각 기록한다.

**재발 방지:**

카오스 테스트 체크리스트에 상태 지연, 데이터 공백, 중복 write 측정 기준을 명시한다.

