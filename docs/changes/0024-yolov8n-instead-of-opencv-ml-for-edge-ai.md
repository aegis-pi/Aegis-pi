# Change 0024 - YOLOv8n instead of OpenCV ML for Edge AI detection

상태: accepted
결정일: 2026-06-08

## 기존 계획

초기 Safe-Edge AI 구현은 Raspberry Pi camera frame을 처리해 화재, 연기, 낙상, 굽힘 이벤트를 감지하는 것을 목표로 했다.

구현 선택지에는 아래 방식이 있었다.

- OpenCV 기반 image processing과 OpenCV ML/HOG/SVM/contour 등 전통적 computer vision 방식
- 경량 deep learning object detection model
- pose estimation model을 이용한 사람 자세 판단

## 변경된 실제 기준

현재 `factory-a`의 `safe-edge-integrated-ai`는 OpenCV를 camera frame 변환과 snapshot 저장에 사용하고, 핵심 AI 판단은 YOLOv8n 계열 모델로 수행한다.

```text
OpenCV 역할:
  - frame color conversion: cv2.cvtColor
  - event snapshot 저장: cv2.imwrite

YOLO 역할:
  - fire.pt: FIRE/SMOKE object detection
  - pose.pt: person pose/keypoint 기반 FALLEN/BENDING 판단
```

현재 처리 루프는 아래 순서다.

```text
picam2.capture_array()
-> cv2.cvtColor()
-> fire_model(frame_bgr, imgsz=320)
-> pose_model(frame_bgr, imgsz=320)
-> event 판단
-> optional cv2.imwrite(snapshot)
-> InfluxDB write_points(ai_detection)
-> sleep(1)
```

## 변경 이유

OpenCV ML 자체가 부적합해서 제외한 것이 아니라, 현재 문제의 핵심이 단순 image classification이나 규칙 기반 영상 처리보다 object detection과 pose estimation에 가깝기 때문이다.

화재/연기 감지는 이벤트 존재 여부뿐 아니라 위치, confidence, class가 필요하다. YOLO는 bounding box, confidence, class를 한 번에 제공하므로 화재/연기 객체 감지에 직접적이다.

낙상/굽힘 판단은 사람의 자세 변화가 핵심이다. 현재 앱은 `pose.pt` 결과의 bounding box 비율과 어깨-엉덩이 keypoint 각도를 이용한다. OpenCV contour, HOG, SVM 기반으로 같은 수준의 자세 의미를 안정적으로 얻으려면 조명, 배경, 카메라 각도, 사람 체형에 대한 예외 처리가 많아진다.

`yolov8n`은 YOLOv8 계열 중 nano model이라 Raspberry Pi edge node에서 운영 가능한 현실적인 크기와 속도를 제공한다. 모델 교체, fine-tuning, ONNX/NCNN 같은 edge inference 최적화 경로도 명확하다.

따라서 OpenCV는 영상 입출력과 가벼운 전처리에 사용하고, ML 판단은 경량 YOLO object detection/pose model에 맡기는 분리 구조를 채택했다.

## 영향

- 구현 복잡도가 낮아진다. 직접 feature engineering과 rule cascade를 크게 줄일 수 있다.
- FIRE/SMOKE는 class와 confidence threshold 기반으로 판단할 수 있다.
- FALLEN/BENDING은 pose/keypoint 기반 rule로 설명 가능하다.
- 모델 성능 개선은 dataset fine-tuning이나 model export/교체로 이어갈 수 있다.
- OpenCV ML 대비 model artifact(`fire.pt`, `pose.pt`) 의존성이 생긴다.
- Raspberry Pi CPU에서 두 YOLO model을 순차 실행하므로 loop latency와 resource 사용량을 지속 관찰해야 한다.

## 대안 검토

### OpenCV ML/HOG/SVM/Contour 기반

장점:

- 의존성이 비교적 단순하다.
- 작은 rule이나 특정 환경에서는 빠르게 동작할 수 있다.
- deep learning model artifact 관리가 필요 없다.

한계:

- 화재/연기처럼 형태와 색상이 변하는 객체에 대해 조명, 배경, 반사, 카메라 각도 영향을 크게 받는다.
- 낙상/굽힘은 사람 자세 의미를 직접 표현하기 어렵다.
- 운영 환경이 바뀔수록 rule과 threshold 보정 비용이 커진다.
- bounding box, class confidence, pose keypoint 같은 downstream 판단 재료를 바로 얻기 어렵다.

### YOLOv8n Object Detection/Pose

장점:

- object detection 결과가 event 판단에 바로 연결된다.
- pose keypoint를 이용해 낙상/굽힘 판단을 설명 가능하게 구성할 수 있다.
- nano model이라 edge 환경에 배포 가능한 속도를 보인다.
- custom dataset fine-tuning과 model export/최적화 경로가 명확하다.

한계:

- model file 관리와 image build/release 절차가 필요하다.
- CPU-only Raspberry Pi에서는 latency가 model 수와 image size에 민감하다.
- 정확한 stage별 latency 확인을 위해 instrumentation이 필요하다.

## 검증

2026-06-08 `factory-a` 운영 Pod에서 재시작 없이 one-shot benchmark를 수행했다.

입력:

```text
container: safe-edge-integrated-ai / ai-processor
image: /app/snapshots/260608122326_event_FALLEN.jpg
shape: 480x640
imgsz: 320
sample: warmup 1회 제외, 5회 집계
```

결과:

```text
fire.inference_ms median=96.3ms, avg=129.3ms, min=91.3ms, max=256.9ms
pose.inference_ms median=102.0ms, avg=105.8ms, min=101.5ms, max=114.7ms
two-model inference median total ~= 198ms
```

동일 시점의 운영 loop 관측값:

```text
AI STATUS log interval avg=1.228s, p95=1.261s
InfluxDB ai_detection point interval avg=1.229s, p95=1.264s
fixed sleep=1.000s
active loop avg ~= 228ms
```

두 YOLO model의 median inference 합계가 약 198ms이고 active loop 평균이 약 228ms이므로, 현재 MVP의 1초대 감시 주기에는 충분히 들어온다.

자세한 latency 기준은 `docs/ops/33_factory_a_ai_latency_measurement.md`를 따른다.

## 업데이트 문서

- `docs/ops/33_factory_a_ai_latency_measurement.md`
- `docs/changes/README.md`

## 운영 기준

- OpenCV는 camera frame 변환, snapshot 저장 등 image I/O와 전처리에 계속 사용한다.
- 화재/연기/사람 자세 판단은 YOLO model 기반을 유지한다.
- 성능 개선은 우선 instrumentation으로 stage별 latency를 분리한 뒤, image size, model export, model 교체, threshold 조정을 검토한다.
- 운영 중 model 변경이나 instrumentation 적용은 image build/push와 rollout이 필요하므로 사전 영향 설명과 승인을 거친다.
