# Safe-Edge 기준선 부트스트랩 가이드

상태: source of truth
기준일: 2026-04-24

## 목적

`factory-a`에서 Safe-Edge 기준선을 다시 구성하는 순서를 운영 문서 관점에서 정리한다.

## 현재 상태

- 이 문서는 구현 순서 기준 가이드다.
- 실제 명령과 매니페스트 경로는 추후 보강 예정이다.
- 현재는 `factory-a`를 Safe-Edge 기준선으로 다시 세우기 위한 운영 순서와 검증 기준을 정리한 상태다.

## 범위

- 선행 조건
- 목표 상태
- 단계별 구성 순서
- 확인 방법
- Aegis-Pi 확장으로 넘어가는 조건

## 상세 내용

## Safe-Edge 기준선 목표

이 문서에서 말하는 복구 완료 상태는 아래를 만족하는 상태다.

- `factory-a`가 3노드 K3s 기반으로 동작한다.
- 내부망에서 ArgoCD, Grafana, 주요 서비스 접근이 가능하다.
- 센서/카메라/마이크 기반 입력 경로가 다시 동작한다.
- Longhorn 복제와 NFS Cold Storage 경로가 복구된다.
- Git push 이후 ArgoCD를 통한 반영이 가능하다.
- Worker 장애 시 감시 워크로드가 재기동 가능한 기준선이 확보된다.

## 전제조건

- Raspberry Pi 3노드 준비
- 내부망 IP 계획 수립
- Host PC 준비
- 외장 SSD/NFS 대상 준비

추가 전제:

- `factory-a`는 실제 운영형 Spoke로 취급한다.
- 이 단계에서는 아직 AWS Hub나 IoT Core를 붙이지 않는다.
- 먼저 로컬 Safe-Edge 기준선을 복구하고, 그 다음 Aegis-Pi 확장으로 넘어간다.

## 기본 노드 역할

| 노드 | IP | 역할 |
| --- | --- | --- |
| `master` | `10.10.10.10` | K3s Control Plane, ArgoCD |
| `worker-1` | `10.10.10.11` | Hot Standby, Longhorn 복제 |
| `worker-2` | `10.10.10.12` | 센서/AI 워크로드 |
| `host-pc` | `10.10.10.100` | NFS, GitLab, Grafana |

## 단계

1. Raspberry Pi OS 및 기본 설정
2. K3s 3노드 클러스터 구성
3. MetalLB / Traefik 구성
4. Longhorn / NFS 구성
5. GitLab + ArgoCD 기준선 복구
6. Prometheus / InfluxDB / Grafana 구성
7. 센서 / 카메라 / 마이크 입력 복구
8. Failover / 운영 자동화 기준 확인

## M0 이슈 흐름과의 대응

현재 구현은 아래 흐름으로 진행한다.

1. OS 기본 세팅
2. 하드웨어 / 네트워크 기준선
3. K3s 3-Node 구성 및 taint / label 적용
4. MetalLB + Traefik
5. Longhorn 3-Node 복제
6. Host PC NFS Cold Storage
7. GitLab + ArgoCD 복구
8. Prometheus + InfluxDB + Grafana
9. BME280 + 카메라 + 마이크 입력 계층
10. YOLOv8 + YAMNet AI 파드 배치
11. Failover 정책 복구
12. Hot / Cold 티어링 + Ansible Playbook 복구
13. Safe-Edge 기준선 통합 검증

즉, 이 문서의 8개 단계는 실제로는 위 13개 이슈를 묶어서 설명한 운영 가이드다.

## 단계별 상세 정리

### 1. Raspberry Pi OS 및 기본 노드 준비

목표:

- 각 노드가 동일한 기본 운영 상태를 갖도록 맞춘다.

해야 할 일:

- hostname 고정
- SSH 접속 확인
- 시간 동기화 확인
- SSD 마운트 준비
- 카메라, 마이크, 센서 인식 확인

완료 기준:

- `master`, `worker-1`, `worker-2`가 고정 IP와 hostname으로 안정적으로 접근 가능
- 장치 인식 상태를 OS 수준에서 확인 가능

### 2. K3s 3노드 클러스터 구성

목표:

- `master` 중심 Control Plane과 두 개의 Worker를 연결한다.

해야 할 일:

- Master에 K3s Control Plane 구성
- Worker 1, Worker 2 조인
- Master `NoSchedule` taint 적용
- Worker 역할 label/taint 적용

완료 기준:

- 3노드 K3s 클러스터 정상 구성
- Master 보호 정책 반영
- Worker별 역할 구분 가능

### 3. MetalLB / Traefik 네트워크 계층 구성

목표:

- 내부망에서 서비스 접근이 가능하도록 네트워크 계층을 정리한다.

해야 할 일:

- MetalLB VIP 범위 확정
- Traefik 노출 정책 정리
- ArgoCD / Grafana / 주요 서비스 접근 경로 설정

완료 기준:

- 내부망에서 주요 관리 서비스 접근 가능
- VIP 충돌 없음

### 4. Longhorn / NFS 스토리지 계층 구성

목표:

- Hot Storage와 Cold Storage 기준선을 복구한다.

해야 할 일:

- Longhorn 배포
- 복제본 수 3 기준 확인
- SSD 경로 확인
- Host PC NFS 구성
- Hot / Cold tier 구분 반영

완료 기준:

- Longhorn 복제 정상
- NFS 마운트 정상
- Hot/Cold 저장 경로가 다시 설명 가능

### 5. GitLab + ArgoCD 기준선 복구

목표:

- Safe-Edge 방식의 GitOps 운영 흐름을 다시 확보한다.

해야 할 일:

- Host PC GitLab 준비
- Master ArgoCD 배치
- 저장소 연결
- Application 생성 및 동기화 확인

완료 기준:

- Git push -> ArgoCD sync -> K3s 반영 흐름 확인 가능

### 6. Prometheus / InfluxDB / Grafana 기준선 복구

목표:

- 노드 상태와 센서/AI 시계열을 다시 볼 수 있게 한다.

해야 할 일:

- Prometheus 스택 확인
- InfluxDB 저장 확인
- Host PC Grafana 연동
- 최소 메트릭과 시계열 패널 확인

완료 기준:

- Prometheus 메트릭 조회 가능
- InfluxDB 입력 가능
- Grafana에서 주요 데이터가 보임

### 7. 센서 / 카메라 / 마이크 입력 복구

목표:

- 실제 운영형 입력 계층을 Safe-Edge 기준선 수준으로 다시 세운다.

해야 할 일:

- BME280 입력 확인
- 카메라 연결 및 관련 프로세스 상태 확인
- 마이크 연결 및 관련 프로세스 상태 확인
- Worker 2 우선 배치 구조 확인

완료 기준:

- 온도/습도 수집 가능
- 카메라/마이크 상태 확인 가능
- 입력 계층이 다시 운영 기준선에 올라옴

### 8. Failover / 운영 자동화 기준 확인

목표:

- Safe-Edge가 의미 있던 이유였던 생존성과 운영 자동화를 다시 확인한다.

해야 할 일:

- Worker 2 우선 / Worker 1 대기 구조 확인
- 장애 시 재기동 흐름 확인
- tiering / failback / healthcheck 스크립트 기준 확인

완료 기준:

- Worker 장애 시 승계 흐름 설명 가능
- 데이터 보존 구조 유지
- 운영 자동화 복구 방향이 정리됨

## 확인 방법

- `kubectl get nodes`
- Longhorn 복제 상태 확인
- ArgoCD sync 확인
- InfluxDB 입력 확인
- Grafana 대시보드 조회

추가 확인 항목:

- 센서값이 실제로 갱신되는가
- 카메라/마이크 관련 프로세스 상태가 정상인가
- Worker 2 정지 시 Worker 1 승계 가능성이 보이는가

## Safe-Edge 완료로 판단하는 최소 기준

- 3노드 K3s가 정상 동작한다.
- Longhorn 복제와 NFS 경로가 복구된다.
- GitOps 반영이 가능하다.
- Grafana에서 기본 메트릭과 센서 데이터가 보인다.
- 센서/카메라/마이크 입력이 다시 연결된다.

## Aegis-Pi 확장으로 넘어가는 조건

아래가 만족된 뒤에만 다음 단계로 넘어간다.

1. `factory-a`가 Safe-Edge 기준선으로 다시 동작한다.
2. 센서/상태/저장/모니터링의 최소 경로가 확인된다.
3. Failover와 운영 자동화의 기준선이 다시 설명 가능하다.

그 다음 단계:

1. `factory-b`, `factory-c` 테스트베드형 Spoke 구성
2. Hub 배포 제어 구조 연결
3. IoT Core -> S3 -> Risk Twin 연결

## TODO

- TODO: 실제 설치 명령 추가
- TODO: Longhorn values 경로 추가
- TODO: MetalLB IP pool 값 추가
- TODO: GitLab / ArgoCD 실제 구성 파일 경로 추가
- TODO: Failover 검증 절차를 별도 운영 문서로 분리할지 결정
