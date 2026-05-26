# OS / Raspberry Pi Troubleshooting

원본: `docs/ops/04_troubleshooting.md`

## 🐛 트러블슈팅 리포트 - cgroup 설정 확인 중 `cgroup_disable=memory` 표시

### 📌 현상 요약

Raspberry Pi 노드에서 K3s 실행에 필요한 memory cgroup 설정이 불명확하게 보였다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: master, worker1, worker2
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Raspberry Pi OS, K3s, cgroup v2
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. 각 노드에서 `/proc/cmdline`을 확인한다.
2. `cgroup_disable=memory` 문자열이 남아 있는지 확인한다.
3. `/sys/fs/cgroup/cgroup.controllers`에서 실제 controller 목록을 확인한다.

### ✅ 기대 동작

K3s 실행에 필요한 `memory` cgroup controller가 활성화되어 있어야 한다.

### ❌ 실제 동작

```text
/proc/cmdline:
cgroup_disable=memory

/sys/fs/cgroup/cgroup.controllers:
cpuset cpu io memory pids
```

`/proc/cmdline`에는 비활성화 문자열이 보였지만 실제 controller에는 `memory`가 있었다.

### 🔍 시도한 것들

- [x] `/boot/firmware/cmdline.txt` 백업
- [x] `cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory` 추가
- [x] 세 노드 재부팅
- [x] 실제 cgroup v2 controller 상태 확인

### 🚨 심각도

상

### 🗂️ 영역

OS / Raspberry Pi, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

K3s는 memory cgroup이 필요하지만 Raspberry Pi 부팅 파라미터와 실제 cgroup v2 controller 상태가 혼동될 수 있다.

**해결 방법:**

`/boot/firmware/cmdline.txt`에 cgroup 활성화 파라미터를 추가하고 재부팅한다. 최종 판단은 `/proc/cmdline` 문자열만 보지 말고 `/sys/fs/cgroup/cgroup.controllers`에서 `memory` controller가 실제 활성화됐는지 확인한다.

**재발 방지:**

Raspberry Pi OS baseline 문서에 cgroup 부팅 파라미터와 확인 명령을 포함한다.

## 🐛 트러블슈팅 리포트 - I2C 장치 파일 없음

### 📌 현상 요약

BME280 센서 확인 시 `/dev/i2c-1` 장치 파일이 없어 센서를 읽을 수 없었다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s
- 노드: worker1, worker2
- 네임스페이스: monitoring
- 관련 컴포넌트/버전: Raspberry Pi OS, I2C, BME280
- 발생 시각: 2026-04-27

### 🔁 재현 순서

1. worker 노드에서 `/dev/i2c-1` 존재 여부를 확인한다.
2. `i2cdetect -y 1`을 실행한다.
3. `/boot/firmware/config.txt`의 I2C 설정을 확인한다.

### ✅ 기대 동작

`/dev/i2c-1`이 존재하고 `i2cdetect -y 1`에서 BME280 주소 `0x76`이 보여야 한다.

### ❌ 실제 동작

```text
ls: cannot access '/dev/i2c-1': No such file or directory
Error: Could not open file `/dev/i2c-1' or `/dev/i2c/1': No such file or directory

/boot/firmware/config.txt:
#dtparam=i2c_arm=on
```

### 🔍 시도한 것들

- [x] `/boot/firmware/config.txt` 백업
- [x] `dtparam=i2c_arm=on` 활성화
- [x] worker 노드 재부팅
- [x] 사용자가 장비에서 직접 `i2cdetect -y 1` 확인

### 🚨 심각도

상

### 🗂️ 영역

OS / Raspberry Pi, AI / Hardware, Monitoring

### 💡 해결 방법

**근본 원인:**

Raspberry Pi 펌웨어 설정에서 I2C가 비활성화되어 BME280 센서 접근에 필요한 장치 파일이 생성되지 않았다.

**해결 방법:**

`/boot/firmware/config.txt`에서 `dtparam=i2c_arm=on`을 활성화하고 재부팅한다. 이후 `i2cdetect -y 1`에서 `0x76` 주소를 확인한다.

**재발 방지:**

하드웨어 셋업 가이드에 I2C 활성화, 재부팅, 센서 주소 확인 절차를 필수 단계로 넣는다.

