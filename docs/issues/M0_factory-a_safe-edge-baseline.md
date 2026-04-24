# M0. `factory-a` Safe-Edge 기준선 복구

> **마일스톤 목표**: Aegis-Pi 전체 구현의 출발점. `factory-a` 라즈베리파이 K3s 클러스터를 Safe-Edge 기준선으로 다시 세운다.  
> 이 마일스톤이 완료되어야 M1(Hub 구성) 이후 모든 단계가 시작 가능하다.

---

## Issue 1 - [Safe-Edge/OS] Raspberry Pi OS Lite 각 노드 기본 세팅

### 🎯 목표 (What & Why)

Master / Worker-1 / Worker-2 세 노드의 OS 환경을 통일한다.  
노드 간 OS 상태가 다르면 K3s 설치 및 Longhorn 복제에서 예측 불가한 문제가 생긴다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Raspberry Pi OS Lite (GUI 없는 버전) 이미지 설치
- [ ] 각 노드 hostname 고정
  - `master`, `worker-1`, `worker-2`
- [ ] SSH 활성화 및 접속 확인
- [ ] time sync (NTP) 설정 완료
- [ ] 기본 패키지 업데이트 완료
- [ ] SSD 마운트 가능 확인
- [ ] 카메라 `/dev/video*`, 마이크 `/dev/snd`, I2C 센서 인식 확인 (worker-2 기준)

### 🔍 Acceptance Criteria

- 세 노드 모두 동일한 hostname, OS 버전, SSH 접속 상태
- `lsblk`에서 SSD 인식
- `v4l2-ctl --list-devices`, `arecord -l`, `i2cdetect -y 1` 정상 응답 (worker-2)

---

## Issue 2 - [Safe-Edge/네트워크] 하드웨어/네트워크 기준선 구성

### 🎯 목표 (What & Why)

모든 노드의 역할과 IP를 고정하고, MetalLB 주소 범위와 DHCP 충돌을 먼저 설계한다.  
네트워크 기반이 흔들리면 이후 K3s, Longhorn, MetalLB 전체가 불안정해지기 때문에 가장 먼저 안정화한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 노드별 고정 IP 확정 및 적용
  - `master` = `10.10.10.10`
  - `worker-1` = `10.10.10.11`
  - `worker-2` = `10.10.10.12`
  - `host-pc` = `10.10.10.100`
- [ ] 모든 노드가 동일 L2 스위치에 연결되어 상호 통신 가능
- [ ] MetalLB용 내부 VIP 범위 확정 (노드 IP와 겹치지 않는 대역)
- [ ] DHCP 충돌 없음 확인
- [ ] Host PC에서 각 노드 SSH 접근 가능

### 🔍 Acceptance Criteria

- `ping 10.10.10.10 / .11 / .12 / .100` 전부 응답
- 동일 노드에 DHCP 재할당 시 IP가 바뀌지 않음
- MetalLB 예정 대역이 노드 IP 및 라우터 IP와 겹치지 않음

---

## Issue 3 - [Safe-Edge/K3s] 3-Node 클러스터 구성 및 taint/label 적용

### 🎯 목표 (What & Why)

K3s Control Plane을 Master에 설치하고 Worker-1, Worker-2를 조인한다.  
Master는 NoSchedule taint로 보호하고, Worker-2를 Active Zone, Worker-1을 Standby Zone으로 구분한다.  
이 구조가 Failover 정책의 기반이 된다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Master에 K3s Control Plane 설치 및 node token 확보
- [ ] Worker-1, Worker-2 K3s 조인 완료
- [ ] Master `NoSchedule` taint 적용
  ```bash
  kubectl taint nodes master node-role.kubernetes.io/master=true:NoSchedule
  ```
- [ ] Worker-1 label/taint 적용
  ```bash
  kubectl label nodes worker-1 role=standby zone=buffer
  kubectl taint nodes worker-1 zone=buffer:NoSchedule
  ```
- [ ] Worker-2 label 적용
  ```bash
  kubectl label nodes worker-2 role=active zone=danger
  ```
- [ ] 3-Node 클러스터 `Ready` 상태 확인

### 🔍 Acceptance Criteria

- `kubectl get nodes` 에서 3개 노드 모두 `Ready`
- Master에 파드가 스케줄되지 않음 확인
- Worker-2에 테스트 파드 우선 배치 확인

---

## Issue 4 - [Safe-Edge/MetalLB] MetalLB + Traefik 네트워크 서비스 계층 구성

### 🎯 목표 (What & Why)

내부망 서비스 노출의 공통 기반이 되는 MetalLB VIP와 Traefik Ingress 계층을 먼저 구성한다.  
이 이슈에서는 서비스 계층 자체를 안정화하는 데 집중하고, ArgoCD / Grafana 실제 UI 접근 검증은 각 서비스 이슈(Issue 7, 8)에서 수행한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] MetalLB 설치 및 내부 VIP 범위 적용
- [ ] Traefik K3s 내장 Ingress 기준 동작 확인
- [ ] 외부 노출 최소화 정책 적용
- [ ] 테스트용 HTTP 서비스 및 Ingress 배포 후 내부망 접근 확인
- [ ] VIP 충돌 없음 확인

### 🔍 Acceptance Criteria

- `kubectl get svc -A`에서 MetalLB가 할당한 EXTERNAL-IP 확인
- 내부망에서 테스트용 서비스에 브라우저 또는 `curl`로 접근 성공
- 외부 대역에서 해당 VIP로 접근 불가 확인

---

## Issue 5 - [Safe-Edge/Longhorn] 3-Node 복제 구성

### 🎯 목표 (What & Why)

Safe-Edge의 핵심 설계 자산인 데이터 생존성을 구현한다.  
Worker-2가 파괴되어도 Worker-1에 복제된 데이터가 살아있어야 한다.  
Longhorn StorageClass 복제본 수를 3으로 설정하여 모든 노드에 데이터를 분산 보존한다.

> 실행 전 사전 점검 필수:
> `open-iscsi` / `iscsid` 상태, 노드별 SSD 마운트 경로, Longhorn 요구 마운트 조건,
> Master `NoSchedule` taint 환경에서 Longhorn 시스템 컴포넌트 배치 정책을 먼저 확인한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Longhorn 사전 요구사항 점검 완료
  - 각 노드 `open-iscsi` 설치 및 `iscsid` 활성화 확인
  - 노드별 SSD 경로 표준화 및 실제 마운트 확인
  - Longhorn 요구 마운트 조건 확인
  - Master taint 환경에서 Longhorn 시스템 컴포넌트 배치 전략 결정
- [ ] 각 노드 SSD 경로 정상 인식 확인
- [ ] Longhorn 설치 및 StorageClass 복제본 수 3 설정
- [ ] Master 포함 3-Node 복제 참여 확인
- [ ] Hot Storage 기준 Longhorn PVC 생성 및 마운트 확인
- [ ] Longhorn UI에서 복제 상태 정상 확인

### 🔍 Acceptance Criteria

- 각 노드에서 `iscsid` 활성 상태 확인
- Longhorn이 사용할 디스크 경로가 노드별로 일관되게 보임
- Longhorn 시스템 컴포넌트가 taint 정책과 충돌 없이 배치됨
- Longhorn UI에서 Volume 상태 `Healthy`, 복제본 3개 확인
- 테스트 PVC 생성 후 `kubectl get pvc` 에서 `Bound` 상태
- Worker-2 노드 강제 종료 후 Longhorn Volume 상태 `Degraded` → 자동 복구 확인

---

## Issue 6 - [Safe-Edge/NFS] Host PC NFS Cold Storage 구성

### 🎯 목표 (What & Why)

Hot Storage(Longhorn SSD)에서 오래된 데이터를 Cold Storage(Host PC HDD NFS)로 이관하는 티어링 구조의 기반을 만든다.  
NFS가 안정적으로 마운트되지 않으면 이후 티어링 스크립트 전체가 동작하지 않는다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Host PC에 NFS 서버 설치 및 공유 경로 설정
- [ ] 각 Worker 노드에서 NFS 마운트 가능 확인
- [ ] NFS 마운트 경로 및 권한 설정 완료
- [ ] 재부팅 후에도 NFS 마운트 유지 확인 (`/etc/fstab` 설정)

### 🔍 Acceptance Criteria

- Worker-1, Worker-2에서 `mount | grep nfs` 정상 출력
- NFS 경로에 파일 쓰기/읽기 가능
- Host PC 재부팅 후에도 NFS 서비스 자동 시작

---

## Issue 7 - [배포/ArgoCD] GitLab + ArgoCD GitOps 복구

### 🎯 목표 (What & Why)

폐쇄망 내부에서 GitOps 배포 자동화를 완성한다.  
코드 변경이 push되면 ArgoCD가 감지하고 K3s에 자동으로 반영되어야 한다.  
이 파이프라인이 Safe-Edge 운영 자동화의 핵심이며, Aegis-Pi의 GitOps 구조 검증 기반이 된다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Host PC에 GitLab 설치 및 구동
- [ ] Master에 ArgoCD 설치
- [ ] GitLab 저장소 ArgoCD 등록
- [ ] ArgoCD Application 생성
- [ ] Auto Sync 설정 및 동작 확인
- [ ] push → ArgoCD 감지 → K3s 배포 반영 흐름 확인

### 🔍 Acceptance Criteria

- GitLab에 push 후 ArgoCD UI에서 `Synced` 상태 전환 확인
- K3s에 배포된 파드가 변경 내용 반영
- ArgoCD UI 내부망 브라우저 접근 가능

---

## Issue 8 - [관제/Grafana] Prometheus + InfluxDB + Grafana 모니터링 구성

### 🎯 목표 (What & Why)

노드 상태, 센서 데이터, AI 감지 결과를 시각화하는 모니터링 스택을 구성한다.  
Grafana 대시보드에서 온도/습도/노드 메트릭이 실시간으로 보여야 Failover 및 이상 상태를 확인할 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Prometheus K3s 내부 설치 및 Node Exporter 구성
  - CPU / 메모리 / 온도 / 파일시스템 메트릭 수집
- [ ] InfluxDB 설치 및 Longhorn PVC 연결
- [ ] Grafana Host PC Docker 구동
- [ ] Grafana 데이터 소스 연결
  - Prometheus
  - InfluxDB
- [ ] 최소 확인 항목 대시보드 구성
  - 노드 CPU/메모리
  - SSD 여유 공간
  - BME280 온도/습도/기압

### 🔍 Acceptance Criteria

- Grafana UI에서 노드 CPU/메모리 실시간 확인 가능
- InfluxDB에 센서 데이터 시계열 적재 확인
- Prometheus `targets` 페이지에서 모든 노드 `UP` 상태

---

## Issue 9 - [데이터/BME280] BME280 + 카메라 + 마이크 입력 계층 구성

### 🎯 목표 (What & Why)

실제 환경 센서와 장치 입력을 K3s 파드와 연결한다.  
카메라와 마이크 디바이스가 파드에 마운트되어야 YOLOv8/YAMNet AI 추론이 가능하다.

### ✅ 완료 조건 (Definition of Done)

- [ ] BME280 I2C 센서 인식 및 데이터 수집 확인
- [ ] BME280 → InfluxDB 주기 기록 동작 확인
- [ ] 카메라 `/dev/video*` 파드 디바이스 마운트 확인
- [ ] 마이크 `/dev/snd` 파드 디바이스 마운트 확인
- [ ] 카메라/마이크 상태 (연결 여부, 프로세스 생존 여부) 수집 동작 확인

### 🔍 Acceptance Criteria

- InfluxDB에 온도/습도/기압 데이터 주기적으로 적재
- 파드 내부에서 `/dev/video*`, `/dev/snd` 접근 가능
- 카메라/마이크 상태 수집 값이 Grafana에서 확인 가능

---

## Issue 10 - [Safe-Edge/YOLOv8] YOLOv8 + YAMNet AI 파드 배포 및 Worker-2 배치

### 🎯 목표 (What & Why)

YOLOv8(영상 감지)과 YAMNet(음향 감지) 파드를 Worker-2에 우선 배치한다.  
Worker-2가 Active Zone이므로 AI 추론 파드는 Worker-2에서 실행되어야 하고,  
Failover 시 Worker-1으로 승계되는 구조를 전제로 배치 정책을 잡는다.

### ✅ 완료 조건 (Definition of Done)

- [ ] YOLOv8 파드 Worker-2 우선 배치 (`nodeAffinity` 또는 `nodeSelector` 적용)
- [ ] YAMNet 파드 Worker-2 우선 배치
- [ ] AI 추론 결과 InfluxDB 저장 확인
- [ ] ARM64 이미지 호환성 확인 (Raspberry Pi 환경)
- [ ] 파드 정상 기동 및 추론 동작 확인

### 🔍 Acceptance Criteria

- `kubectl get pods -o wide`에서 AI 파드가 `worker-2` 노드에서 실행 중
- InfluxDB에 AI 감지 결과 시계열 적재 확인
- Grafana에서 AI 감지 결과 확인 가능

---

## Issue 11 - [Safe-Edge/Failover] Failover 정책 복구 (tolerationSeconds, affinity)

### 🎯 목표 (What & Why)

Worker-2 장애 시 Worker-1이 AI 감시 임무를 자동으로 승계하는 Failover 구조를 복구한다.  
`tolerationSeconds: 30`을 기준으로 T+55초 안팎에 Worker-1에서 파드가 재기동되어  
2분 이내 감시가 재개되는 타임라인을 목표로 한다.

> ⚠️ 주의: Safe-Edge 환경에서 Failover eviction 타이밍은 `tolerationSeconds` (파드 스펙)로 제어한다.  
> 표준 K8s의 `node-monitor-grace-period`와 혼동하지 않는다.

### ✅ 완료 조건 (Definition of Done)

- [ ] AI 파드 스펙에 `tolerationSeconds: 30` 적용
  - `node.kubernetes.io/unreachable`
  - `node.kubernetes.io/not-ready`
- [ ] Worker-2 `zone=danger`, Worker-1 `zone=buffer` label 기반 affinity 설정
- [ ] Worker-2 장애 시나리오 테스트 실행
- [ ] Failover 타임라인 확인
  - T+15s: NotReady 감지
  - T+45s: Eviction + 재스케줄링 시작
  - T+55s 안팎: Worker-1에서 파드 재기동
  - 목표: 2분 이내 감시 재개
- [ ] Longhorn 복제 데이터가 유지된 상태로 재기동 확인

### 🔍 Acceptance Criteria

- Worker-2 전원 차단 후 2분 이내 Worker-1에서 AI 파드 `Running`
- Longhorn Volume 데이터 유지 확인 (파드 재기동 후 이전 데이터 접근 가능)
- Grafana에서 Failover 전후 데이터 연속성 확인

---

## Issue 12 - [자동화/Ansible] Hot/Cold 티어링 + Ansible Playbook 복구

### 🎯 목표 (What & Why)

Hot Storage(Longhorn SSD)에서 Cold Storage(NFS HDD)로 오래된 데이터를 자동 이관하는 티어링을 복구한다.  
Ansible Playbook으로 운영 자동화 기준선을 코드화하여 재부팅/복구 시에도 주요 자동화가 동작하게 한다.

> 참고: K3s CronJob 방식은 NFS hostPath 마운트 타임아웃 문제로 인해 사용하지 않는다.  
> Worker-1 호스트의 Linux native crontab에서 직접 실행하는 방식을 기준으로 한다.
>
> 실행 원칙: 이 이슈는 한 번에 처리하지 않고 아래 두 단계로 나눠 진행한다.  
> 1) 기반 자동화 복구: `network.yml`, `nfs.yml`, `healthcheck.yml`  
> 2) 데이터 운영 자동화 복구: `tiering.yml`, `run_tiering.sh`, `run_photo_tiering.sh`, `auto_failback.sh`
>
> `auto_failback.sh`는 Failover 정책(Issue 11) 검증 결과를 기준으로 최종 확정한다.

### ✅ 완료 조건 (Definition of Done)

- [ ] Ansible Playbook 기준선 복구
  - `network.yml`
  - `nfs.yml`
  - `healthcheck.yml`
- [ ] 기반 자동화 적용 후 네트워크 / NFS / 헬스체크 정상 동작 확인
- [ ] Worker-1 crontab 기반 티어링 스크립트 복구
  - `run_tiering.sh`
  - `run_photo_tiering.sh`
  - `auto_failback.sh`
- [ ] `tiering.yml` 복구 및 NFS 연결 검증 로직 포함 (mount exit code 기반)
- [ ] 재부팅 후 자동화 스크립트 정상 동작 확인

### 🔍 Acceptance Criteria

- `ansible-playbook -i hosts network.yml`, `nfs.yml`, `healthcheck.yml` 정상 실행
- 기반 자동화 적용 후 NFS 마운트와 상태 점검이 정상 동작
- crontab 실행 후 NFS 경로에 Cold Data 이관 확인
- NFS 미연결 시 스크립트가 에러 없이 종료 (마운트 exit code 기반 분기)
- Failover 정책 기준이 확정된 뒤 `auto_failback.sh` 동작 검증 가능
- 재부팅 후 NFS 마운트 및 tiering 스크립트 자동 복구

---

## Issue 13 - [검증/통합] Safe-Edge 기준선 통합 검증

### 🎯 목표 (What & Why)

M0의 모든 구성이 실제로 연결되어 동작하는지 end-to-end로 검증한다.  
이 이슈가 완료되어야 M1(Hub 클라우드 구성)으로 넘어갈 수 있다.

### ✅ 완료 조건 (Definition of Done)

- [ ] 센서값이 InfluxDB와 Grafana에 실시간으로 표시됨
- [ ] Git push 후 ArgoCD가 K3s에 자동 반영됨
- [ ] Worker-2 중단 시 Worker-1이 2분 이내 AI 감시 승계
- [ ] Longhorn 복제 데이터가 Failover 후에도 유지됨
- [ ] NFS Cold 티어링이 스케줄대로 동작함
- [ ] Grafana에서 노드/센서/AI 결과 전체 확인 가능

### 🔍 Acceptance Criteria

- 위 6개 완료 조건 전부 실측 통과
- Failover 후 감시 재개까지 2분 이내 달성
- Grafana 대시보드에서 전체 스택 상태 한눈에 확인 가능
- `factory-a`가 Safe-Edge 기준선으로 단독 동작 가능하다고 판단
