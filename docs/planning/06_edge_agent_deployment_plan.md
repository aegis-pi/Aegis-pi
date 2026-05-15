# Edge Data-Plane 배포 계획

상태: draft
기준일: 2026-05-15

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
  dummy-data-generator
    -> local spool/outbox
    -> edge-iot-publisher
    -> AWS IoT Core
```

## 컴포넌트

| 컴포넌트 | 배포 위치 | 역할 |
| --- | --- | --- |
| `factory-a-log-adapter` | `factory-a` K3s | 실제 Safe-Edge raw/log/status 데이터를 canonical JSON으로 변환 |
| `dummy-data-generator` | `factory-b/c` K3s | canonical JSON 형식의 가데이터 생성 |
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
  -> factory-a/b/c K3s workload 배포와 drift 관리
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

## M5 확장 순서

`factory-b/c`는 실제 센서가 없으므로 `dummy-data-generator`가 canonical JSON을 만든다. IoT Core 송신은 `factory-a`와 같은 `edge-iot-publisher`를 사용한다.

```text
factory-b/c K3s
  dummy-data-generator
  edge-iot-publisher
```

이 구조를 통해 테스트베드 공장도 실제 데이터 플레인과 같은 IoT Core/S3/Lambda/Dashboard 경로를 탄다.

## Placement 기준

`factory-a`에서는 기존 Safe-Edge workload 배치 기준을 따른다.

- `worker2` preferred
- `worker1` failover
- `master` avoid
- 1 replica부터 시작
- local spool/outbox가 중복 publish를 제어할 때까지 보수적 update 전략 사용

초기에는 두 sender가 동시에 같은 outbox를 처리하지 않도록 `edge-iot-publisher`를 1 replica로 둔다. checkpoint/idempotency 검증 후 RollingUpdate 확장을 검토한다.

## Secret 기준

IoT Core 인증서와 private key는 K3s Secret으로 주입한다.

```text
namespace: ai-apps
secret: aws-iot-factory-a-cert
mount path: /etc/aegis/iot
```

Secret 값은 Git에 저장하지 않는다. 생성과 주입 절차는 `docs/ops/12_iot_core_thing_secret_mount.md`를 따른다.

M4에서 data-plane workload namespace를 `aegis-spoke-system`으로 확정하면 동일 인증서를 해당 namespace Secret으로 재주입하거나 External Secrets/SealedSecrets 전환 기준을 별도로 정한다.

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
