# Factory B/C Dummy Data systemd Runbook

상태: source of truth
기준일: 2026-06-02

## 목적

`factory-b` Mac UTM VM과 `factory-c` Windows VirtualBox VM에서 실제 공장 센서가 있는 것처럼 가데이터를 계속 생성한다. 현재 표준 운영에서는 VM 로컬 generator가 outbox에 JSON을 쓰고, Spoke K3s에 ArgoCD로 배포된 `edge-iot-publisher`가 AWS IoT Core로 전송한다.

구조는 Factory A 최신 data-plane 구현과 같은 경계를 따른다.

```text
dummy generator
  -> 3초마다 factory_state JSON 생성
  -> 20초마다 infra_state JSON 생성
  -> 기본 node 상태는 항상 ready로 고정
  -> node 장애는 명시적 dummy scenario에서만 생성
  -> /var/lib/aegis/outbox/*.json 저장

edge-iot-publisher (K3s)
  -> outbox JSON scan
  -> AWS IoT Core MQTT publish
  -> 성공한 파일 삭제

AWS IoT Rule
  -> S3 raw/{factory_id}/{source_type}/yyyy=.../{message_id}.json
```

## 파일 역할

| 파일 | Factory | 역할 |
| --- | --- | --- |
| `apps/dummy-sensor/factory_b_dummy_generator.py` | factory-b | `stable-lab` canonical JSON 생성 |
| `apps/dummy-sensor/factory_b_iot_publisher.py` | factory-b | legacy/manual smoke publisher. 표준 운영에서는 K3s `edge-iot-publisher` 사용 |
| `apps/dummy-sensor/factory_c_dummy_generator.py` | factory-c | `noisy-vm` canonical JSON 생성 |
| `apps/dummy-sensor/factory_c_iot_publisher.py` | factory-c | legacy/manual smoke publisher. 표준 운영에서는 K3s `edge-iot-publisher` 사용 |

## 전제 조건

각 VM에 아래 파일이 있어야 한다.

```text
/etc/aegis/iot/<factory-id>/endpoint.txt
/etc/aegis/iot/<factory-id>/AmazonRootCA1.pem
/etc/aegis/iot/<factory-id>/certificate.pem.crt
/etc/aegis/iot/<factory-id>/private.pem.key
```

주의:

- private key, certificate 원문은 git이나 문서에 기록하지 않는다.
- Factory B와 Factory C는 서로 다른 IoT Thing/client id를 사용한다.
- 같은 factory 안에서 같은 MQTT client id를 쓰는 프로세스를 동시에 두 개 띄우지 않는다.
- K3s `edge-iot-publisher`가 Running인 현재 표준 운영에서는 VM 로컬 dummy publisher systemd를 설치하거나 활성화하지 않는다.
- SSH user, host/IP, password 같은 접속 정보는 문서에 기록하지 않는다. 운영자는 로컬 보안 저장소나 별도 env 파일에서만 관리한다.

## 실제 실행 위치와 접근 방식

factory-b/c dummy data generator는 **worker VM에서 systemd service로 실행**된다. master VM에서 generator를 실행하면 master-local `/var/lib/aegis/outbox`에만 JSON이 쌓이고, worker node에 떠 있는 K3s `edge-iot-publisher` Pod가 읽는 hostPath와 달라져 S3/DynamoDB 파이프라인으로 전달되지 않는다.

표준 흐름:

```text
worker VM systemd generator
  -> worker-local /var/lib/aegis/outbox/*.json
  -> worker node K3s edge-iot-publisher Pod hostPath mount
  -> AWS IoT Core
  -> S3 raw / processed
  -> DynamoDB LATEST / HISTORY
```

접근은 보통 master VM을 jump host로 사용해 worker VM에 들어간다. 실제 user, host/IP, password는 문서에 남기지 않고 운영자 로컬 설정으로만 주입한다.

권장 관리 명령:

```bash
# repo root 기준. scripts/ops/dummy-generators.env 또는
# AEGIS_DUMMY_GENERATORS_ENV가 가리키는 로컬 env 파일에서 접속 대상을 읽는다.
scripts/ops/manage-dummy-generators.sh status factory-b
scripts/ops/manage-dummy-generators.sh status factory-c

scripts/ops/manage-dummy-generators.sh start factory-b
scripts/ops/manage-dummy-generators.sh stop factory-b
```

수동 접근이 필요할 때는 같은 구조를 직접 사용한다.

```bash
ssh -J <ssh-user>@<master-host> <ssh-user>@<worker-host>
```

worker VM 안에서 확인할 항목:

```bash
systemctl status aegis-factory-b-dummy-generator.service --no-pager
systemctl cat aegis-factory-b-dummy-generator.service
cat /etc/aegis/factory-b-dummy.env
ls -lt /var/lib/aegis/outbox | head
journalctl -u aegis-factory-b-dummy-generator.service -n 50 --no-pager
```

factory-c에서는 service와 env 파일 이름만 `factory-c`로 바꾼다.

정상 기준:

- service `ExecStart`가 `/usr/bin/python3 /opt/aegis/dummy-sensor/factory_*_dummy_generator.py --loop`다.
- `EnvironmentFile`은 `/etc/aegis/factory-*-dummy.env`다.
- `AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox`다.
- worker-local outbox에 `factory_state`가 약 3초마다 생성된다.
- worker-local outbox에 `infra_state`가 약 20초마다 생성된다.
- K3s `edge-iot-publisher`가 같은 worker-local outbox hostPath를 읽어 publish한다.
- master VM의 generator service는 표준 운영에서 중지 상태여야 한다.

## Factory B와 C 차이

두 factory는 같은 envelope와 publish 경로를 쓰지만 profile과 topology가 다르다. `factory_state`는 가데이터이고, `infra_state`는 기본적으로 실제 K3s 상태를 읽는다.

| 항목 | Factory B | Factory C |
| --- | --- | --- |
| 실행 위치 | Mac UTM `factory-b` worker1 VM | Windows VirtualBox `factory-c-worker` VM |
| Factory ID | `factory-b` | `factory-c` |
| environment_type | `vm-mac` | `vm-windows` |
| IoT client id | `AEGIS-IoTThing-factory-b` | `AEGIS-IoTThing-factory-c` |
| MQTT topic | `aegis/factory-b/factory_state`, `aegis/factory-b/infra_state` | `aegis/factory-c/factory_state`, `aegis/factory-c/infra_state` |
| S3 raw prefix | `raw/factory-b/...` | `raw/factory-c/...` |
| profile | `stable-lab` | `noisy-vm` |
| topology | master + worker | master + worker |
| nodes 배열 | `["master", "worker1"]` | `["factory-c-master", "factory-c-worker"]` |
| factory_state node_id | `worker1` | `factory-c-worker` |
| temperature baseline/jitter | `24.5 ± 3.0` | `27.0 ± 4.0` |
| humidity baseline/jitter | `45.0 ± 8.0` | `52.0 ± 10.0` |
| pressure baseline/jitter | `1013.5 ± 1.5` | `1012.0 ± 2.0` |
| sensor event interval | `6~10분` | `4~7분` |
| sensor event hold | `30초` | `30초` |
| AI event interval | `25~30분` | `25~30분` |
| AI event type | `ai_warning` | `ai_warning`, `ai_critical` |
| AI score selection | fire/fall/bend 중 1~2개, `0.5~0.8` | warning은 fire/fall/bend 중 1~3개, `0.5~0.8`; critical은 1~3개, `0.8~1.0` |
| abnormal_sound label | `brief lab impact` | `intermittent vibration` |
| sequence file | `/var/lib/aegis/factory-b-publish-sequence` | `/var/lib/aegis/factory-c-publish-sequence` |
| infra_state 기본 모드 | synthetic fixed-ready | synthetic fixed-ready |

이 차이 때문에 Dashboard나 S3 raw에서 두 testbed가 같은 데이터를 반복 송신하는 것처럼 보이지 않는다.

AI event는 화재, 넘어짐, 굽힘, 이상소음을 각각 독립 스케줄로 발생시키지 않는다. `ai_warning` 또는 `ai_critical`이 due일 때 `fire_score`, `fall_score`, `bend_score` 중 일부를 랜덤으로 올리고, `abnormal_sound` 라벨도 같은 `factory_state` 1건에 함께 넣는다. Sensor spike와 달리 AI event에는 hold window가 없다.

Sensor event별 재발 주기와 sensor 외 AI/infra/pipeline gap event 기본 주기는 `docs/ops/27_dummy_data_generation_and_risk_scenarios.md`의 `Sensor event 세부 주기`와 `infra_state 생성 로직`을 기준으로 한다. worker env 파일에서 event interval을 override하지 않으면 factory-b는 sensor event가 `6~10분`마다 1개, factory-c는 `4~7분`마다 1개 round-robin으로 발생한다.

## infra_state node 상태 기준

기본 운영에서는 node down을 랜덤으로 만들지 않는다. `AEGIS_CLUSTER_STATE_MODE=synthetic` 기준으로 master/worker 두 node는 항상 `ready=true`이고, 그래프 검증 중 임의의 node down spike가 생기지 않도록 한다.

node down을 테스트할 때만 명시적으로 scenario를 켠다.

```bash
sudo sed -i 's/^AEGIS_DUMMY_SCENARIO=.*/AEGIS_DUMMY_SCENARIO=node_down/' /etc/aegis/factory-b-dummy.env
echo 'AEGIS_DUMMY_SCENARIO_DOWN_NODES=worker1' | sudo tee -a /etc/aegis/factory-b-dummy.env
sudo systemctl restart aegis-factory-b-dummy-generator.service
```

Factory C:

```bash
sudo sed -i 's/^AEGIS_DUMMY_SCENARIO=.*/AEGIS_DUMMY_SCENARIO=node_down/' /etc/aegis/factory-c-dummy.env
echo 'AEGIS_DUMMY_SCENARIO_DOWN_NODES=factory-c-worker' | sudo tee -a /etc/aegis/factory-c-dummy.env
sudo systemctl restart aegis-factory-c-dummy-generator.service
```

정상 모드로 되돌릴 때:

```bash
sudo sed -i 's/^AEGIS_DUMMY_SCENARIO=.*/AEGIS_DUMMY_SCENARIO=normal/' /etc/aegis/factory-b-dummy.env
sudo sed -i '/^AEGIS_DUMMY_SCENARIO_DOWN_NODES=/d' /etc/aegis/factory-b-dummy.env
sudo systemctl restart aegis-factory-b-dummy-generator.service

sudo sed -i 's/^AEGIS_DUMMY_SCENARIO=.*/AEGIS_DUMMY_SCENARIO=normal/' /etc/aegis/factory-c-dummy.env
sudo sed -i '/^AEGIS_DUMMY_SCENARIO_DOWN_NODES=/d' /etc/aegis/factory-c-dummy.env
sudo systemctl restart aegis-factory-c-dummy-generator.service
```

`AEGIS_CLUSTER_STATE_MODE=kubernetes`를 쓰면 workload 상태만 Kubernetes에서 읽고, node ready는 그래프 안정성을 위해 fixed-ready synthetic node를 유지한다.

## outbox cleanup cron

outbox backlog가 오래 남아 그래프/집계 해석을 흐리지 않도록 Linux cron으로 오래된 `.json` 파일을 정리한다. Kubernetes CronJob이 아니다.

기본 정책:

- 위치: `/etc/cron.d/aegis-outbox-cleanup`
- 주기: `0 3 */3 * *`
- 대상: `/var/lib/aegis/outbox/*.json`
- 보호: 최근 24시간 파일은 삭제하지 않음
- 제외: `tmp/` 디렉터리는 삭제하지 않음
- 로그: `/var/log/aegis-outbox-cleanup.log`

설치 파일:

```text
/opt/aegis/bin/aegis-outbox-cleanup.sh
/etc/cron.d/aegis-outbox-cleanup
```

## 공통 배치 순서

Computer 1에서 대상 VM으로 파일을 복사한다.

Factory B:

```bash
scp apps/dummy-sensor/factory_b_dummy_generator.py \
    apps/dummy-sensor/factory_b_iot_publisher.py \
    apps/dummy-sensor/k8s_state.py \
    <vm-ssh-user>@<factory-b-ip>:/tmp/
```

Factory C:

```bash
scp apps/dummy-sensor/factory_c_dummy_generator.py \
    apps/dummy-sensor/factory_c_iot_publisher.py \
    apps/dummy-sensor/k8s_state.py \
    <vm-ssh-user>@${TS_IP_WORKER}:/tmp/
```

## Factory B 설치

실행 위치: **factory-b VM**

```bash
sudo mkdir -p /opt/aegis/dummy-sensor /etc/aegis /var/lib/aegis/outbox
sudo cp /tmp/factory_b_dummy_generator.py /tmp/factory_b_iot_publisher.py /tmp/k8s_state.py /opt/aegis/dummy-sensor/
sudo chmod 755 /opt/aegis/dummy-sensor/*.py

K3S_VER="$(/usr/local/bin/k3s --version | awk '/k3s version/ {print $3}')"

sudo tee /etc/aegis/factory-b-dummy.env >/dev/null <<EOF
AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox
AEGIS_IOT_DIR=/etc/aegis/iot/factory-b
AEGIS_IOT_CLIENT_ID=AEGIS-IoTThing-factory-b
AEGIS_K3S_VERSION=${K3S_VER}
AEGIS_CLUSTER_STATE_MODE=synthetic
AEGIS_DUMMY_SCENARIO=normal
EOF

sudo chmod 600 /etc/aegis/factory-b-dummy.env
```

## Factory C 설치

실행 위치: **factory-c-worker VM**

```bash
sudo mkdir -p /opt/aegis/dummy-sensor /etc/aegis /var/lib/aegis/outbox
sudo cp /tmp/factory_c_dummy_generator.py /tmp/factory_c_iot_publisher.py /tmp/k8s_state.py /opt/aegis/dummy-sensor/
sudo chmod 755 /opt/aegis/dummy-sensor/*.py

K3S_VER="$(/usr/local/bin/k3s --version | awk '/k3s version/ {print $3}')"

sudo tee /etc/aegis/factory-c-dummy.env >/dev/null <<EOF
AEGIS_OUTBOX_DIR=/var/lib/aegis/outbox
AEGIS_IOT_DIR=/etc/aegis/iot/factory-c
AEGIS_IOT_CLIENT_ID=AEGIS-IoTThing-factory-c
AEGIS_K3S_VERSION=${K3S_VER}
AEGIS_CLUSTER_STATE_MODE=synthetic
AEGIS_DUMMY_SCENARIO=normal
EOF

sudo chmod 600 /etc/aegis/factory-c-dummy.env
```

## 1회 동작 확인

Factory B:

```bash
/usr/bin/python3 /opt/aegis/dummy-sensor/factory_b_dummy_generator.py --once all --no-write --pretty

sudo env $(cat /etc/aegis/factory-b-dummy.env | xargs) \
  /usr/bin/python3 /opt/aegis/dummy-sensor/factory_b_dummy_generator.py --once all

sudo env $(cat /etc/aegis/factory-b-dummy.env | xargs) \
  /usr/bin/python3 /opt/aegis/dummy-sensor/factory_b_iot_publisher.py --once
```

Factory C:

```bash
/usr/bin/python3 /opt/aegis/dummy-sensor/factory_c_dummy_generator.py --once all --no-write --pretty

sudo env $(cat /etc/aegis/factory-c-dummy.env | xargs) \
  /usr/bin/python3 /opt/aegis/dummy-sensor/factory_c_dummy_generator.py --once all

sudo env $(cat /etc/aegis/factory-c-dummy.env | xargs) \
  /usr/bin/python3 /opt/aegis/dummy-sensor/factory_c_iot_publisher.py --once
```

정상 기준:

```text
published /var/lib/aegis/outbox/...factory_state...json -> aegis/<factory-id>/factory_state
published /var/lib/aegis/outbox/...infra_state...json -> aegis/<factory-id>/infra_state
```

`infra_state`가 실제 K3s를 읽는지 확인:

```bash
sudo env $(cat /etc/aegis/factory-b-dummy.env | xargs) \
  /usr/bin/python3 /opt/aegis/dummy-sensor/factory_b_dummy_generator.py --once infra_state --no-write --pretty \
  | jq '.payload.heartbeat.cluster_state_source, .payload.nodes, .payload.workloads'

sudo env $(cat /etc/aegis/factory-c-dummy.env | xargs) \
  /usr/bin/python3 /opt/aegis/dummy-sensor/factory_c_dummy_generator.py --once infra_state --no-write --pretty \
  | jq '.payload.heartbeat.cluster_state_source, .payload.nodes, .payload.workloads'
```

정상 기준은 `"kubernetes"`다. `"synthetic"`이면 `kubectl get nodes -o json`이 해당 VM에서 성공하는지 먼저 확인한다.

## systemd 등록

### Factory B

```bash
sudo tee /etc/systemd/system/aegis-factory-b-dummy-generator.service >/dev/null <<'UNIT'
[Unit]
Description=Aegis factory-b dummy data generator
Wants=network-online.target
After=network-online.target k3s.service

[Service]
Type=simple
EnvironmentFile=/etc/aegis/factory-b-dummy.env
ExecStart=/usr/bin/python3 /opt/aegis/dummy-sensor/factory_b_dummy_generator.py --loop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/aegis-factory-b-dummy-publisher.service >/dev/null <<'UNIT'
[Unit]
Description=Aegis factory-b dummy IoT publisher
Wants=network-online.target
After=network-online.target tailscaled.service k3s.service aegis-factory-b-dummy-generator.service

[Service]
Type=simple
EnvironmentFile=/etc/aegis/factory-b-dummy.env
ExecStart=/usr/bin/python3 /opt/aegis/dummy-sensor/factory_b_iot_publisher.py --loop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now aegis-factory-b-dummy-generator.service
sudo systemctl enable --now aegis-factory-b-dummy-publisher.service
```

### Factory C

```bash
sudo tee /etc/systemd/system/aegis-factory-c-dummy-generator.service >/dev/null <<'UNIT'
[Unit]
Description=Aegis factory-c dummy data generator
Wants=network-online.target
After=network-online.target k3s-agent.service

[Service]
Type=simple
EnvironmentFile=/etc/aegis/factory-c-dummy.env
ExecStart=/usr/bin/python3 /opt/aegis/dummy-sensor/factory_c_dummy_generator.py --loop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/systemd/system/aegis-factory-c-dummy-publisher.service >/dev/null <<'UNIT'
[Unit]
Description=Aegis factory-c dummy IoT publisher
Wants=network-online.target
After=network-online.target tailscaled.service k3s-agent.service aegis-factory-c-dummy-generator.service

[Service]
Type=simple
EnvironmentFile=/etc/aegis/factory-c-dummy.env
ExecStart=/usr/bin/python3 /opt/aegis/dummy-sensor/factory_c_iot_publisher.py --loop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now aegis-factory-c-dummy-generator.service
sudo systemctl enable --now aegis-factory-c-dummy-publisher.service
```

## 상태 확인

Factory B:

```bash
systemctl is-active aegis-factory-b-dummy-generator
systemctl is-active aegis-factory-b-dummy-publisher
sudo journalctl -u aegis-factory-b-dummy-publisher -n 30 --no-pager
cat /var/lib/aegis/factory-b-publish-sequence
```

Factory C:

```bash
systemctl is-active aegis-factory-c-dummy-generator
systemctl is-active aegis-factory-c-dummy-publisher
sudo journalctl -u aegis-factory-c-dummy-publisher -n 30 --no-pager
cat /var/lib/aegis/factory-c-publish-sequence
```

정상 기준:

```text
generator: active
publisher: active
publisher journal: published ... -> aegis/<factory-id>/...
sequence file: 20초마다 증가
```

## S3 확인

Computer 1에서 확인한다.

Factory B:

```bash
aws s3 ls s3://aegis-bucket-data/raw/factory-b/factory_state/ --recursive | tail
aws s3 ls s3://aegis-bucket-data/raw/factory-b/infra_state/ --recursive | tail
```

Factory C:

```bash
aws s3 ls s3://aegis-bucket-data/raw/factory-c/factory_state/ --recursive | tail
aws s3 ls s3://aegis-bucket-data/raw/factory-c/infra_state/ --recursive | tail
```

nodes 배열 확인:

```bash
LATEST_B="$(aws s3 ls s3://aegis-bucket-data/raw/factory-b/infra_state/ --recursive | sort | tail -1 | awk '{print $4}')"
aws s3 cp "s3://aegis-bucket-data/${LATEST_B}" - | jq '.payload.nodes | map(.node_id)'

LATEST_C="$(aws s3 ls s3://aegis-bucket-data/raw/factory-c/infra_state/ --recursive | sort | tail -1 | awk '{print $4}')"
aws s3 cp "s3://aegis-bucket-data/${LATEST_C}" - | jq '.payload.nodes | map(.node_id)'
```

정상 기준:

```text
factory-b nodes = ["factory-b"]
factory-c nodes = ["factory-c-master", "factory-c-worker"]
```

## 중단 / 재시작

일반 운영에서는 repository의 wrapper를 사용한다.

```bash
scripts/ops/manage-dummy-generators.sh status factory-b
scripts/ops/manage-dummy-generators.sh start factory-b
scripts/ops/manage-dummy-generators.sh stop factory-b

scripts/ops/manage-dummy-generators.sh status factory-c
scripts/ops/manage-dummy-generators.sh start factory-c
scripts/ops/manage-dummy-generators.sh stop factory-c
```

`start/status`는 generator만 다룬다. `stop`은 generator를 멈추고, legacy local publisher unit이 설치돼 있으면 함께 멈춘다.

Factory B:

```bash
sudo systemctl restart aegis-factory-b-dummy-generator.service

sudo systemctl disable --now aegis-factory-b-dummy-generator.service
sudo systemctl disable --now aegis-factory-b-dummy-publisher.service 2>/dev/null || true
```

Factory C:

```bash
sudo systemctl restart aegis-factory-c-dummy-generator.service

sudo systemctl disable --now aegis-factory-c-dummy-generator.service
sudo systemctl disable --now aegis-factory-c-dummy-publisher.service 2>/dev/null || true
```

legacy local publisher가 설치돼 있다면 K3s `edge-iot-publisher`와 동시에 실행하지 않는다.

## 미수신 / 재수신 드릴

1~2일 동안 데이터가 들어오지 않다가 다시 들어오는 상황은 systemd 서비스를 멈췄다가 다시 시작해서 테스트한다.

스크립트:

| 파일 | 실행 위치 | 역할 |
| --- | --- | --- |
| `apps/dummy-sensor/scripts/factory-dummy-outage-drill.sh` | 대상 VM | generator/publisher를 멈췄다가 지정 시간 후 재시작 |
| `apps/dummy-sensor/scripts/check-s3-ingestion-gap.sh` | Computer 1 | S3 raw object가 outage window 동안 끊기고 이후 재개됐는지 확인 |

### 드릴 모드

| mode | 동작 | 검증 목적 |
| --- | --- | --- |
| `drop` | generator와 publisher 모두 중단 | 실제 현장/네트워크 중단처럼 새 데이터 자체가 없음. 재개 후 최신 데이터만 다시 들어옴 |
| `backlog` | publisher만 중단, generator는 계속 outbox 작성 | 통신 장애 후 밀린 로컬 outbox가 한 번에 flush되는 상황 확인 |

운영 관제의 "1~2일간 데이터 미수신" 테스트는 기본적으로 `drop` 모드를 사용한다. `backlog`는 별도 보상/재처리 동작을 확인할 때만 쓴다.

### VM에 드릴 스크립트 복사

Factory B:

```bash
scp apps/dummy-sensor/scripts/factory-dummy-outage-drill.sh \
    <vm-ssh-user>@<factory-b-ip>:/tmp/

ssh <vm-ssh-user>@<factory-b-ip> \
  'sudo install -m 755 /tmp/factory-dummy-outage-drill.sh /usr/local/bin/factory-dummy-outage-drill.sh'
```

Factory C:

```bash
scp apps/dummy-sensor/scripts/factory-dummy-outage-drill.sh \
    <vm-ssh-user>@${TS_IP_WORKER}:/tmp/

ssh <vm-ssh-user>@${TS_IP_WORKER} \
  'sudo install -m 755 /tmp/factory-dummy-outage-drill.sh /usr/local/bin/factory-dummy-outage-drill.sh'
```

### 짧은 smoke 드릴

먼저 2분짜리로 절차를 검증한다.

Factory B:

```bash
sudo /usr/local/bin/factory-dummy-outage-drill.sh --factory factory-b --duration 2m --mode drop
```

Factory C:

```bash
sudo /usr/local/bin/factory-dummy-outage-drill.sh --factory factory-c --duration 2m --mode drop
```

스크립트 출력의 `outage_start`, `outage_end`를 기록한다.

### 1~2일 드릴

Factory B:

```bash
sudo /usr/local/bin/factory-dummy-outage-drill.sh --factory factory-b --duration 1d --mode drop
```

Factory C:

```bash
sudo /usr/local/bin/factory-dummy-outage-drill.sh --factory factory-c --duration 1d --mode drop
```

2일 테스트는 `--duration 2d`를 사용한다.

터미널을 계속 열어두기 어렵다면 `--no-sleep`으로 중단만 수행하고, 원하는 시점에 수동 재시작한다.

```bash
sudo /usr/local/bin/factory-dummy-outage-drill.sh --factory factory-b --duration 2d --mode drop --no-sleep

# 재개 시점
sudo systemctl start aegis-factory-b-dummy-generator.service
sudo systemctl start aegis-factory-b-dummy-publisher.service
```

### S3 gap 확인

Computer 1에서 실행한다.

```bash
apps/dummy-sensor/scripts/check-s3-ingestion-gap.sh \
  --factory factory-b \
  --start 2026-05-20T00:00:00Z \
  --end 2026-05-21T00:00:00Z
```

Factory C:

```bash
apps/dummy-sensor/scripts/check-s3-ingestion-gap.sh \
  --factory factory-c \
  --start 2026-05-20T00:00:00Z \
  --end 2026-05-21T00:00:00Z
```

정상 해석:

```text
drop 모드:
  during = 0 또는 거의 0
  after  = 다시 증가

backlog 모드:
  during = 0 또는 거의 0
  after  = 밀린 outbox flush 때문에 일시적으로 급증 가능
```

Dashboard/Lambda 측에서는 이 드릴을 통해 아래를 확인한다.

- `infra_state` 미수신 시간이 warning/critical 상태로 반영되는지
- `factory_state` 미수신 중 risk 계산이 오래된 값을 그대로 정상처럼 표시하지 않는지
- 재수신 후 latest 상태가 다시 정상으로 복귀하는지
- 1~2일 gap 이후에도 S3 raw prefix와 DynamoDB history가 깨지지 않는지
