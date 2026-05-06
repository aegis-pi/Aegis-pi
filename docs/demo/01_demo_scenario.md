# 데모 시나리오

상태: source of truth
기준일: 2026-05-06

## 목적

현재 구현된 `factory-a` Safe-Edge 기준선으로 시연 가능한 데모 흐름을 정리한다.

## 현재 가능한 데모

```text
factory-a 단독 Safe-Edge 운영 상태 확인
Grafana 센서/AI dashboard 확인
ArgoCD GitOps sync 확인
Longhorn storage 확인
worker2 장애 -> worker1 failover -> worker2 failback 확인
```

AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선, Hub Prometheus Agent, 내부 Grafana/AMP datasource, Foundation S3 bucket, AMP Workspace, IoT Rule -> S3 raw 적재, `factory-a` IoT Thing/Policy/K3s Secret, Hub IRSA S3/AMP 권한은 2026-05-06 기준 `build-all`로 재생성했고 active 상태를 확인했다. `factory-b`, `factory-c`, Risk Twin 통합 화면은 후속 데모다.

## 데모 순서

### 1. Factory-A 구조 설명

보여줄 것:

```text
master 10.10.10.10
worker1 10.10.10.11
worker2 10.10.10.12
```

전달 메시지:
- 현재 완료된 것은 실제 Raspberry Pi 기반 `factory-a` 운영형 기준선이다.
- worker2가 센서/AI/Audio 우선 노드이고 worker1이 failover standby다.

### 2. ArgoCD GitOps 확인

보여줄 것:

```text
ArgoCD UI: 10.10.10.200
safe-edge-monitoring
safe-edge-ai-apps
```

전달 메시지:
- monitoring과 ai-apps를 분리해 배포한다.
- GitHub repo push 후 ArgoCD UI sync로 반영한다.

### 3. Grafana Dashboard 확인

보여줄 것:

```text
Grafana UI: 10.10.10.202
InfluxDB sensor / AI dashboard
Node Exporter Full 1860
```

전달 메시지:
- 온도/습도/기압과 AI 결과를 InfluxDB에서 읽는다.
- 노드 상태는 Prometheus 1860 dashboard로 본다.

### 4. Longhorn Storage 확인

보여줄 것:

```text
Longhorn UI: 10.10.10.201
InfluxDB PVC
ai-apps PVC 없음
AI snapshot hostPath /var/lib/safe-edge/snapshots
```

전달 메시지:
- 시계열 데이터와 AI 추론 결과는 InfluxDB PVC를 통해 Longhorn에 저장된다.
- AI event snapshot은 node-local hostPath에 임시 저장하고, 24시간 cleanup과 매일 03:00 KST purge를 적용했다.

### 5. 장애 복구 결과 설명

보여줄 것:

```text
docs/ops/09_failover_failback_test_results.md
```

전달 메시지:
- LAN 제거와 k3s-agent 중지 테스트에서 failover/failback이 성공했다.
- AI snapshot PVC 제거 후 Longhorn Multi-Attach 없이 AI가 worker1로 정상 failover됐다.
- 데이터 공백과 중복 write 후보도 측정했다.

## 핵심 수치

```text
전원 제거 첫 관찰 -> worker2 NotReady: 약 42초
worker2 NotReady -> worker1 전체 Running: 약 32초
전원 제거 첫 관찰 -> worker1 전체 Running: 약 74초
전원 재연결 첫 관찰 -> worker2 전체 Running: 약 2분 11초
failover 1초 bucket 최대 공백: 65-75초
failback 1초 bucket 최대 공백: 2초
```

## 데모 성공 기준

```text
ArgoCD apps Synced / Healthy
Grafana dashboard 갱신
Longhorn volumes healthy
대상 Pod 3개 worker2 Running
장애 테스트 결과 문서화 완료
```
