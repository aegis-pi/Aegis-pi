# Factory-A AI Latency Measurement

상태: measured baseline
기준일: 2026-06-08

## 목적

`factory-a`의 `safe-edge-integrated-ai` workload에서 카메라 frame capture부터 YOLO 추론, event 판단, snapshot 저장, InfluxDB 기록까지의 처리 시간을 가능한 범위에서 측정한다.

이 문서는 운영 workload를 재시작하거나 patch하지 않고 읽기 전용 확인과 one-shot benchmark만으로 얻은 기준값이다.

## 현재 배포 상태

2026-06-08 확인 기준:

```text
namespace: ai-apps
deployment: safe-edge-integrated-ai
pod: safe-edge-integrated-ai-5bc6fb8796-4sssf
node: worker2
status: 2/2 Running
image: minsoo0919/safe-edge-ai:v6
containers: ai-processor, snapshot-cleanup
snapshot mount: /app/snapshots -> /var/lib/safe-edge/snapshots hostPath
```

`safe-edge-integrated-ai`는 `worker2`에 preferred node affinity로 배치되어 있으며, 현재 Pod는 `worker2`에서 정상 동작 중이다.

## 처리 루프 구조

컨테이너 내부 `/app/app.py` 기준 처리 순서는 아래와 같다.

```text
while True:
  1. picam2.capture_array()
  2. cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
  3. fire_model(frame_bgr, imgsz=320, verbose=False)
  4. pose_model(frame_bgr, imgsz=320, verbose=False)
  5. fire/fallen/bending event 판단
  6. event detected and cooldown passed -> cv2.imwrite(snapshot)
  7. InfluxDB client.write_points(ai_detection)
  8. time.sleep(1)
```

InfluxDB measurement:

```text
measurement: ai_detection
tags: location=danger_zone, node=worker-2
fields: fire_detected, fallen_detected, bending_detected
```

Snapshot 설정:

```text
SNAPSHOT_DIR=/app/snapshots
COOLDOWN_SEC=5
filename format: {YYMMDDHHMMSS}_event_{EVENT}.jpg
```

주의: 앱 코드 주석에는 10초 cooldown이라고 적혀 있지만 실제 값은 `COOLDOWN_SEC = 5`다.

## Loop 주기 측정

AI 앱 로그의 `[AI STATUS]` timestamp 300개를 집계했다.

```text
samples=300
intervals=299
min=1.204s
avg=1.228s
median=1.224s
p95=1.261s
max=1.279s
```

InfluxDB `ai_detection` 최신 120 point interval도 거의 동일하다.

```text
points=120
intervals=119
min=1.204s
avg=1.229s
median=1.226s
p95=1.264s
max=1.292s
```

앱 코드에 `time.sleep(1)`이 고정으로 들어가 있으므로, 정상 loop에서 활성 처리 시간은 대략 아래와 같이 추정된다.

```text
active loop avg ~= 1.228s - 1.000s = 0.228s
active loop p95 ~= 1.261s - 1.000s = 0.261s
```

여기서 active loop는 frame capture, color conversion, fire inference, pose inference, event 판단, optional snapshot 저장, InfluxDB write를 모두 포함한다. 측정 당시 최신 loop는 event가 없는 상태였으므로 snapshot 저장 시간은 포함되지 않은 것으로 봐야 한다.

## YOLO One-Shot Benchmark

운영 Pod를 재시작하지 않고, 같은 `ai-processor` 컨테이너에서 별도 Python 프로세스로 최신 snapshot 1장을 읽어 `fire.pt`, `pose.pt`를 각각 6회 실행했다. 첫 1회는 warmup으로 제외하고 5회만 집계했다.

입력:

```text
image=/app/snapshots/260608122326_event_FALLEN.jpg
shape=(480, 640, 3)
imgsz=320
```

결과:

```text
fire.wall_ms       avg=131.2  median=98.1   min=93.2   max=258.8
fire.preprocess_ms avg=1.1    median=1.1    min=1.0    max=1.1
fire.inference_ms  avg=129.3  median=96.3   min=91.3   max=256.9
fire.postprocess_ms avg=0.5   median=0.5    min=0.5    max=0.5

pose.wall_ms       avg=107.8  median=103.8  min=103.5  max=116.5
pose.preprocess_ms avg=1.1    median=1.0    min=1.0    max=1.2
pose.inference_ms  avg=105.8  median=102.0  min=101.5  max=114.7
pose.postprocess_ms avg=0.6   median=0.6    min=0.6    max=0.7
```

해석:

```text
fire inference typical: about 91-96ms
fire inference with outlier: avg about 129ms
pose inference typical: about 102ms
two-model inference typical total: about 198ms
```

Loop active time 추정치가 약 228ms이고, two-model inference median 합계가 약 198ms이므로 나머지 약 30ms가 capture, color conversion, postprocess, event 판단, InfluxDB write 등에 사용된 것으로 볼 수 있다.

## 현재 Latency Baseline

2026-06-08 현재 관측 가능한 기준값:

| 구간 | 현재 기준값 | 근거 | 비고 |
| --- | ---: | --- | --- |
| 한 loop 전체 | avg 1.228s, p95 1.261s | `[AI STATUS]` 로그 timestamp | `time.sleep(1)` 포함 |
| active loop 전체 | avg 약 228ms, p95 약 261ms | loop 전체에서 sleep 1초 차감 | snapshot 미포함 상태 |
| fire model inference | median 96.3ms | one-shot benchmark `result.speed["inference"]` | 1회 outlier 256.9ms |
| pose model inference | median 102.0ms | one-shot benchmark `result.speed["inference"]` | 비교적 안정적 |
| two-model inference 합계 | median 약 198ms | fire + pose median | active loop 대부분 |
| capture + conversion + 판단 + InfluxDB write | 약 30ms 수준 추정 | active loop - inference median | 단계별 직접 측정 아님 |
| snapshot 저장 | 미측정 | 최근 loop에 event 없음 | `cv2.imwrite()` instrumentation 필요 |
| snapshot upload | backlog 기준 1개당 대략 1.2-1.5s 로그 관찰 | snapshot-uploader 로그 | 신규 파일 end-to-end latency로 사용 불가 |

## 측정 한계

현재 앱 로그만으로는 아래 값을 직접 분리할 수 없다.

- `picam2.capture_array()` 시간
- RGB/BGR conversion 시간
- fire YOLO preprocess/inference/postprocess의 운영 loop 내부 값
- pose YOLO preprocess/inference/postprocess의 운영 loop 내부 값
- event 판단 시간
- `cv2.imwrite()` snapshot 저장 시간
- `client.write_points()` InfluxDB write 시간

Ultralytics 결과 객체에는 `result.speed`가 있으므로 모델별 preprocess/inference/postprocess 자체는 앱 코드에서 출력할 수 있다. 현재 배포된 `app.py`가 그 값을 로그에 남기지 않을 뿐이다.

One-shot benchmark는 같은 컨테이너, 같은 모델, 같은 Pi에서 실행했으므로 모델 추론 시간의 유효한 근사치다. 다만 운영 loop와 완전히 동일하지는 않다.

- 별도 Python 프로세스가 모델을 추가 로드한다.
- 기존 AI loop와 CPU/memory 자원을 잠깐 공유한다.
- 최신 snapshot 정지 이미지를 입력으로 사용한다.
- camera capture와 InfluxDB write는 benchmark에 포함되지 않는다.

## 더 정확한 측정 방안

운영 loop 내부에 `time.perf_counter()` 기반 instrumentation을 추가한다.

권장 로그 형식:

```text
[AI LATENCY] capture_ms=18.4 convert_ms=2.1 fire_pre_ms=1.1 fire_infer_ms=96.3 fire_post_ms=0.5 pose_pre_ms=1.0 pose_infer_ms=102.0 pose_post_ms=0.6 decision_ms=0.2 snapshot_ms=0.0 influx_ms=8.6 loop_active_ms=229.0 loop_total_ms=1229.5 event=none
```

수정 위치:

```text
loop start
  capture_array 전후
  cvtColor 전후
  fire_model 전후 + fire_results[0].speed
  pose_model 전후 + pose_results[0].speed
  event 판단 전후
  cv2.imwrite 전후
  client.write_points 전후
loop end
```

예상 영향:

- 로그 출력과 `perf_counter()` 호출만 추가하면 CPU 영향은 작다.
- 정확한 운영값을 얻으려면 새 image build/push와 `safe-edge-integrated-ai` rollout이 필요하다.
- rollout 시 카메라 재초기화 때문에 AI 감시와 InfluxDB write에 짧은 공백이 생길 수 있다.
- 운영 적용 전에는 영향과 시점을 설명하고 승인받아야 한다.

## 참고 명령

Loop 로그 interval 집계:

```bash
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n ai-apps logs deploy/safe-edge-integrated-ai -c ai-processor --tail=300 --timestamps
```

InfluxDB 최신 point 확인:

```bash
kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n monitoring exec deploy/influxdb -- \
  influx -database safe_edge_db \
  -execute 'SELECT fire_detected,fallen_detected,bending_detected FROM ai_detection ORDER BY time DESC LIMIT 20'
```

One-shot YOLO benchmark는 운영 workload를 재시작하지 않지만, 같은 컨테이너에서 모델을 추가 로드하므로 잠깐 CPU/memory 부하가 생긴다. 반복 실행은 피하고, 필요할 때 짧게 실행한다.

## 별도 관찰사항

2026-06-08 확인 중 `aegis-spoke-edge-iot-publisher` 로그에서 `unsupported source_type: image_snapshot`가 반복됐다. 이 문서는 AI 추론 latency 측정 기록이므로 해당 문제는 수정하지 않았다. Snapshot pipeline의 metadata publish 상태를 다시 검증할 때 별도 확인이 필요하다.
