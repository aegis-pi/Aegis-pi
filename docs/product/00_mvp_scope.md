# MVP 범위

상태: source of truth
기준일: 2026-05-08

## 목적

현재 MVP에 포함되는 것과 포함하지 않는 것을 분리한다.

## 현재 상태

- MVP의 첫 기준선인 M0 `factory-a` Safe-Edge 구축과 실측 검증은 완료됐다.
- AWS Hub EKS/ArgoCD, AWS Load Balancer Controller, Admin UI HTTPS Ingress, foundation S3/AMP/IoT Rule, `factory-a` IoT Thing/Policy/K3s Secret은 2026-05-06~2026-05-07 기준 `build-all --admin-ui`와 `build-hub`로 재생성/검증했고, 2026-05-08 비용 정리를 위해 destroy 완료 상태다.
- 전체 MVP는 운영형 Spoke 1개와 테스트베드형 Spoke 2개를 포함한 멀티 공장 관제 구조를 목표로 한다.

## 2026-05-13 멘토링 반영

### 기존 초안

기존 MVP 초안은 `factory-a/b/c`, EKS Hub, Tailscale, IoT Core -> S3, Risk Score, 메인 대시보드를 중심으로 정의했다. 이 초안에서는 LLM 기반 일일 보고서 자동 생성은 MVP 범위 초과로 분류했다.

### 변경 이유

멘토링에서는 CI/CD와 ArgoCD가 필요한 이유를 더 명확히 설명해야 한다는 피드백이 있었다. 단순 대시보드만으로는 모델/설정 업데이트와 배포 파이프라인의 필요성이 약해질 수 있다.

### 보강 방향

기존 MVP 범위는 유지하되, LLM 보고서를 전체 자동화 기능이 아니라 하루 1회 운영 리포트 초안 생성으로 제한해 포함하는 방향을 검토한다. 이 리포트는 자동 재학습이나 자동 배포가 아니라, Edge AI 판단의 실패/불확실 사례와 모델/설정 업데이트 후보를 찾는 용도다.

추가로 Dashboard 최신 상태는 S3 raw를 직접 조회하는 방식이 아니라, DynamoDB LATEST/HISTORY를 통해 준실시간으로 조회한다. S3 raw는 원본 보존, 재처리, 감사, 리포트 입력으로 유지한다.

## 현재 완료 범위

- `factory-a` Safe-Edge 기준선 재구성
- Raspberry Pi 3노드 K3s
- ArgoCD + Helm 기반 GitOps
- GitHub repo `https://github.com/aegis-pi/safe-edge-config-main.git`
- `monitoring`, `ai-apps` namespace 분리
- InfluxDB/Grafana/Prometheus
- Grafana 센서/AI/노드 대시보드
- Longhorn 기반 PVC
- InfluxDB 1일 retention policy
- AI snapshot 24시간 cleanup
- 이미지 prepull DaemonSet
- LAN 제거 및 전원 제거 failover/failback 테스트
- Hub EKS/VPC/namespace/ArgoCD bootstrap
- Foundation S3 bucket
- AMP Workspace
- IoT Rule -> S3 raw 적재
- `factory-a` IoT Thing/certificate/policy 및 K3s Secret

## MVP 포함 범위

- `factory-a` 운영형 Spoke
- `factory-b`, `factory-c` K3s 테스트베드형 Spoke
- AWS EKS Hub
- Tailscale 기반 Hub-Spoke 연결
- IoT Core -> S3 수집 경로
- Risk Score 기반 `안전 / 주의 / 위험` 표현
- 메인 대시보드
  - 공장별 위험 상태 카드
  - 센서 현황
  - 이상 시스템 목록
  - 최근 상태 변화 로그

## MVP 제외 범위

- LLM 기반 일일 보고서 자동 생성
- event 기반 점수 반영
- 별도 이벤트 전용 파이프라인
- 공장별 상세 커스텀 정책 활성화
- 완전 자동화된 장애/복구 리허설
- 장기 이력 분석 계층

## 후속 확장 범위

- event 입력 반영
- 분석 계층
- 공장 수 확대
- 세부 알람 정책
- 운영 자동화 고도화
- 장기 저장소와 리포트 자동화

## MVP 완료 판정

MVP는 아래 조건을 만족할 때 완료로 본다.

- `factory-a`, `factory-b`, `factory-c`가 Hub에서 독립 공장으로 식별된다.
- 운영형 `factory-a`는 실제 입력 기반 상태를 보낸다.
- 테스트베드형 `factory-b`, `factory-c`는 Dummy 시나리오 기반 상태를 보낸다.
- Hub 관제에서 공장별 `안전 / 주의 / 위험` 상태가 보인다.
- 배포, 데이터 수집, 장애 시나리오가 문서와 일치한다.
