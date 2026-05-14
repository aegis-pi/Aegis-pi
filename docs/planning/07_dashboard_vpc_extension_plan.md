# Dashboard VPC Extension Plan

상태: draft
기준일: 2026-04-30

## 목적

본사 관리자 대시보드를 Tailscale/VPN 의존 없이 접근할 수 있도록 별도 Dashboard VPC 기반 관제 구조를 설계한다.

이 문서는 기존 Hub/Spoke 제어망과 별개로, 관리자 조회 화면을 public authenticated ingress로 제공하는 확장 방향을 정리한다.

## 최신 기준

2026-05-09 기준 최종 클라우드 아키텍처의 source of truth는 `docs/planning/15_cloud_architecture_final.md`다.

이 문서의 `Dashboard VPC`와 `Processing VPC` 분리 표현은 초기 확장안이다. 최신 기준에서는 아래 이름과 경계를 사용한다.

```text
1번 VPC: Data / Dashboard VPC
  - 데이터 처리
  - Risk 계산
  - 사용자 대시보드

2번 VPC: Control / Management VPC
  - 중앙 배포
  - Hub-Spoke 연결
  - 운영 관측
```

이 문서에서 유지할 결정은 Dashboard가 Tailscale, ArgoCD, EKS API, Spoke K3s API에 직접 접근하지 않는다는 경계다.

## 핵심 결정

Dashboard VPC와 Processing VPC는 VPC Peering 또는 Transit Gateway로 직접 연결하지 않는다.

두 영역 사이의 공유 지점은 네트워크가 아니라 AWS 관리형 저장소와 IAM 권한이다.

```text
Tailscale: Hub -> Spoke 제어/배포/운영 접근망
Dashboard VPC: 관리자 조회망
S3/DynamoDB/Timestream: 조회망과 처리망 사이의 데이터 계약
```

## 목표 구조

```text
factory-a / factory-b / factory-c
  -> Edge Agent
  -> AWS IoT Core
  -> S3 raw

Processing VPC
  -> Lambda data processor
  -> S3 processed
  -> DynamoDB LATEST/HISTORY

Dashboard VPC
  -> Route53
  -> ALB
  -> WAF
  -> Cognito or IdP auth
  -> Dashboard Web/API
  -> read-only access to DynamoDB LATEST/HISTORY + S3 processed
```

명시적으로 금지하는 경로:

```text
Dashboard VPC -> Processing VPC private service direct call
Dashboard VPC -> EKS admin API
Dashboard VPC -> ArgoCD admin API
Dashboard VPC -> Spoke K3s API
Dashboard VPC -> raw S3 bucket full access
```

## 보안 요구와 해결 방식

| 보안 요구 | 설계 대응 |
| --- | --- |
| 관리자 대시보드 외부 접근 | Route53 + ALB + WAF + Cognito/Auth |
| Processing 계층 private 유지 | Processing VPC에는 public ingress를 두지 않음 |
| 침해 범위 축소 | Dashboard VPC는 조회 전용 저장소 권한만 보유 |
| VPC 간 lateral movement 방지 | VPC Peering/TGW 없음 |
| 최소 권한 | Dashboard API IAM role은 processed prefix와 latest table read-only |
| 감사 가능성 | ALB/WAF/CloudTrail/VPC Flow Logs를 영역별로 분리 |
| 운영자 접근과 제어망 분리 | 사람은 Dashboard, 제어/배포는 Tailscale/ArgoCD |

## 데이터 저장소 역할

```text
S3 raw
  - IoT Core에서 들어온 원시 데이터 저장
  - 재처리, 감사, 이력 보존

S3 processed
  - Lambda data processor 처리 결과 저장
  - 상세 조회, 리포트, drill-down

DynamoDB LATEST/HISTORY
  - 공장별 최신 상태
  - risk level
  - top reasons
  - last_received_at
  - pipeline_status
  - dashboard 빠른 조회
```

S3만으로 대시보드를 구성할 수는 있지만 최신 상태 조회가 느릴 수 있다. MVP 대시보드는 latest/status 저장소를 우선 읽고, 상세 이력은 S3 processed를 조회한다.

## Edge에서 올려야 하는 상태

Dashboard VPC가 Spoke나 Processing VPC 내부 API를 직접 조회하지 않으므로, 현장 상태도 Edge Agent가 데이터 플레인으로 올려야 한다.

권장 source type:

```text
sensor
system_status
workload_status
device_status
pipeline_heartbeat
event
```

권장 상태 항목:

```text
sensor_status:
  - BME280 수신 여부
  - 최근 측정 시각
  - 센서 read 실패 횟수
  - I2C 접근 오류 여부

device_status:
  - camera available
  - mic/audio device available
  - snapshot write success/failure

node_status:
  - master/worker1/worker2 Ready 여부
  - CPU/memory/disk usage
  - disk pressure / memory pressure
  - k3s-agent active 여부

workload_status:
  - bme280-sensor Running 여부
  - safe-edge-integrated-ai Running 여부
  - safe-edge-audio Running 여부
  - pod node placement
  - restart count
  - failover/failback 상태

pipeline_heartbeat:
  - edge-agent alive
  - last publish success/failure
  - last successful publish timestamp
```

예시 payload:

```json
{
  "message_id": "factory-a:system_status:worker2:2026-04-30T01:00:00Z",
  "factory_id": "factory-a",
  "node_id": "worker2",
  "source_type": "system_status",
  "source_timestamp": "2026-04-30T01:00:00Z",
  "published_at": "2026-04-30T01:00:02Z",
  "status": {
    "node_ready": true,
    "cpu_usage_pct": 42.1,
    "memory_usage_pct": 63.4,
    "disk_usage_pct": 71.2,
    "k3s_agent_active": true,
    "sensor_bme280_recent": true,
    "camera_available": true,
    "audio_device_available": true,
    "pod_restarts": {
      "safe-edge-integrated-ai": 1,
      "safe-edge-audio": 0,
      "bme280-sensor": 0
    }
  }
}
```

## IoT Core 병목 관리

상태 데이터가 추가되면 메시지 수는 증가하지만, system/workload/device status는 작은 JSON이다. MVP 규모에서는 주기와 payload 크기를 제한하면 IoT Core 병목은 관리 가능하다.

권장 전송 정책:

```text
heartbeat:
  주기: 10~15초
  payload: 최소 필드

full system_status:
  주기: 30~60초
  payload: 노드/워크로드/장치 요약

status change event:
  상태 변화 시 즉시 전송

sensor / ai / audio event:
  기존 수집 주기 또는 이벤트 발생 시 전송
```

Topic 분리:

```text
aegis/factory-a/sensor
aegis/factory-a/event
aegis/factory-a/system_status
aegis/factory-a/workload_status
aegis/factory-a/device_status
aegis/factory-a/heartbeat
```

확장 시 작은 S3 object가 과도하게 늘어나면 아래 구조를 검토한다.

```text
MVP:
  IoT Core -> IoT Rule -> S3

확장:
  IoT Core -> IoT Rule -> Kinesis Firehose -> S3 batch
```

## 예상 지연

MVP 기준 예상 지연은 수집 주기, AWS 처리 지연, 대시보드 refresh 주기의 합이다.

```text
현장 상태 변화 발생
  -> Edge Agent 감지:        0~10초
  -> IoT Core publish:       0.1~2초
  -> IoT Rule / S3 적재:     1~5초
  -> Lambda/DynamoDB 처리:   1~10초
  -> latest DB 반영:         0.1~2초
  -> Dashboard refresh:      5~15초

총 예상 지연:
  일반 상태 변화: 10~35초
  보수적 worst case: 30~60초
```

상태별 기준:

| 데이터 | 권장 주기 | 대시보드 반영 예상 |
| --- | ---: | ---: |
| heartbeat | 10~15초 | 10~25초 |
| node/workload 상태 | 30초 | 30~50초 |
| 센서 최신값 | 기존 수집 주기 + 처리 | 10~40초 |
| AI/audio 이벤트 | 이벤트 발생 즉시 publish | 5~20초 |
| Risk score | 입력 반영 후 계산 | 15~45초 |
| 장애 감지 | heartbeat miss 기준 | 40~60초 |

권장 MVP 기준:

```text
heartbeat: 10초
full system_status: 30초
status change event: 즉시
dashboard refresh: 10초
장애 판정: heartbeat 3회 miss
```

이 대시보드는 실시간 제어 화면이 아니라 운영 관제 화면이다. 10~60초 지연은 MVP 관제 목적에서는 수용 가능한 범위로 본다.

## Dashboard 화면 기준

```text
공장 카드:
  - factory-a/b/c 상태: SAFE / WARNING / DANGER
  - 마지막 수신 시각
  - 주요 원인 Top 3

노드 상태:
  - master / worker1 / worker2 Ready
  - CPU / memory / disk

입력 장치 상태:
  - BME280
  - camera
  - microphone

워크로드 상태:
  - AI Running node
  - Audio Running node
  - BME Running node
  - restart count

데이터 파이프라인:
  - IoT publish status
  - S3 raw latest
  - processed latest
  - risk result latest
```

## 장점

- 관리자는 Tailscale 없이 인증된 URL로 접근한다.
- Processing VPC는 public ingress 없이 private하게 유지한다.
- Dashboard 침해가 EKS/ArgoCD/Spoke 제어망 침해로 바로 이어지지 않는다.
- VPC Peering이 없으므로 VPC 간 lateral movement 경로를 만들지 않는다.
- Dashboard API는 read-only IAM으로 제한할 수 있다.
- Dashboard와 처리 계층을 독립적으로 배포/확장할 수 있다.

## 단점과 제약

- 대시보드가 현장 또는 Processing 내부 API를 직접 조회하지 않는다.
- 대시보드 반영은 데이터 적재/처리 이후에 가능하다.
- latest/status 저장소 설계가 필요하다.
- Cognito/Auth, WAF, ALB, Dashboard API 운영이 추가된다.
- raw/processed/latest 데이터 모델이 불명확하면 대시보드가 느려질 수 있다.

## M1~M6 반영 기준

```text
M1:
  Dashboard VPC, ALB, WAF, Auth, DynamoDB LATEST/HISTORY 조회를 설계에 포함

M4:
  Edge Agent가 sensor뿐 아니라 system_status, device_status, workload_status, heartbeat를 송신

M6:
  Grafana-only 중앙 관제에서 Dashboard Web/API + latest store 조회 구조로 확장

M7:
  현장 상태 변화 -> IoT/S3 -> latest store -> Dashboard 반영 지연을 실측
```

## 결론

Dashboard VPC는 조회 전용 public access 영역이고, cloud-side data processing은 Lambda data processor와 managed storage 중심으로 둔다.

두 VPC를 네트워크로 연결하지 않고, DynamoDB LATEST/HISTORY와 S3 processed를 IAM read-only로 조회하는 구조를 목표 확장안으로 둔다.

## 2026-05-14 수정 방향

이 문서의 `Processing VPC`, `Normalizer`, `Risk Engine` 표현은 이전 확장안의 용어다.

최신 MVP 기준은 아래 흐름이다.

```text
IoT Core
  -> IoT Rule -> S3 raw
  -> Lambda data processor
      -> DynamoDB LATEST
      -> DynamoDB HISTORY
      -> S3 processed
Dashboard Web/API
  -> read-only DynamoDB + S3 processed
```

별도 `risk-normalizer`, `risk-score-engine`, `pipeline-status-aggregator` 컨테이너 서비스는 MVP 구현 대상에서 제외한다.
