# Portfolio Idea Assessment

이 문서는 Aegis-Pi Risk Twin 아이디어를 포트폴리오 관점에서 평가한 기록이다.
현재 프로젝트는 개발 중이므로, 구현 완성도보다 아이디어의 실무성, 차별성, 전달 메시지, MVP 범위를 중심으로 본다.

## 한 줄 정의

Aegis-Pi Risk Twin은 공장 엣지 장애와 데이터 공백을 중앙에서 정량화하고, 각 공장의 위험 상태를 비교 가능한 Risk Score로 보여주는 Edge-to-Cloud 운영 관제 플랫폼이다.

## 아이디어 평가

아이디어 자체의 실무성은 높다.
Raspberry Pi 기반 단일 공장 엣지 운영 기준선을 먼저 만들고, 이후 AWS Hub, 멀티 Spoke, Risk Twin 관제로 확장하는 흐름은 실제 산업 IoT와 엣지 운영 문제에 가깝다.

일반적인 CRUD 서비스나 단순 모니터링 대시보드보다 문제의 난도가 높고, 네트워크 단절, 노드 장애, failover/failback, 데이터 공백, 로컬 저장 정책, 중앙 관제 같은 운영 요소를 함께 다룬다는 점에서 포트폴리오 주제로 경쟁력이 있다.

다만 현재 아이디어는 범위가 크다.
K3s, Longhorn, ArgoCD, Grafana, EKS, IoT Core, S3, Risk Score, Dashboard VPC, Tailscale, `factory-b`, `factory-c`가 한꺼번에 등장하면 핵심 메시지가 흐려질 수 있다.
포트폴리오에서는 "기술을 많이 쓴 프로젝트"가 아니라 "엣지 장애와 데이터 공백을 위험도로 모델링하는 프로젝트"로 보여야 한다.

## 강점

### 실제 엣지 환경의 제약을 다룬다

`factory-a`는 단순 시뮬레이션이 아니라 Raspberry Pi 3-node K3s 기준선 위에서 운영되는 구조다.
노드 장애, LAN 제거, `k3s-agent` 중지, failover/failback, Longhorn PVC, MetalLB, ArgoCD, Grafana 같은 요소는 실제 운영 환경에서 마주치는 문제와 연결된다.

### 운영 검증 중심의 주제다

이 프로젝트의 강점은 "구성했다"보다 "장애 상황에서 어떻게 동작하는지 확인했다"에 있다.
장애 중 워크로드가 어디로 이동하는지, 데이터 공백이 몇 초 발생하는지, 복구 후 원래 노드로 돌아오는지 같은 항목은 포트폴리오에서 실무적인 신뢰를 준다.

### Cloud Hub 확장이 자연스럽다

엣지에서 수집한 센서값과 시스템 상태를 Hub로 올리고, 공장별 상태를 중앙에서 비교하는 구조는 산업 IoT 맥락과 맞다.
IoT Core, S3 raw, Lambda data processor, DynamoDB LATEST/HISTORY, S3 processed, Dashboard VPC로 이어지는 확장 방향도 설계상 자연스럽다.

## 약점과 주의점

### Risk Twin의 차별성을 더 명확히 해야 한다

현재 이름은 Risk Twin이지만, 포트폴리오에서 설득력을 가지려면 Risk Score가 정확히 무엇을 근거로 계산되는지 보여야 한다.
단순 CPU, memory, pod 상태 조합이라면 기존 Grafana 모니터링과 차별성이 약하다.

Risk Score의 입력은 최소한 다음 항목을 포함하는 방향이 좋다.

- `sensor_freshness`
- `workload_health`
- `failover_state`
- `pipeline_heartbeat`
- `data_gap_seconds`
- `device_status`
- `edge_node_status`

이 항목들을 조합해 `normal`, `warning`, `critical` 상태와 원인을 계산하면 "대시보드"가 아니라 "위험 판단 시스템"으로 보인다.

### 범위가 커 보이는 위험이 있다

전체 목표를 한 번에 말하면 개인 프로젝트로는 과하게 넓어 보일 수 있다.
면접이나 README 첫 화면에서는 완료된 범위, 개발 중인 범위, 후속 범위를 강하게 분리해야 한다.

특히 `factory-b`, `factory-c`, Dashboard VPC, IoT Core, S3, Risk Twin UI를 모두 같은 무게로 설명하면 아직 구현 중인 프로젝트의 약점이 먼저 보인다.
핵심은 `factory-a`의 운영 기준선과, 그 위에 올라갈 Risk Twin 데이터 모델이다.

### "기술 스택 나열"로 보이면 약해진다

K3s, EKS, ArgoCD, Longhorn, Grafana, IoT Core를 썼다는 사실 자체보다, 왜 그 기술이 이 문제에 필요한지가 중요하다.
예를 들어 Longhorn은 엣지 장애 시 PVC를 유지하기 위한 선택이고, ArgoCD는 Spoke 배포 기준선을 재현하기 위한 선택이며, IoT Core/S3는 엣지 데이터를 Hub와 분리된 방식으로 수집하기 위한 선택이라는 식으로 설명해야 한다.

## 권장 포트폴리오 메시지

포트폴리오에서는 아래 메시지를 중심에 둔다.

> 공장 엣지 시스템은 장애가 나도 즉시 멈추면 안 되고, 중앙 관리자는 각 공장의 위험 상태와 원인을 빠르게 알아야 한다.
> Aegis-Pi는 Raspberry Pi K3s 엣지에서 장애와 데이터 공백을 측정하고, 이를 표준 상태 이벤트와 Risk Score로 변환해 중앙에서 비교 가능하게 만드는 프로젝트다.

이 메시지는 현재 구현 중인 상태와도 맞고, 후속 확장 방향도 자연스럽게 포함한다.

## MVP 범위 제안

포트폴리오 MVP는 아래 다섯 단계로 좁히는 것이 좋다.

1. `factory-a`에서 장애 발생 시 워크로드가 살아남는지 검증한다.
2. 장애 동안 발생한 데이터 공백을 측정한다.
3. Edge Agent가 공장 상태를 표준 이벤트로 Hub에 보낸다.
4. Lambda data processor가 상태를 `normal`, `warning`, `critical`로 계산한다.
5. 대시보드가 공장별 위험 원인을 보여준다.

이 범위가 완성되면 프로젝트는 "엣지 운영 자동화"와 "중앙 위험 관제"를 모두 보여줄 수 있다.
반대로 이 범위가 완성되기 전에는 Dashboard VPC, 멀티 Spoke, 배포 파이프라인, 장기 데이터 레이크를 모두 같은 우선순위로 밀지 않는 편이 좋다.

## 개발 우선순위

포트폴리오 설득력을 높이는 순서는 다음과 같다.

1. Edge Agent 최소 구현
2. Lambda data processor Risk 계산 로직 최소 구현
3. Risk 입력 스키마와 샘플 이벤트
4. 단위 테스트와 smoke test
5. 간단한 공장별 상태 대시보드
6. IoT Core/S3 또는 대체 가능한 Hub 수집 경로
7. `factory-b`, `factory-c` dummy mode 확장

현재 문서와 운영 기록은 이미 충분히 많다.
다음 단계에서는 더 많은 계획 문서보다, 작게라도 실행 가능한 코드와 테스트가 포트폴리오 가치를 더 크게 올린다.

## 최종 판단

Aegis-Pi Risk Twin은 포트폴리오 아이디어로 충분히 경쟁력이 있다.
흔한 웹 서비스나 단순 대시보드보다 실무 문제에 가깝고, 엣지 장애와 데이터 공백을 Risk Score로 연결한다는 점이 차별점이다.

다만 아이디어의 중심은 "많은 기술을 연결한 플랫폼"이 아니라 "엣지 장애와 데이터 공백을 위험도로 모델링하는 운영 관제 시스템"이어야 한다.
이 메시지만 선명하게 유지하면, 개발 중인 상태에서도 프로젝트의 방향성과 실무적 가치는 잘 전달된다.
