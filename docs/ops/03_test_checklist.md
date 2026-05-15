# 테스트 체크리스트

상태: source of truth
기준일: 2026-05-08

## 목적

`factory-a` 운영 시작 시 반복해야 하는 상태 점검과 장애 테스트 기준을 기록한다.

## 시작 시 기본 점검

master에서 실행한다.

```bash
kubectl get nodes -o wide
kubectl -n argocd get application
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

체크:

```text
[ ] master Ready
[ ] worker1 Ready
[ ] worker2 Ready
[ ] safe-edge-monitoring Synced / Healthy
[ ] safe-edge-ai-apps Synced / Healthy
[ ] monitoring pod Running
[ ] ai-apps target pod 3개 worker2 Running
[ ] image prepull DaemonSet worker1/worker2 Running
[ ] Longhorn volumes healthy
[ ] InfluxDB retention 1d
[ ] Grafana dashboard 갱신
[ ] failback cron이 worker2 대상 Pod 존재로 skip
```

## InfluxDB 최신 데이터 확인

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM environment_data ORDER BY time DESC LIMIT 3'

kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM ai_detection ORDER BY time DESC LIMIT 3'

kubectl -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db -execute 'SELECT * FROM acoustic_detection ORDER BY time DESC LIMIT 3'
```

## 장애 테스트 공통 원칙

- 사용자가 물리 장애를 시작한다고 말하기 전까지 장애 테스트를 시작하지 않는다.
- 장애 발생 직후 첫 5분은 판정 보류 구간으로 둔다.
- worker2가 일시적으로 Ready처럼 보여도 5분 전에는 failback 성공으로 보지 않는다.
- 최종 성공은 대상 Pod 3개가 worker2에서 Running일 때만 인정한다.
- 테스트 후 InfluxDB 10초 bucket과 1초 bucket을 모두 확인한다.
- 차후 반복 검증에서는 `start_test` 기반 절차를 Ansible playbook으로 표준화한다.
- 물리 장애 유발은 초기 자동화 범위에서 제외하고, Ansible은 baseline 수집, 테스트 실행, 관측, 로그 수집, 결과 파일화를 우선 담당한다.

대상 Pod:

```text
bme280-sensor
safe-edge-integrated-ai
safe-edge-audio
```

## Ansible 테스트 자동화 체크

상세 계획은 `docs/ops/11_ansible_test_automation.md`를 기준으로 한다.

초기 목표:

```text
start_test 절차를 사람이 매번 손으로 재구성하지 않고,
동일한 baseline 수집 -> 테스트 실행 -> 관측 -> 결과 수집 순서로 반복 가능하게 만든다.
```

자동화 범위:

```text
[x] Ansible inventory에 master, worker1, worker2 정의
[x] master 기준 kubectl 실행 가능 여부 확인
[x] 테스트 결과 저장 디렉터리 생성
[x] 테스트 시작 전 node/pod/pvc/application 상태 수집
[x] master wlan0 IPv4/default route와 Tailscale control plane DNS/HTTPS 확인
[x] master Tailscale daemon/self/IP 확인
[ ] InfluxDB 최신 timestamp 수집
[x] start_test 실행 또는 동등한 테스트 시작 명령 표준화
[ ] 테스트 중 10초 간격 node/pod 상태 수집
[x] failback cron log 또는 관련 system log 수집
[ ] 테스트 종료 후 InfluxDB 10초 bucket query 실행
[ ] 테스트 종료 후 InfluxDB 1초 bucket query 실행
[x] Longhorn volume 상태 수집
[ ] Grafana 확인용 시간창 기록
[x] start_test 결과 파일을 Markdown evidence로 저장
[ ] 장애 테스트 결과 파일을 evidence pack으로 묶기
```

현재 구현:

```text
scripts/ansible/playbooks/start_test.yml
```

새 세션의 시작 점검은 이 playbook을 먼저 실행하고, 생성된 `scripts/ansible/evidence/` Markdown 결과를 기준으로 확인한다. control host가 `10.10.10.0/24` 내부망에 붙어 있으면 기본 inventory의 master `10.10.10.10`으로 실행하고, master Tailscale IP는 SSH 실행 경로로 사용하지 않는다.

초기에는 수동으로 남길 항목:

```text
[ ] worker2 LAN 물리 제거
[ ] worker2 LAN 재연결
[ ] worker2 전원 물리 제거
[ ] worker2 전원 재연결
[ ] 최종 성공/실패 해석
```

차후 확장 후보:

```text
[ ] 네트워크 인터페이스 down/up 자동화
[ ] 스마트 플러그 또는 PDU 기반 전원 차단 자동화
[ ] 1초 bucket 최대 공백 자동 산출
[ ] 중복 write 후보 자동 표시
[ ] Markdown/CSV 테스트 리포트 자동 생성
```

## LAN 제거 테스트 기준

절차:

```text
1. 시작 전 상태와 InfluxDB 최신 timestamp 기록
2. worker2 LAN 제거
3. 10초 간격으로 node/pod/failback log 확인
4. 첫 5분 판정 보류
5. worker1 failover 완료 시각 기록
6. LAN 재연결
7. worker2 Ready 및 대상 Pod 3개 worker2 Running 확인
8. InfluxDB 10초/1초 bucket 분석
```

검증 완료 결과:

```text
Failover: 성공
Failback: 성공
10초 bucket 기준 실제 전환 구간 공백 없음
전환 구간 중복 write 후보 있음
```

## 전원 제거 테스트 기준

절차:

```text
1. 시작 전 상태와 InfluxDB 최신 timestamp 기록
2. worker2 전원 제거
3. 10초 간격으로 node/pod/failback log 확인
4. 첫 5분 판정 보류
5. worker1 failover 완료 시각 기록
6. worker2 전원 재연결
7. worker2 Ready 및 대상 Pod 3개 worker2 Running 확인
8. Longhorn degraded -> healthy 복귀 확인
9. InfluxDB 10초/1초 bucket 분석
```

검증 완료 결과:

```text
Failover: 성공
Failback: 성공
전원 제거 첫 관찰 -> worker2 NotReady: 약 42초
worker2 NotReady -> worker1 전체 Running: 약 32초
전원 제거 첫 관찰 -> worker1 전체 Running: 약 74초
전원 재연결 첫 관찰 -> worker2 Ready: 약 21초
worker2 Ready -> worker2 전체 Running: 약 1분 50초
전원 재연결 첫 관찰 -> worker2 전체 Running: 약 2분 11초
Longhorn degraded 발생 후 healthy 복귀
```

1초 bucket 연속 공백:

```text
failover environment_data 최대 65초
failover ai_detection 최대 72초
failover acoustic_detection 최대 75초
failback environment_data 최대 2초
failback ai_detection 최대 2초
failback acoustic_detection 최대 2초
```

## 남은 판단 항목

```text
[ ] 전원 장애 시 허용 가능한 데이터 공백 기준 결정
[ ] failback 전환 구간 중복 write 허용 여부 결정
[ ] active writer guard 또는 writer node tag 필요성 검토
[ ] Grafana에서 장애 시간대 공백/스파이크 시각 확인
```

## Edge data-plane 배포 후 추가 검증

Edge data-plane은 아직 현재 운영 workload가 아니다. 배포 후에는 `docs/planning/06_edge_agent_deployment_plan.md`의 기준을 따라 아래 항목을 추가로 확인한다.

```text
[ ] factory-a-log-adapter Pod가 ai-apps namespace에서 Running
[ ] edge-iot-publisher Pod가 ai-apps namespace에서 Running
[ ] data-plane workload가 worker2에 우선 배치됨
[ ] resource request 50m / 128Mi, limit 200m / 256Mi 반영
[ ] AWS IoT Core MQTT test client에서 aegis/factory-a/factory_state 수신
[ ] AWS IoT Core MQTT test client에서 aegis/factory-a/infra_state 수신
[ ] payload에 message_id, factory_id, node_id, source_type, source_timestamp, published_at 포함
[ ] edge-iot-publisher 재시작 후 checkpoint 기준으로 중복 송신이 제한됨
[ ] AWS IoT Core 연결 단절 후 backoff 재연결 확인
[ ] ServiceAccount/RBAC가 최소 읽기 권한으로 제한됨
[ ] AWS IoT 인증서 private key가 Git repo에 포함되지 않음
[ ] worker2 장애 시 data-plane workload가 worker1로 재스케줄
[ ] 재스케줄 후 infra_state 또는 pipeline 관련 상태 송신 유지
[ ] 평상시 메모리 150Mi 이하
[ ] 피크 메모리 200Mi 이하
```
