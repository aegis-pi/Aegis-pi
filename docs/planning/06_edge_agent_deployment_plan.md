# Edge Data-Plane 배포 계획

상태: draft
기준일: 2026-05-20

## 목적

클라우드 확장을 위해 `factory-a/b/c` K3s에 배포할 Edge data-plane workload와 Hub ArgoCD 배포 방식을 정리한다.

2026-05-15 기준으로 단일 `edge-agent` real/dummy mode 계획은 폐기한다. 현재 기준은 입력 변환과 IoT Core 송신을 분리하는 구조다.

```text
factory-a:
  raw/log/status data
    -> factory-a-log-adapter
    -> local spool/outbox
    -> edge-iot-publisher
    -> AWS IoT Core

factory-b/c:
  VM-local dummy-data-generator
    -> worker hostPath outbox
    -> edge-iot-publisher
    -> AWS IoT Core
```

## 컴포넌트

| 컴포넌트 | 배포 위치 | 역할 |
| --- | --- | --- |
| `factory-a-log-adapter` | `factory-a` K3s | 실제 Safe-Edge raw/log/status 데이터를 canonical JSON으로 변환 |
| `dummy-data-generator` | `factory-b/c` VM 로컬 script/systemd service | canonical JSON 형식의 가데이터 생성 |
| `edge-iot-publisher` | `factory-a/b/c` K3s | local spool/outbox의 JSON을 AWS IoT Core로 MQTT publish |

`apps/edge-agent`는 M3 GitHub Actions/ECR 검증용 smoke image로 남긴다. 실제 데이터 플레인 구현은 M4/M5에서 위 컴포넌트 이름으로 추가한다.

## 배포 책임

```text
Terraform
  -> IoT Core, S3, ECR, IAM, OIDC 같은 AWS 리소스

Ansible
  -> Hub ArgoCD bootstrap, kubeconfig/cluster 등록, Secret 주입 보조

GitHub Actions
  -> image build/test/push

GitOps repo + Hub ArgoCD
  -> factory-a K3s adapter/publisher 배포와 drift 관리
  -> factory-b/c K3s publisher 배포와 drift 관리
```

GitHub Actions는 Spoke K3s에 직접 `kubectl apply`하지 않는다. Hub ArgoCD가 Tailscale 경로로 각 Spoke cluster에 배포한다.

## M4 배포 순서

1. `docs/specs/iot_data_format.md` 기준으로 canonical JSON 계약을 확정한다.
2. `factory-a-log-adapter`가 `factory-a` raw/log/status를 읽어 `factory_state`, `infra_state` JSON을 만든다.
3. adapter는 publish 성공 여부를 직접 판단하지 않고 local spool/outbox에 기록한다.
4. `edge-iot-publisher`가 outbox JSON을 읽어 AWS IoT Core topic에 publish한다.
5. Hub ArgoCD가 `factory-a` K3s에 adapter와 publisher를 배포한다.
6. IoT Core Rule이 S3 raw prefix에 object를 생성하는지 확인한다.
7. S3 object body가 canonical JSON 계약과 일치하는지 검증한다.

## M4 Adapter 입력 기준

`factory-a-log-adapter`는 MVP에서 장치를 직접 잡지 않는다. 기존 Safe-Edge workload가 이미 쓰고 있는 `/dev/i2c-1`, camera, mic 접근을 adapter가 공유하면 하드웨어 충돌과 rollout 위험이 커지기 때문이다.

초기 입력 source:

```text
factory_state:
  InfluxDB safe_edge_db
  URL: http://influxdb-svc.monitoring.svc.cluster.local:8086

infra_state:
  Kubernetes API
```

수집 기준:

| 구분 | Source | 비고 |
| --- | --- | --- |
| BME280 온도/습도/기압 | InfluxDB `environment_data` | 최근 3초 평균 |
| AI fire/fall/bend score | InfluxDB `ai_detection` | 최근 3초 평균 |
| 이상소음 | InfluxDB `acoustic_detection` | 최근 3초 집계. `sum(is_danger) > 0`이면 대표 `event_type`, 아니면 `"none"` |
| 노드 Ready | Kubernetes API Node status | `infra_state.nodes[]` |
| 워크로드 상태 | Kubernetes API Pod/Deployment status | `restart_count`, `node_id` 포함 |
| 장치 summary | 워크로드 상태 + 최근 InfluxDB write timestamp | 직접 장치 접근 없음 |
| CPU/memory/disk usage | metrics API 또는 Prometheus 후속 확인 | 미확정 시 `null` |

adapter 환경변수:

```text
AEGIS_INFLUXDB_URL=http://influxdb-svc.monitoring.svc.cluster.local:8086
AEGIS_INFLUXDB_DATABASE=safe_edge_db
AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox
```

대안 source 판단:

| 방식 | 판단 |
| --- | --- |
| Pod logs | fallback/debug only. 로그 포맷 변경에 취약하므로 primary source로 쓰지 않는다. |
| 기존 workload shared output | future candidate. structured JSON file, shared volume, HTTP endpoint 방식은 후속 개선으로 검토한다. |
| direct device access | out of scope. 기존 BME/AI/audio workload와 장치 충돌 가능성이 있어 M4에서 제외한다. |

## M5 확장 순서

`factory-b/c`는 실제 센서가 없으므로 VM 로컬 `dummy-data-generator`가 canonical JSON을 만든다. IoT Core 송신은 `factory-a`와 같은 `edge-iot-publisher`를 사용한다.

```text
factory-b/c VM worker
  local dummy-data-generator
    -> /var/lib/aegis/outbox

factory-b/c K3s worker
  edge-iot-publisher
    -> hostPath /var/lib/aegis/outbox
```

이 구조를 통해 테스트베드 공장도 실제 데이터 플레인과 같은 IoT Core/S3/Lambda/Dashboard 경로를 탄다.

dummy generator를 Kubernetes Deployment로 배포하지 않는 이유는 테스트베드 입력을 VM 로컬에서 직접 제어하려는 요구 때문이다. ArgoCD는 공장별 publisher와 Kubernetes 리소스 상태만 관리하고, 입력 데이터 생성 프로세스는 각 VM 담당자가 로컬에서 시작/중지한다.

## Placement 기준

`factory-a`에서는 기존 Safe-Edge workload 배치 기준을 따른다.

- `worker2` preferred
- `worker1` failover
- `master` avoid
- 1 replica부터 시작
- local spool/outbox가 중복 publish를 제어할 때까지 보수적 update 전략 사용

초기에는 두 sender가 동시에 같은 outbox를 처리하지 않도록 `edge-iot-publisher`를 1 replica로 둔다. checkpoint/idempotency 검증 후 RollingUpdate 확장을 검토한다.

`factory-b/c`에서는 worker node에 `aegis.workload-node=true` label을 적용하고 publisher를 해당 worker에 고정한다. outbox가 `hostPath`이므로 publisher Pod가 다른 노드에 뜨면 VM 로컬 generator가 쓰는 파일을 볼 수 없다. 테스트베드 b/c는 worker 1대 기준으로 이 제약을 수용한다.

## Secret 기준

IoT Core 인증서와 private key는 K3s Secret으로 주입한다.

```text
namespace: ai-apps
secret: aws-iot-<factory-id>-cert
mount path: /etc/aegis/iot
```

Secret 값은 Git에 저장하지 않는다. 생성과 주입 절차는 `docs/ops/12_iot_core_thing_secret_mount.md`를 따른다.

M4 data-plane workload namespace는 `ai-apps`로 확정했다. `factory-a`는 `ai-apps/aws-iot-factory-a-cert` Secret을 사용한다. `factory-b/c`는 후속 IoT 등록 단계에서 `aws-iot-factory-b-cert`, `aws-iot-factory-c-cert`를 생성한다. 운영 단계에서는 External Secrets/SealedSecrets 전환 기준을 별도로 정한다.

## 검증 기준

- adapter/generator가 canonical JSON schema를 만족한다.
- publisher가 IoT Core MQTT publish에 성공한다.
- IoT Core Rule이 S3 raw object를 생성한다.
- S3 raw object prefix가 `raw/{factory_id}/{source_type}/yyyy=.../mm=.../dd=.../` 형식을 따른다.
- S3 raw object body가 publish payload와 일치한다.
- publisher 재시작 후 checkpoint 기준으로 중복과 누락이 제한된다.
- worker2 장애 시 workload가 worker1로 재스케줄된다.
- Hub ArgoCD에서 Sync/Health 상태를 확인할 수 있다.

## M3와의 관계

M3 Issue 6 manifest tag update workflow는 이 데이터 플레인 이미지가 실제 기능을 갖춘 뒤 재개한다.

재개 시 기준 이미지는 smoke `apps/edge-agent`가 아니라 아래 중 하나 이상이다.

```text
factory-a-log-adapter
edge-iot-publisher
dummy-data-generator
```

따라서 현재 우선순위는 M4에서 `factory-a` 실제 데이터 변환과 IoT Core/S3 적재를 통과시키는 것이다.
