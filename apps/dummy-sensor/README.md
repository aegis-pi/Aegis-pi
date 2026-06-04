# Dummy Sensor

`factory-b`, `factory-c` 테스트베드 Spoke에서 사용하는 더미 데이터 생성 코드를 둔다.

기준일: 2026-06-04

현재 구현 범위는 `factory-b` Mac UTM K3s testbed 와 `factory-c` Windows VirtualBox K3s testbed 용이다.

## Factory B/C 구조

Factory A 최신 데이터 플레인과 같은 경계를 따른다.

```text
factory_b_dummy_generator.py / factory_c_dummy_generator.py
  -> canonical JSON 생성
  -> local outbox 파일 저장

edge-iot-publisher (K3s, ArgoCD 배포)
  -> outbox JSON scan
  -> AWS IoT Core MQTT publish
  -> IoT Rule
  -> S3 raw/{factory_id}/{source_type}/...
```

`factory_b_iot_publisher.py`와 `factory_c_iot_publisher.py`는 legacy/manual smoke 용도다. 현재 표준 운영에서는 VM 로컬 publisher systemd를 켜지 않고, Spoke K3s의 `edge-iot-publisher`가 publish를 담당한다.

생성되는 source type:

| source type | 기본 주기 | 내용 |
| --- | --- | --- |
| `factory_state` | 3초 | factory별 profile 기반 센서/AI 가데이터 |
| `infra_state` | 20초 | factory별 K3s node/workload 상태 |

Factory별 프로파일:

| Factory | Host | Profile | Node topology | 값 특성 |
| --- | --- | --- | --- | --- |
| `factory-b` | Mac UTM | `stable-lab` | 2-node `master`/`worker1` | warning 중심 sensor/infra coverage, 25~30분 AI event |
| `factory-c` | Windows VirtualBox | `noisy-vm` | 2-node `factory-c-master`/`factory-c-worker` | critical/gate 중심 sensor/infra coverage, 25~30분 AI event |

공통 envelope는 Factory A 구현과 맞춰 `data_plane_instance_id`를 포함한다.

기본 profile은 순수 확률이 아니라 `랜덤 간격 + round-robin 이벤트 타입 + 랜덤 값`으로 risk input을 만든다. 평상시 baseline jitter는 유지하고, 이벤트가 due일 때만 sensor spike, infra 상태 변화, AI score를 주입한다. Sensor spike는 기본 30초 동안 유지해서 LATEST 기반 화면에서도 관찰 가능하게 한다.

AI score는 화재, 넘어짐, 굽힘, 이상소음을 각각 독립 이벤트로 스케줄링하지 않는다. `ai_warning` 또는 `ai_critical`이 25~30분 간격으로 due일 때 `fire_score`/`fall_score`/`bend_score` 중 일부를 랜덤으로 올리고 `abnormal_sound` label도 같은 `factory_state` 1건에 함께 넣는다. `factory-b`는 `ai_warning`만 쓰며 1~2개 score를 `0.5~0.8`로 설정한다. `factory-c`는 `ai_warning`/`ai_critical`을 round-robin으로 쓰며 warning은 1~3개 score를 `0.5~0.8`, critical은 1~3개 score를 `0.8~1.0`으로 설정한다.

Sensor spike 값 범위:

| Factory | Event | Range |
| --- | --- | --- |
| `factory-b` | `temperature_high` | `39.0~45.0` Celsius |
| `factory-b` | `humidity_high` | `88.0~96.0` percent |
| `factory-b` | `pressure_high` | `1055.0~1075.0` hPa |
| `factory-b` | `pressure_low` | `940.0~960.0` hPa |
| `factory-c` | `temperature_critical` | `45.0~52.0` Celsius |
| `factory-c` | `humidity_critical` | `95.0~99.0` percent |
| `factory-c` | `pressure_high_critical` | `1070.0~1090.0` hPa |
| `factory-c` | `pressure_low_critical` | `930.0~950.0` hPa |

pipeline freshness 확인용 이벤트는 payload에 status를 직접 넣지 않고 `--loop`에서 `infra_state` 생성을 건너뛰어 만든다. `factory-b`의 `pipeline_warning_gap`은 75~105초, `factory-c`의 `pipeline_critical_gap`은 135~180초, `pipeline_outage_gap`은 301~330초다. 현재 DataProcessor 기준은 warning 60초 초과, critical 120초 초과다.

## Local Preview

```bash
python3 apps/dummy-sensor/factory_b_dummy_generator.py --once all --no-write --pretty
python3 apps/dummy-sensor/factory_c_dummy_generator.py --once all --no-write --pretty
```

outbox에 1회 생성:

```bash
AEGIS_OUTBOX_DIR=/tmp/aegis-factory-c-outbox \
  python3 apps/dummy-sensor/factory_c_dummy_generator.py --once all
```

Factory B는 파일명과 경로만 바꾼다.

```bash
AEGIS_OUTBOX_DIR=/tmp/aegis-factory-b-outbox \
  python3 apps/dummy-sensor/factory_b_dummy_generator.py --once all
```

legacy publisher로 outbox를 1회 publish하는 smoke 테스트:

```bash
AEGIS_OUTBOX_DIR=/tmp/aegis-factory-c-outbox \
AEGIS_IOT_DIR=/etc/aegis/iot/factory-c \
AEGIS_IOT_CLIENT_ID=AEGIS-IoTThing-factory-c \
  python3 apps/dummy-sensor/factory_c_iot_publisher.py --once
```

Factory B:

```bash
AEGIS_OUTBOX_DIR=/tmp/aegis-factory-b-outbox \
AEGIS_IOT_DIR=/etc/aegis/iot/factory-b \
AEGIS_IOT_CLIENT_ID=AEGIS-IoTThing-factory-b \
  python3 apps/dummy-sensor/factory_b_iot_publisher.py --once
```

`AEGIS_IOT_DIR` 기본값은 factory별로 `/etc/aegis/iot/factory-b` 또는 `/etc/aegis/iot/factory-c` 이며 아래 파일을 읽는다.

```text
endpoint.txt
AmazonRootCA1.pem
certificate.pem.crt
private.pem.key
```

인증서 경로를 직접 지정하려면 아래 환경변수를 사용한다.

| 환경변수 | 기본값 |
| --- | --- |
| `AEGIS_IOT_ENDPOINT` | `AEGIS_IOT_DIR/endpoint.txt` |
| `AEGIS_IOT_CA_FILE` | `AEGIS_IOT_DIR/AmazonRootCA1.pem` |
| `AEGIS_IOT_CERT_FILE` | `AEGIS_IOT_DIR/certificate.pem.crt` |
| `AEGIS_IOT_KEY_FILE` | `AEGIS_IOT_DIR/private.pem.key` |
| `AEGIS_IOT_CLIENT_ID` | `AEGIS-IoTThing-factory-b` 또는 `AEGIS-IoTThing-factory-c` |
| `AEGIS_OUTBOX_DIR` | `/var/lib/aegis/outbox` |
| `AEGIS_CLUSTER_STATE_MODE` | `synthetic` (`kubernetes`는 workload만 조회하고 node ready는 고정) |
| `AEGIS_DUMMY_SCENARIO` | `normal`. node 장애 테스트 시 `node_down` |
| `AEGIS_DUMMY_SCENARIO_DOWN_NODES` | `node_down` 대상 node id CSV. 미지정 시 worker node |
| `AEGIS_DUMMY_SENSOR_EVENT_HOLD_SECONDS` | sensor spike 유지 시간. 기본 `30` |
| `KUBECONFIG` | 선택. systemd 실행 시 특정 kubeconfig를 지정할 때 사용 |

## Factory B VM systemd 예시

`factory-b` Mac UTM VM에서:

```bash
sudo mkdir -p /opt/aegis/dummy-sensor /var/lib/aegis/outbox /etc/aegis
sudo cp factory_b_dummy_generator.py factory_b_iot_publisher.py k8s_state.py /opt/aegis/dummy-sensor/
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

generator service:

```ini
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

[Install]
WantedBy=multi-user.target
```

legacy publisher service:

현재 표준 운영에서는 이 service를 설치/활성화하지 않는다. 같은 factory에서 K3s `edge-iot-publisher`와 동시에 실행하면 MQTT client id 충돌이나 중복 publish가 발생할 수 있다.

```ini
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

[Install]
WantedBy=multi-user.target
```

## Factory C Worker VM systemd 예시

`factory-c-worker` VM에서:

```bash
sudo mkdir -p /opt/aegis/dummy-sensor /var/lib/aegis/outbox /etc/aegis
sudo cp factory_c_dummy_generator.py factory_c_iot_publisher.py k8s_state.py /opt/aegis/dummy-sensor/
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

generator service:

```ini
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

[Install]
WantedBy=multi-user.target
```

legacy publisher service:

현재 표준 운영에서는 이 service를 설치/활성화하지 않는다. 같은 factory에서 K3s `edge-iot-publisher`와 동시에 실행하면 MQTT client id 충돌이나 중복 publish가 발생할 수 있다.

```ini
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

[Install]
WantedBy=multi-user.target
```

## Tests

```bash
python3 -m unittest discover -s apps/dummy-sensor/tests
```

## Runbook

VM에 파일을 복사하고 systemd로 상시 실행하는 전체 절차는 아래 문서를 기준으로 한다.

- `apps/dummy-sensor/docs/factory-b-c-dummy-systemd-runbook.md`

미수신/재수신 드릴용 script:

| 파일 | 용도 |
| --- | --- |
| `apps/dummy-sensor/scripts/factory-dummy-outage-drill.sh` | VM에서 systemd 서비스를 멈췄다가 재시작 |
| `apps/dummy-sensor/scripts/check-s3-ingestion-gap.sh` | Computer 1에서 S3 raw gap 확인 |
