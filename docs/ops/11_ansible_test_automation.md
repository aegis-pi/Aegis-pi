# Ansible 테스트 자동화 계획

상태: draft
기준일: 2026-05-08

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
master

[factory_a_workers]
worker1
worker2

[factory_a:children]
factory_a_master
factory_a_workers
```

IP, LoadBalancer 주소, SSH 사용자, 워크로드 노드명은 inventory에 직접 쓰지 않고 아래 변수 파일에서 관리한다.

```text
scripts/ansible/inventory/group_vars/factory_a.yml
```

예:

```yaml
factory_a_nodes:
  master:
    ip: 10.10.10.10
  worker1:
    ip: 10.10.10.11
  worker2:
    ip: 10.10.10.12

factory_a_ssh_hosts:
  master: "{{ factory_a_master_ssh_host }}"
  worker1: "{{ factory_a_worker1_ssh_host }}"
  worker2: "{{ factory_a_worker2_ssh_host }}"

ansible_host: "{{ factory_a_ssh_hosts[inventory_hostname] | default(factory_a_nodes[inventory_hostname].ip) }}"
```

2026-05-08 기준 control host는 `10.10.10.100`으로 고정되어 있고, `start_test.yml`은 기본 inventory의 master `10.10.10.10`으로 SSH 접속한다. 이 접속은 `eth0` 내부망 경로이며, playbook 내부에서 master의 `wlan0` 인터넷 경로와 Tailscale 상태를 별도로 검증한다.

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
    start_test.yml
    03_observe_failover.yml
    04_collect_influxdb_buckets.yml
    05_collect_logs.yml
    06_build_evidence_pack.yml
```

현재 저장소에는 `start_test.yml`까지 구현해 두었다. 이후 장애 관측과 InfluxDB bucket 분석 playbook은 이 구조를 확장한다.

## 현재 구현된 start_test 자동화

구현 위치:

```text
scripts/ansible/
  ansible.cfg
  README.md
  inventory/
    factory-a.ini
    group_vars/factory_a.yml
  playbooks/
    start_test.yml
  evidence/.gitignore
```

실행 기준:

```bash
cd scripts/ansible
ansible-playbook -i inventory/factory-a.ini playbooks/start_test.yml
```

비밀번호 SSH를 사용하는 경우 control host에 `sshpass`가 필요하다.

```bash
sudo apt-get install -y sshpass
```

현재 `start_test.yml`은 `master`에만 SSH 접속하고, worker 상태는 `master`의 `kubectl` 결과로 확인한다. 따라서 start_test 실행 시에는 `master SSH/sudo password` 프롬프트 하나만 입력한다.

Tailscale 검증은 실행 경로와 분리한다. master Tailscale IP `100.117.40.125`를 SSH transport로 사용하면 Tailscale 장애를 제대로 검증할 수 없으므로 playbook이 preflight에서 실패시킨다.

실행 경로 기준:

```text
권장: control host 10.10.10.100 -> master 10.10.10.10 over eth0/internal route
대안: factory_a_master_ssh_host=<master-wlan-ip>
금지: factory_a_master_ssh_host=100.117.40.125
```

`master-wlan-ip`는 DHCP로 바뀔 수 있으므로 AP/router reservation을 잡거나 실행 직전에 현재 IP를 확인한다.

node별 비밀번호 변수는 아래처럼 `inventory/group_vars/factory_a.yml`에서 매핑한다.

```yaml
factory_a_nodes:
  master:
    password_var: factory_a_master_password
  worker1:
    password_var: factory_a_worker1_password
  worker2:
    password_var: factory_a_worker2_password
```

worker에 직접 SSH 접속하는 playbook을 추가할 때는 해당 playbook의 `vars_prompt`에 `factory_a_worker1_password`, `factory_a_worker2_password`를 추가한다. 비밀번호는 prompt로만 받고 파일에 저장하지 않는다.

현재 playbook은 아래를 수행한다.

```text
1. master에서 start_test 명령 실행
2. 노드 Ready/IP, ServiceLB 비활성, MetalLB pool, LoadBalancer IP 검증
3. Longhorn UI/volume 상태 검증
4. master taint, Argo CD Application, monitoring/ai-apps Pod 배치 검증
5. failback cron skip 로그 검증
6. master `wlan0` IPv4/default route와 Tailscale control plane DNS/HTTPS reachability 검증
7. master Tailscale daemon/self hostname/IP 검증
8. scripts/ansible/evidence/ 아래 Markdown evidence 생성
```

앞으로 새 세션의 `start_test`는 먼저 이 Ansible playbook으로 실행하고, evidence 결과를 기준으로 판정한다. 수동 kubectl 실행은 playbook 실패 원인 조사나 추가 분석이 필요할 때만 사용한다.

민감 정보 정책:

```text
SSH 비밀번호, sudo 비밀번호, K3s token, GitHub token, AWS credential은 inventory, 변수 파일, evidence, 문서에 기록하지 않는다.
scripts/ansible/evidence/의 실행 산출물은 로컬 보관용이며 Git push 대상에서 제외한다.
```

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

후속 장애 관측 playbook은 아래 정보를 추가로 기록한다. 현재 구현된 `start_test.yml`은 시작 상태 점검과 master `wlan0`/Tailscale preflight 결과를 evidence Markdown으로 남긴다.

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
