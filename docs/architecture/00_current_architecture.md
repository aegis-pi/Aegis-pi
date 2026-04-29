# 현재 구조 요약

상태: source of truth
기준일: 2026-04-29

## 목적

현재 실제로 구축된 `factory-a` Safe-Edge 로컬 구조를 설명한다.

## 현재 상태

- 현재 구현 완료 범위는 `factory-a` 단일 운영형 Spoke다.
- AWS Hub, `factory-b`, `factory-c`, IoT Core, S3, ECR, GitHub Actions, Tailscale은 아직 구축 전이다.
- 이 문서는 목표 Hub/Spoke 구조가 아니라 현재 동작 중인 로컬 기준선을 설명한다.

## 물리 / 클러스터 구조

```text
factory-a
├── master  10.10.10.10  K3s control plane
├── worker1 10.10.10.11  failover standby
└── worker2 10.10.10.12  sensor / AI / audio preferred
```

Kubernetes:

```text
K3s v1.34.6+k3s1
```

## Namespace 구조

```text
argocd
longhorn-system
monitoring
ai-apps
```

역할:

| Namespace | 역할 |
| --- | --- |
| `argocd` | GitOps 배포 제어 |
| `longhorn-system` | PVC 및 replica storage |
| `monitoring` | InfluxDB, Prometheus, Grafana |
| `ai-apps` | BME280, integrated AI, audio, image prepull |

## 관리 UI

| UI | 주소 |
| --- | --- |
| ArgoCD | `http://10.10.10.200` |
| Longhorn | `http://10.10.10.201` |
| Grafana | `http://10.10.10.202` |

## 배포 구조

현재 배포 흐름:

```text
GitHub safe-edge-config-main
    -> ArgoCD UI refresh / sync
    -> safe-edge-monitoring
    -> safe-edge-ai-apps
    -> factory-a K3s
```

GitOps repo:

```text
https://github.com/aegis-pi/safe-edge-config-main.git
```

Application:

```text
safe-edge-monitoring
safe-edge-ai-apps
```

현재는 GitHub Actions / ECR / ApplicationSet 기반 멀티 Spoke 배포가 아니라, GitHub repo와 ArgoCD Application을 이용한 로컬 `factory-a` GitOps 기준선이다.

## 데이터 구조

현재 데이터 흐름:

```text
BME280 / camera / mic / AI
    -> ai-apps Pods
    -> InfluxDB safe_edge_db
    -> Grafana dashboard
```

`edge-agent`는 현재 운영 workload가 아니다. 후속 클라우드 확장 단계에서 기존 `bme280-sensor`, `safe-edge-integrated-ai`, `safe-edge-audio` 옆에 추가될 송신 컴포넌트다. 초기 계획은 직접 장치 접근이 아니라 InfluxDB query와 Kubernetes API status query를 사용해 AWS IoT Core로 전송하는 방식이다.

InfluxDB measurement:

```text
environment_data
ai_detection
acoustic_detection
```

주요 field:

```text
environment_data.temperature
environment_data.humidity
environment_data.pressure
ai_detection.fire_detected
ai_detection.fallen_detected
ai_detection.bending_detected
acoustic_detection.is_danger
```

## 저장소 구조

```text
InfluxDB PVC -> Longhorn
AI snapshot -> node-local hostPath
AI inference result -> InfluxDB PVC -> Longhorn
```

보존 정책:

```text
InfluxDB safe_edge_db: 1일 retention
AI snapshots: 24시간 초과 jpg/jpeg/png 삭제
```

AI snapshot:

```text
mount path: /app/snapshots
hostPath: /var/lib/safe-edge/snapshots
cleanup: snapshot-cleanup sidecar
```

## 모니터링 구조

Grafana datasource:

```text
InfluxDB: 센서 / AI / 소리 데이터
Prometheus: 노드 상태
```

Dashboard:

```text
Factory-A sensor / AI dashboard
Node Exporter Full 1860
```

## Failover / Failback 구조

정책:

```text
worker2 preferred affinity
tolerationSeconds: 30
worker1 failover standby
master OS cron 기반 Kubernetes-only failback
```

대상 Pod:

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
```

Failback 원칙:

- worker2가 Ready일 때만 진행한다.
- worker2에 대상 Pod가 이미 Running이면 skip한다.
- worker1에 남은 대상 Pod만 순차 삭제한다.
- Kubernetes CronJob이 아니라 master OS cron에서 `kubectl`만 실행한다.

## Image Prepull 구조

`safe-edge-image-prepull` DaemonSet은 worker1/worker2에 큰 이미지를 미리 받아 둔다.

목적:

```text
failover 시 worker1에서 이미지 pull 지연 감소
새 이미지 태그 배포 전 worker1/worker2 이미지 준비
```

## 현재 검증 결과

LAN 제거:

```text
Failover 성공
Failback 성공
10초 bucket 기준 데이터 공백 없음
중복 write 후보 있음
```

전원 제거:

```text
Failover 성공
Failback 성공
전원 제거 첫 관찰 -> worker1 전체 Running: 약 74초
전원 재연결 첫 관찰 -> worker2 전체 Running: 약 2분 11초
Longhorn degraded 후 healthy 복귀
```

1초 bucket 연속 공백:

```text
failover environment_data: 최대 65초
failover ai_detection: 최대 72초
failover acoustic_detection: 최대 75초
failback 각 항목: 최대 2초
```

## 현재 구조 밖의 항목

다음 항목은 현재 구조가 아니라 후속 목표 구조다.

```text
AWS EKS Hub
factory-b / factory-c
Tailscale Hub-Spoke 연결
IoT Core
S3
ECR
GitHub Actions
Risk Score Engine
AMP
ApplicationSet
edge-agent
```

후속 구조는 `docs/architecture/01_target_architecture.md`에서 관리한다.
