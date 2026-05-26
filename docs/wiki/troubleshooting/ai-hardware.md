# AI / Hardware Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - 하드웨어 의존 Pod RollingUpdate 갱신 충돌

### 📌 현상 요약

카메라, 오디오, I2C 센서를 직접 잡는 Pod는 RollingUpdate 중 장치 점유 충돌이 발생할 수 있다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1, worker2
- 네임스페이스: ai-apps, monitoring
- 관련 컴포넌트/버전: safe-edge-integrated-ai, safe-edge-audio, bme280-sensor
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. 하드웨어 장치를 사용하는 Deployment를 기본 `RollingUpdate`로 둔다.
2. 새 버전을 배포한다.
3. 기존 Pod와 새 Pod가 동시에 장치를 열려고 하는지 확인한다.

### ✅ 기대 동작

기존 Pod가 장치를 놓은 뒤 새 Pod가 시작되어야 한다.

### ❌ 실제 동작

```text
동일 카메라 또는 오디오 장치를 두 프로세스가 동시에 열려고 시도
/dev/snd 또는 /dev/i2c-1 접근 충돌
센서/오디오 초기화 실패
장치 점유 상태가 꼬여 Pod 재시작 반복
```

### 🔍 시도한 것들

- [x] 하드웨어 의존 Deployment 목록 정리
- [x] `safe-edge-integrated-ai`, `safe-edge-audio`, `bme280-sensor` 전략 확인
- [x] 모두 `Recreate` 전략으로 유지

### 🚨 심각도

상

### 🗂️ 영역

AI / Hardware, K3s / Kubernetes, Operations / DR

### 💡 해결 방법

**근본 원인:**

RollingUpdate는 새 Pod를 먼저 만들고 기존 Pod를 나중에 종료한다. 하드웨어 장치는 동시에 여러 프로세스가 안정적으로 점유할 수 없다.

**해결 방법:**

하드웨어 의존 Deployment는 `strategy.type: Recreate`를 사용한다.

**재발 방지:**

카메라, 오디오, I2C 등 물리 장치를 사용하는 모든 workload 배치 정책에 `Recreate` 원칙을 명시한다.

## 🐛 트러블슈팅 리포트 - `safe-edge-integrated-ai` ai_detection 미기록 문제

### 📌 현상 요약

AI Pod는 Running이고 카메라도 인식하지만 InfluxDB에 `ai_detection` measurement가 생성되지 않았다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker2
- 네임스페이스: ai-apps, monitoring
- 관련 컴포넌트/버전: safe-edge-integrated-ai, Picamera2, libcamera, InfluxDB
- 발생 시각: 2026-05-06

### 🔁 재현 순서

1. worker2에서 `rpicam-hello --list-cameras`로 카메라 인식을 확인한다.
2. `safe-edge-integrated-ai` Pod 상태와 log를 확인한다.
3. InfluxDB에서 `SHOW MEASUREMENTS`와 `ai_detection` 최신 데이터를 조회한다.

### ✅ 기대 동작

AI Pod가 프레임을 캡처하고 YOLO 추론 후 `ai_detection` 데이터를 InfluxDB에 기록해야 한다.

### ❌ 실제 동작

```text
[INFO] Picamera2 연결 시도 중...
[INFO] 카메라 연결 및 설정 완료!
Camera frontend has timed out!
Please check that your camera sensor connector is attached securely.
```

Pod는 Running이지만 `ai_detection` write가 없다.

### 🔍 시도한 것들

- [x] Pod 위치와 log 확인
- [x] 컨테이너 내부 `/dev/video*`, `/dev/media*`, `/run/udev` 확인
- [x] InfluxDB measurement와 최신 row 확인
- [x] AI Deployment scale down/up으로 카메라 점유 상태 초기화

### 🚨 심각도

중

### 🗂️ 영역

AI / Hardware, Monitoring / Grafana / InfluxDB

### 💡 해결 방법

**근본 원인:**

카메라 장치 인식과 실제 프레임 캡처 성공은 다르다. `picam2.capture_array()`가 막히면 Pod는 Running이어도 YOLO 추론과 `ai_detection` write까지 진행되지 않는다.

**해결 방법:**

AI Deployment를 scale down/up해 카메라 점유 상태를 초기화하고, log의 `[AI STATUS]` 반복 출력과 InfluxDB `ai_detection` 최신 row를 확인한다.

**재발 방지:**

capture loop heartbeat, livenessProbe, 또는 일정 시간 `ai_detection` write가 없을 때 프로세스를 종료하는 watchdog을 추가한다.

