# Ansible 테스트 자동화 계획

상태: draft
기준일: 2026-04-29

## 목적

`factory-a` Safe-Edge의 `start_test` 기반 검증 절차를 Ansible playbook으로 표준화한다.

목표는 장애 테스트를 완전히 무인화하는 것이 아니라, 반복 가능한 테스트 준비, 실행, 관측, 로그 수집, 결과 파일화를 먼저 자동화하는 것이다.

## 배경

현재 M0에서는 LAN 제거와 전원 제거 기반 failover/failback 테스트를 수동으로 수행했다.

후속 M7 통합 검증에서는 같은 유형의 테스트를 반복해야 하므로, 사람이 매번 명령을 재구성하면 아래 문제가 생긴다.

- 테스트 전 baseline 누락
- 관측 간격 불일치
- InfluxDB query 시간창 오류
- failover/failback 시각 기록 누락
- 결과 파일과 해석 근거 분산

Ansible은 이 절차를 표준화하는 테스트 오케스트레이터로 사용한다.

## 기본 원칙

초기 자동화는 안전한 범위부터 시작한다.

```text
자동화 우선:
  baseline 수집
  start_test 실행
  kubectl 상태 관측
  InfluxDB query 실행
  Longhorn 상태 수집
  로그 수집
  evidence pack 생성

수동 유지:
  LAN 물리 제거/재연결
  전원 물리 제거/재연결
  최종 성공/실패 해석
```

물리 장애 유발은 권한, 하드웨어, 안전 문제가 있으므로 초기 playbook에 넣지 않는다.

## 대상 노드

Ansible inventory는 `factory-a` 기준으로 시작한다.

```ini
[factory_a_master]
master ansible_host=10.10.10.10

[factory_a_workers]
worker1 ansible_host=10.10.10.11
worker2 ansible_host=10.10.10.12

[factory_a:children]
factory_a_master
factory_a_workers
```

명령 실행 기준:

| 대상 | 역할 |
| --- | --- |
| `master` | `kubectl`, InfluxDB query, failback cron log 수집 |
| `worker1` | failover 대상 상태 확인 |
| `worker2` | 장애 대상 및 복구 대상 상태 확인 |

## Playbook 구성 후보

```text
scripts/ansible/
  inventory/factory-a.ini
  playbooks/
    00_preflight.yml
    01_collect_baseline.yml
    02_start_test.yml
    03_observe_failover.yml
    04_collect_influxdb_buckets.yml
    05_collect_logs.yml
    06_build_evidence_pack.yml
```

현재 저장소에는 아직 실제 Ansible 파일을 두지 않는다. 이 문서는 후속 구현 기준이다.

## 00 Preflight

목적:

```text
테스트를 시작해도 되는 상태인지 확인한다.
```

확인 항목:

```text
[ ] master SSH 접근 가능
[ ] worker1 SSH 접근 가능
[ ] worker2 SSH 접근 가능
[ ] master에서 kubectl 실행 가능
[ ] kubeconfig context 확인
[ ] `kubectl get nodes` 성공
[ ] `argocd` namespace 접근 가능
[ ] `monitoring` namespace 접근 가능
[ ] `ai-apps` namespace 접근 가능
```

실패 시 테스트를 중단한다.

## 01 Baseline 수집

목적:

```text
장애 전 정상 상태를 evidence로 남긴다.
```

수집 명령:

```bash
kubectl get nodes -o wide
kubectl -n argocd get application -o wide
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

InfluxDB 최신 데이터:

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM environment_data ORDER BY time DESC LIMIT 3'

kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM ai_detection ORDER BY time DESC LIMIT 3'

kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM acoustic_detection ORDER BY time DESC LIMIT 3'
```

## 02 start_test 실행

목적:

```text
기존 start_test 절차 또는 동등한 테스트 시작 명령을 표준화한다.
```

playbook은 아래 정보를 기록한다.

```text
test_id
test_type: lan_disconnect 또는 power_disconnect
start_time_kst
operator
target_node: worker2
target_pods:
  - bme280-sensor
  - safe-edge-integrated-ai
  - safe-edge-audio
```

초기에는 장애 유발 전 아래 메시지를 출력하고 대기한다.

```text
worker2 LAN 제거 또는 전원 제거를 수동으로 수행한 뒤 계속 진행한다.
```

## 03 Failover / Failback 관측

목적:

```text
장애 발생 후 node/pod 전환 상태를 일정 간격으로 남긴다.
```

기본 관측 간격:

```text
10초
```

수집 명령:

```bash
kubectl get nodes -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n monitoring get pod -o wide
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

관측해야 하는 시각:

```text
장애 첫 관찰 시각
worker2 NotReady 시각
worker1 대상 Pod 전체 Running 시각
복구 시작 시각
worker2 Ready 시각
worker2 대상 Pod 전체 Running 시각
Longhorn healthy 복귀 시각
```

초기 5분은 판정 보류 구간으로 기록한다.

## 04 InfluxDB bucket 분석

목적:

```text
장애 전환 구간의 데이터 공백과 중복 write 후보를 확인한다.
```

10초 bucket:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(10s) fill(0)
```

1초 bucket:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(1s) fill(0)
```

동일 방식으로 아래 measurement도 확인한다.

```text
ai_detection.fire_detected
acoustic_detection.is_danger
```

초기 자동화에서는 query 결과 파일만 남긴다.

차후 확장에서는 아래 값을 자동 산출한다.

```text
max_empty_bucket_seconds
duplicate_write_candidate_count
first_data_after_failover
first_data_after_failback
```

## 05 로그 수집

목적:

```text
장애 전후 원인 분석에 필요한 로그를 한 위치에 모은다.
```

수집 후보:

```bash
kubectl -n ai-apps logs deploy/bme280-sensor --tail=300
kubectl -n ai-apps logs deploy/safe-edge-integrated-ai --tail=300
kubectl -n ai-apps logs deploy/safe-edge-audio --tail=300
journalctl --since '<START>' --until '<END>'
```

failback이 master OS cron에서 동작하므로 master의 cron/system log도 수집한다.

## 06 Evidence Pack

목적:

```text
테스트 결과를 한 디렉터리 단위로 보관한다.
```

디렉터리 구조 후보:

```text
test-results/
  2026-04-29_lan_disconnect_worker2/
    metadata.yaml
    baseline/
    observation/
    influxdb/
    logs/
    summary.md
```

`metadata.yaml` 후보:

```yaml
test_id: 2026-04-29_lan_disconnect_worker2
test_type: lan_disconnect
target_node: worker2
start_time_kst: "2026-04-29T13:00:00+09:00"
end_time_kst: "2026-04-29T13:20:00+09:00"
operator: "manual"
automation: "ansible"
physical_fault_trigger: "manual"
```

`summary.md` 후보:

```text
# Test Summary

## Timeline

## Baseline

## Failover Result

## Failback Result

## InfluxDB Bucket Result

## Longhorn Result

## Open Questions
```

## 성공 기준

Ansible 자동화의 1차 성공 기준은 아래와 같다.

```text
[ ] 동일 playbook으로 같은 순서의 테스트 자료를 반복 수집할 수 있다.
[ ] 테스트 시작 전 baseline이 누락되지 않는다.
[ ] 10초 간격 관측 로그가 파일로 남는다.
[ ] InfluxDB 10초/1초 bucket query 결과가 파일로 남는다.
[ ] Longhorn degraded/healthy 상태 변화가 파일로 남는다.
[ ] 테스트별 evidence pack 디렉터리가 생성된다.
```

## 후속 확장

초기 자동화가 안정화되면 아래를 검토한다.

```text
[ ] 1초 bucket 최대 공백 자동 계산
[ ] 중복 write 후보 자동 계산
[ ] Grafana annotation 또는 시간창 URL 생성
[ ] Markdown/CSV 리포트 자동 생성
[ ] 네트워크 장애 유발 자동화
[ ] 스마트 플러그 또는 PDU 기반 전원 장애 자동화
[ ] M7 통합 검증 시나리오와 연결
```

## 관련 문서

- `docs/ops/03_test_checklist.md`
- `docs/ops/09_failover_failback_test_results.md`
- `docs/issues/M7_integration-test.md`
