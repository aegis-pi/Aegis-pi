# Why

상태: draft
기준일: 2026-04-29

## 목적

이 문서는 Aegis-Pi에서 여러 대안 중 현재 방식을 선택한 이유를 정리한다.

단순히 가능한 기술을 나열하는 것이 아니라, 현재 프로젝트의 제약과 이미 검증된 기준선을 바탕으로 왜 특정 방식을 채택했는지 기록한다.

## 현재 핵심 선택

현재 Aegis-Pi의 클라우드 확장 기본 방향은 아래와 같다.

```text
factory-a / factory-b / factory-c
  -> K3s workload
  -> Edge Agent
  -> AWS IoT Core
  -> S3
  -> EKS Risk Services
  -> AMP / Grafana
```

즉, 엣지 실행 환경은 K3s를 유지하고, 클라우드 수신 진입점은 AWS IoT Core를 사용하며, Risk 계산은 Lambda가 아니라 EKS 위의 서비스로 둔다.

## 왜 K3s + Edge Agent + IoT Core인가

### 선택한 방식

```text
K3s Pod
  -> Edge Agent
  -> MQTT publish
  -> AWS IoT Core
  -> IoT Rule
  -> S3
```

### 대안

```text
AWS IoT Greengrass Core
  -> Greengrass Component
  -> AWS IoT Core
  -> S3
```

### 판단

현재 MVP에서는 Greengrass를 메인 런타임으로 도입하지 않는다.

`factory-a`는 이미 Raspberry Pi 3-node K3s 기준선이 구축되어 있고, 아래 운영 요소가 실제로 검증되어 있다.

```text
K3s 3-node cluster
ArgoCD GitOps
Longhorn PVC
worker2 preferred affinity
worker1 failover
master OS cron 기반 failback
image prepull DaemonSet
LAN 제거 / 전원 제거 failover 테스트
```

Greengrass는 엣지 디바이스에서 로컬 처리, ML 추론, 필터링/집계, 오프라인 동작, AWS IoT Core 연동을 제공하는 강한 선택지다. 그러나 현재 구조에 바로 넣으면 K3s와 Greengrass가 모두 엣지 런타임과 배포 관리 역할을 갖게 된다.

그 결과 아래 복잡도가 생긴다.

```text
K3s 배포 단위: Pod / Deployment / Helm
Greengrass 배포 단위: Component / Deployment

K3s 배포 제어: ArgoCD / ApplicationSet
Greengrass 배포 제어: Greengrass cloud deployment

K3s 장애 복구: scheduler / affinity / toleration / failback
Greengrass 장애 복구: Greengrass core 및 component lifecycle 기준
```

Aegis-Pi는 이미 K3s 기반 failover/failback과 GitOps 운영을 핵심 가치로 잡고 있으므로, MVP 단계에서 Greengrass를 추가하면 이중 운영 체계가 된다.

따라서 현재는 Edge Agent를 K3s workload로 구현하고, Edge Agent가 AWS IoT Core로 MQTT publish하는 방식을 선택한다.

### 선택 이유

| 기준 | K3s + Edge Agent | Greengrass |
| --- | --- | --- |
| 현재 구현 연속성 | 높음 | 낮음 |
| `factory-a` 검증 결과 재사용 | 높음 | 낮음 |
| ArgoCD/ApplicationSet과 정합성 | 높음 | 중간 |
| worker1/worker2 failover 설계 재사용 | 높음 | 낮음 |
| AWS IoT 네이티브 엣지 관리 | 낮음 | 높음 |
| 오프라인 버퍼링 기본 제공 | 낮음 | 높음 |
| MVP 구현 복잡도 | 낮음 | 높음 |

### 결론

```text
MVP:
  K3s + Edge Agent + IoT Core 사용

후속:
  장시간 오프라인 버퍼링, Greengrass component 기반 fleet 관리,
  로컬 메시징/필터링이 실제 병목이 되면 Greengrass 재검토
```

draw.io에서는 Greengrass를 현재 메인 구성요소로 그리지 않는다.

대신 Edge Agent 박스에 아래 주석을 둘 수 있다.

```text
Edge Agent
  runs on K3s
  publishes MQTT to AWS IoT Core
  future option: AWS IoT Greengrass component/runtime
```

## 왜 AWS IoT Core인가

### 선택한 방식

```text
Edge Agent
  -> AWS IoT Core MQTT endpoint
  -> IoT Rule
  -> S3
```

### 대안

```text
Edge Agent
  -> 직접 HTTP API
  -> EKS Ingress / API Gateway
  -> Risk Service
```

### 판단

AWS IoT Core는 디바이스 인증, MQTT 수신, Rules Engine, AWS 서비스 연동을 표준 기능으로 제공한다.

현재 Aegis-Pi는 공장별 Spoke가 Hub로 데이터를 보내는 구조이며, 향후 `factory-b`, `factory-c`가 추가된다. 이때 각 Spoke를 IoT Thing 또는 공장 단위 인증서로 분리하면 연결과 권한 관리가 명확해진다.

직접 HTTP API를 만들면 초기 구현은 단순할 수 있지만, 아래를 직접 설계해야 한다.

```text
디바이스 인증서 또는 토큰 관리
재연결 처리
메시지 라우팅
S3 적재
장애 로그
공장별 접근 제어
```

따라서 MVP에서는 AWS IoT Core를 클라우드 수신 진입점으로 사용한다.

### 결론

```text
Spoke -> Cloud 수신 계층은 AWS IoT Core를 사용한다.
IoT Rule을 통해 S3 raw data 적재를 표준 경로로 둔다.
```

## 왜 S3 Raw Data Lake인가

### 선택한 방식

```text
IoT Core
  -> S3 raw JSON
  -> Risk Normalizer
```

### 대안

```text
IoT Core
  -> Risk Service 직접 처리
```

또는

```text
IoT Core
  -> Timestream / DynamoDB
```

### 판단

S3는 원본 데이터를 가장 단순하고 오래 보존하기 쉬운 계층으로 둔다.

Aegis-Pi에서는 Risk 계산 기준, threshold, `pipeline_status`, Dummy Sensor 시나리오 값이 M7에서 보정될 수 있다. 원본을 S3에 남기면 계산 로직이 바뀌어도 재처리와 검증이 가능하다.

S3 경로는 아래처럼 공장/source_type/날짜 기준으로 나눈다.

```text
s3://<bucket>/
  factory-a/sensor/yyyy/MM/dd/
  factory-a/system_status/yyyy/MM/dd/
  factory-b/sensor/yyyy/MM/dd/
  factory-c/sensor/yyyy/MM/dd/
```

Risk Service로 직접 넣으면 지연은 줄어들 수 있지만, 원본 보존과 재처리 근거가 약해진다.

### 결론

```text
IoT Core 수신 데이터는 먼저 S3에 raw JSON으로 적재한다.
Risk Normalizer는 S3 raw data를 읽어 정규화한다.
```

## 왜 Risk 계산을 Lambda가 아니라 EKS 서비스로 하는가

### 선택한 방식

```text
S3 raw data
  -> Risk Normalizer on EKS
  -> Risk Score Engine on EKS
  -> Prometheus-compatible metrics
  -> AMP / Grafana
```

### 대안

```text
S3 event
  -> Lambda
  -> DynamoDB / Timestream / S3 processed
  -> Grafana
```

### 판단

Lambda는 단일 이벤트 변환이나 가벼운 후처리에 적합하다. 그러나 Aegis-Pi의 Risk 계산은 단순한 메시지 1건 변환보다 상태 기반 계산에 가깝다.

Risk Score Engine은 아래 판단을 해야 한다.

```text
최근 N분 센서 무수신
노드 이상 지속 시간
Edge Agent 이상 지속 시간
카메라/마이크 상태
pipeline_status 지연
공장별 top causes
score_delta_10m
safe / warning / danger 상태 전환
```

이 계산은 공장별 최근 상태를 유지하고, 이전 상태와 현재 상태를 비교해야 한다.

또한 현재 관제 방향은 Prometheus-compatible metrics를 노출하고 AMP/Grafana에서 조회하는 구조다. EKS 서비스는 `/metrics` 노출, ConfigMap 기반 설정, ArgoCD 배포, Kubernetes rollout과 자연스럽게 맞는다.

Lambda로 구현하면 아래가 추가로 필요해진다.

```text
상태 저장소
Lambda 배포 파이프라인
IAM/권한 분리
Grafana 조회용 저장소
EKS/ArgoCD와 별도 운영 체계
```

따라서 MVP에서는 Risk 계산 본체를 EKS 서비스로 둔다.

### 결론

```text
Risk Normalizer와 Risk Score Engine은 EKS `risk` namespace에서 실행한다.
Lambda는 필요하면 후속 보조 트리거 또는 가벼운 전처리 용도로만 검토한다.
```

## 왜 AMP / Grafana인가

### 선택한 방식

```text
Risk Score Engine
  -> Prometheus-compatible metrics
  -> AMP
  -> Grafana Hub
```

### 대안

```text
Risk Service
  -> 별도 REST API
  -> Custom Dashboard
```

### 판단

현재 `factory-a`는 이미 Grafana 기반 관제가 운영 기준선으로 검증되어 있다.

Hub 확장에서도 Grafana를 유지하면 아래 이점이 있다.

```text
기존 관제 경험 재사용
Prometheus/AMP 기반 메트릭 조회
Risk Score와 시스템 메트릭을 같은 화면에서 표현
별도 프론트엔드 MVP 구현 부담 감소
```

Custom Dashboard는 최종 제품 관점에서는 가능하지만, MVP에서는 구현 부담이 크다. 먼저 Grafana로 중앙 관제 구조를 완성하고, 이후 필요하면 별도 UI로 확장한다.

### 결론

```text
MVP 관제는 AMP + Grafana Hub를 사용한다.
Risk Twin 결과는 Prometheus-compatible metrics로 노출한다.
```

## 왜 ArgoCD / ApplicationSet인가

### 선택한 방식

```text
GitHub
  -> ArgoCD ApplicationSet
  -> factory-a / factory-b / factory-c
```

### 대안

```text
GitHub Actions
  -> kubectl apply
  -> 각 Spoke 직접 배포
```

### 판단

Aegis-Pi는 멀티 Spoke 구조를 목표로 한다.

공장별 values가 분리되어야 하고, 운영형 `factory-a`와 테스트베드형 `factory-b`, `factory-c`는 sync/rollback 정책이 다르다.

ArgoCD/ApplicationSet은 아래 구조와 맞다.

```text
charts/aegis-spoke
envs/factory-a/values.yaml
envs/factory-b/values.yaml
envs/factory-c/values.yaml
```

GitHub Actions에서 직접 `kubectl apply`를 수행하면 빠르게 만들 수 있지만, 배포 상태, drift, sync 이력, 공장별 정책 관리가 약해진다.

### 결론

```text
멀티 Spoke 배포는 ArgoCD/ApplicationSet으로 관리한다.
GitHub Actions는 이미지 build/push와 manifest update에 집중한다.
```

## 왜 Ansible 테스트 자동화인가

### 선택한 방식

```text
Ansible
  -> baseline 수집
  -> start_test 실행
  -> 상태 관측
  -> InfluxDB bucket query
  -> evidence pack 생성
```

### 대안

```text
수동 테스트 기록
```

또는

```text
완전 자동 장애 유발
```

### 판단

M0에서 LAN 제거와 전원 제거 테스트는 이미 수동으로 수행했다. 하지만 M7 통합 검증에서는 같은 계열의 테스트를 반복해야 한다.

수동 기록은 빠르지만, 반복 검증에서 baseline 누락, 시간창 오류, 로그 누락이 발생하기 쉽다.

반대로 전원 차단까지 완전 자동화하면 초기 범위가 과도해지고 하드웨어 위험이 커진다.

따라서 초기에는 Ansible을 테스트 오케스트레이터로 사용한다.

```text
자동화:
  상태 수집
  로그 수집
  query 실행
  결과 파일화

수동 유지:
  물리 LAN 제거
  물리 전원 제거
  최종 판정
```

### 결론

```text
Ansible은 M7 반복 검증을 위한 evidence 수집 자동화로 도입한다.
물리 장애 유발 자동화는 후속 확장으로 둔다.
```

## 현재 보류한 선택지

| 선택지 | 보류 이유 |
| --- | --- |
| AWS IoT Greengrass 메인 런타임 | K3s/ArgoCD와 역할이 겹치며 MVP 복잡도가 증가 |
| Lambda 기반 Risk 계산 | 상태 기반 Risk 계산과 AMP/Grafana 메트릭 노출 구조에 덜 적합 |
| 직접 HTTP API 수신 | 디바이스 인증, 메시지 라우팅, S3 적재를 직접 구현해야 함 |
| Custom Dashboard 우선 구현 | MVP에서는 Grafana 재사용이 더 빠르고 검증 가능 |
| 완전 자동 물리 장애 유발 | 하드웨어/안전/권한 리스크가 있어 후속으로 분리 |

## 향후 재검토 조건

아래 조건이 실제 병목으로 확인되면 현재 결정을 다시 검토한다.

```text
공장 인터넷 단절 시간이 길어져 오프라인 버퍼링이 핵심 요구가 되는 경우
K3s 운영 부담이 Greengrass fleet 관리보다 커지는 경우
엣지 로컬 메시징과 필터링이 복잡해지는 경우
Risk 계산이 단순 이벤트 변환 수준으로 축소되는 경우
Grafana로 MVP 관제 요구를 만족하지 못하는 경우
물리 장애 테스트를 정기적으로 무인 수행해야 하는 경우
```
