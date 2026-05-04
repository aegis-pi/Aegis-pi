# Issues 수정 필요 사항 정리

상태: draft
기준일: 2026-04-29

## 목적

`docs/issues/`의 기존 마일스톤 문서를 바로 수정하지 않고, 최근 설계 변경 사항을 기준으로 나중에 어떤 부분이 얼마나 바뀌었는지 비교할 수 있도록 수정 후보를 별도 정리한다.

기준이 되는 최근 변경 사항:

```text
edge-agent는 기존 Safe-Edge workload를 대체하지 않고 옆에 추가한다.
factory-a는 edge-agent real mode를 사용한다.
factory-b, factory-c는 edge-agent dummy mode를 사용한다.
초기 edge-agent는 직접 장치 접근을 하지 않는다.
초기 데이터 수집은 InfluxDB query + Kubernetes API status query를 사용한다.
AWS IoT Core 송신에는 idempotency key, checkpoint, reconnect/backoff, 최소 RBAC, Secret 분리를 적용한다.
MVP edge-agent는 1 replica, worker2 preferred, worker1 failover, master avoid로 둔다.
```

## 전체 수정 방향

### 현재 문서와 달라진 핵심

기존 issue 문서 일부는 아래 방식으로 읽힌다.

```text
입력 모듈이 직접 Edge Agent에 데이터를 준다.
Edge Agent가 BME280 등 실제 장치를 직접 수집할 수 있다.
Dummy Sensor가 별도 송신 주체가 될 수 있다.
S3 object key는 timestamp 중심이다.
배포 전략은 일반 RollingUpdate 기준으로 생각한다.
```

최근 설계 기준은 아래에 가깝다.

```text
기존 Safe-Edge workload가 먼저 InfluxDB에 쓴다.
edge-agent는 InfluxDB와 Kubernetes API를 읽어 클라우드로 송신한다.
factory-b/c는 별도 Dummy Sensor보다 edge-agent dummy mode를 우선 검토한다.
payload에는 message_id, source_timestamp, published_at을 포함한다.
S3 object key에는 message_id 또는 hash를 포함한다.
중복 publish 방지를 위해 MVP edge-agent는 1 replica와 Recreate 전략을 권장한다.
```

## 우선순위

```text
1. M4_data-plane.md
2. M1_hub-cloud.md
3. M3_deploy-pipeline.md
4. M5_vm-spoke-expansion.md
5. M7_integration-test.md
6. M0_factory-a_safe-edge-baseline.md
7. MASTER_CHECKLIST.md
```

## M4_data-plane.md

수정 필요도: 높음

### Issue 1 - 표준 입력 스키마 확정

현재 보강 필요:

```text
timestamp 중심 필드만 있다.
message_id, source_timestamp, published_at, agent_instance_id가 없다.
idempotency key 기준이 없다.
```

수정 방향:

```text
필수 공통 필드에 message_id 추가
timestamp를 source_timestamp로 명확화
published_at 추가
agent_instance_id 추가 검토
message_id 생성 규칙 추가
source_type별 payload 예시에 message_id 반영
```

권장 필드:

```text
message_id
factory_id
node_id
source_type
measurement
source_timestamp
published_at
agent_instance_id
environment_type
input_module_type
payload
```

### Issue 2 - Edge Agent 수집/변환 로직 구현

현재 보강 필요:

```text
BME280 온도/습도 직접 수집처럼 읽힌다.
카메라/마이크 직접 상태 확인 범위가 불명확하다.
checkpoint와 중복 송신 방지 기준이 없다.
```

수정 방향:

```text
초기 수집 방식은 InfluxDB query + Kubernetes API status query로 명시
직접 /dev/i2c-1, camera, mic 접근은 후속 단계로 이동
last_sent checkpoint 구현을 DoD에 추가
message_id 생성 로직을 DoD에 추가
재시작 후 중복 송신 제한을 Acceptance Criteria에 추가
```

추가할 구현 기준:

```text
InfluxDB에서 environment_data, ai_detection, acoustic_detection 조회
Kubernetes API에서 pod/node/deployment 상태 조회
edge_agent_checkpoint marker measurement 또는 Longhorn PVC 기반 checkpoint 사용
message_id = factory_id + measurement/source_type + source_timestamp 조합으로 시작
```

### Issue 3 - Edge Agent 컨테이너화 및 K3s 배포 준비

현재 보강 필요:

```text
디바이스 마운트 요구사항 정리가 포함되어 있다.
초기 edge-agent는 직접 장치 접근을 하지 않으므로 device mount는 기본 요구사항이 아니다.
Secret, ConfigMap, ServiceAccount/RBAC, checkpoint 저장소 기준이 부족하다.
```

수정 방향:

```text
디바이스 마운트는 후속 직접 장치 접근 모드 후보로 내린다.
AWS IoT 인증서 Secret mount 기준 추가
ConfigMap 환경값 기준 추가
ServiceAccount/RBAC 최소 권한 추가
resource request/limit 추가
worker2 preferred / worker1 failover / master avoid 추가
MVP strategy Recreate 추가
```

필수 배포 리소스 후보:

```text
ConfigMap: edge-agent-config
Secret: aws-iot-factory-a-cert
ServiceAccount: edge-agent
Role/ClusterRole/RoleBinding: 최소 read 권한
Deployment: edge-agent
```

### Issue 4 - Edge Agent -> IoT Core 연결 및 수신 확인

현재 보강 필요:

```text
재연결 로직은 있으나 backoff 기준이 없다.
QoS 기준이 없다.
인증서 Git 금지와 Secret 운영 기준이 약하다.
```

수정 방향:

```text
MQTT QoS 1 권장 추가
initial backoff 1s, max backoff 60s, jitter enabled 추가
인증서/private key Git commit 금지 추가
Kubernetes Secret 수동 주입, 후속 SealedSecrets/External Secrets/SOPS 검토 추가
IoT policy 최소 topic 권한 추가
```

### Issue 5 - IoT Core -> S3 적재 확인

현재 보강 필요:

```text
S3 object key가 <timestamp>.json 중심이다.
중복 제거 가능한 key 기준이 없다.
```

수정 방향:

```text
object key에 message_id 또는 hash 포함
partition은 factory_id/source_type/date 유지
중복 publish 시 같은 object key로 덮어쓰기 또는 idempotent 처리 기준 결정
```

권장 예시:

```text
s3://<bucket>/factory_id=factory-a/source_type=sensor/date=2026-04-29/<message_id>.json
```

### Issue 8 - 데이터 플레인 end-to-end 검증

현재 보강 필요:

```text
중복 송신, checkpoint, backoff 검증이 없다.
```

수정 방향:

```text
edge-agent 재시작 후 checkpoint 기반 재송신 확인 추가
같은 원본 데이터의 message_id 안정성 확인 추가
IoT Core 단절 후 backoff 재연결 확인 추가
S3 object key에 message_id/hash 포함 확인 추가
worker2 장애 후 worker1 재스케줄 상태 송신 확인 추가
```

## M1_hub-cloud.md

수정 필요도: 높음

### Issue 4 - Hub/S3 버킷 생성 및 경로 파티셔닝 설계

현재 보강 필요:

```text
경로 예시가 factory-a/sensor/yyyy/mm/dd/<timestamp>.json 형태다.
message_id/hash 기반 object key가 없다.
```

수정 방향:

```text
partition key는 factory_id/source_type/date 기준 유지
object key에는 message_id 또는 hash 포함
중복 메시지 idempotent 처리 기준 추가
```

### Issue 5 - Hub/IoT Core Thing / 인증서 / 규칙 구성

현재 보강 필요:

```text
공장별 Thing 또는 통합 Thing 방식 결정으로 열려 있다.
최근 계획은 공장 단위 Thing이다.
IoT policy topic 범위가 구체적이지 않다.
인증서 보관 기준이 짧다.
```

수정 방향:

```text
Thing은 AEGIS-IoTThing-factory-a, AEGIS-IoTThing-factory-b, AEGIS-IoTThing-factory-c 공장 단위로 시작
topic prefix는 aegis/factory-a, aegis/factory-b, aegis/factory-c
policy는 각 Thing이 자기 factory topic에만 publish 가능하도록 제한
인증서/private key는 Git 금지
K3s에는 Kubernetes Secret으로 주입
후속 운영 Secret 관리 후보 명시
```

## M3_deploy-pipeline.md

수정 필요도: 높음

### Issue 1 - Helm 저장소 구조 설계

현재 보강 필요:

```text
factory_id, environment_type, input_module_type 정도만 있다.
edge-agent 운영 설정이 부족하다.
```

수정 방향:

```text
edge_agent_mode 추가
aws_iot_topic_prefix 추가
checkpoint_backend 추가
mqtt_qos 추가
resources 추가
nodeAffinity / tolerations 추가
secretName 추가
```

공장별 values 예시:

```text
factory-a:
  edge_agent_mode: real
  input_module_type: sensor
  checkpoint_backend: influxdb

factory-b/c:
  edge_agent_mode: dummy
  input_module_type: dummy
```

### Issue 2 - ECR 저장소 구성 및 이미지 태그 전략

현재 보강 필요:

```text
Edge Agent와 Dummy Sensor가 별도 이미지처럼 보인다.
```

수정 방향:

```text
MVP는 edge-agent 단일 이미지 우선
factory-b/c dummy mode는 같은 edge-agent 이미지 설정으로 분기
Dummy Sensor 별도 이미지는 후속 후보로 조정
```

### Issue 5 - ArgoCD 동기화 정책 및 롤백 정책

현재 보강 필요:

```text
RollingUpdate 전략 설정이라고 되어 있다.
```

수정 방향:

```text
workload 성격별 strategy 분리로 변경
hardware pod: Recreate
RWO PVC pod: Recreate
edge-agent MVP: Recreate 권장
stateless 검증 완료 후 RollingUpdate 검토
```

## M5_vm-spoke-expansion.md

수정 필요도: 중간

### Issue 5 - Dummy Sensor 모듈 구현 및 배포

현재 보강 필요:

```text
Dummy Sensor가 별도 모듈/파드로 IoT Core에 직접 송신하는 흐름처럼 보인다.
최근 기준은 edge-agent 하나를 만들고 mode로 real/dummy를 나누는 방식이다.
```

수정 방향:

```text
Issue 이름 또는 설명을 edge-agent dummy input mode 중심으로 조정
factory-b/c는 edge-agent dummy mode로 동일 송신 로직 사용
별도 Dummy Sensor 이미지는 후속 후보 또는 내부 input module로 정리
```

### Issue 7 - factory-b/c 데이터 플레인 연결 확인

현재 보강 필요:

```text
Dummy Sensor -> IoT Core -> S3 흐름으로 표현된다.
```

수정 방향:

```text
edge-agent dummy mode -> IoT Core -> S3 흐름으로 변경
factory-b/c도 message_id, checkpoint, backoff 기준을 동일하게 적용
```

## M7_integration-test.md

수정 필요도: 중간

### Issue 1 - factory-a 운영형 시나리오 검증

추가할 검증:

```text
message_id가 중복 제거 가능한 형태인지 확인
edge-agent 재시작 후 checkpoint 기준으로 중복 송신이 제한되는지 확인
IoT Core 단절 후 backoff/reconnect 확인
S3 object key에 message_id/hash 포함 확인
```

### Issue 3 - Failover 시나리오

추가할 검증:

```text
worker2 장애 시 edge-agent가 worker1로 재스케줄되는지 확인
재스케줄 후 system_status 또는 pipeline 관련 상태 송신 유지 확인
worker2 복구 후 중복 publish 여부 확인
checkpoint가 failover/failback 중 깨지지 않는지 확인
```

## M0_factory-a_safe-edge-baseline.md

수정 필요도: 낮음

M0는 완료된 기준선 문서이므로 큰 구조 변경은 하지 않는 편이 좋다. 다만 현재 운영 상태 보강 후보는 있다.

보강 후보:

```text
Grafana: master 배치
ArgoCD: worker1 배치
Prometheus/InfluxDB: worker1 배치
AI/audio/BME: worker2 배치
AI/audio/BME strategy: Recreate
AI/audio memory limit: 2000Mi
Grafana/InfluxDB strategy: Recreate
```

단, M0 문서는 완료 시점 기록으로 남길 수도 있으므로, 수정 여부는 나중에 결정한다.

## MASTER_CHECKLIST.md

수정 필요도: 낮음

현재 체크 상태를 바꿀 필요는 없다.

수정이 필요한 경우:

```text
M4/M5 issue 제목을 edge-agent dummy mode 기준으로 바꾸는 경우 checklist 제목도 같이 맞춘다.
M3에서 Dummy Sensor 별도 이미지 표현을 제거하면 checklist 표현도 같이 맞춘다.
```

## 아직 바로 수정하지 않는 이유

기존 issue 문서는 초기 접근과 설계 가정을 담고 있다. 현재 바로 덮어쓰면 초반 설계에서 어떤 점이 바뀌었는지 추적하기 어렵다.

따라서 우선 이 문서에 변경 후보를 남기고, 실제 M1~M5 구현을 시작할 때 해당 이슈 파일을 순서대로 갱신한다.
