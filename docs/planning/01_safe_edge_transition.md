# Safe-Edge에서 Aegis-Pi로의 전환 전략

상태: source of truth
기준일: 2026-04-28

## 목적

왜 Safe-Edge를 먼저 복구했는지, 현재 `factory-a`에서 무엇을 검증했는지, 그리고 어떤 설계 자산을 Aegis-Pi에서 계승하는지 정리한다.

## 현재 상태

- Safe-Edge는 Aegis-Pi의 선행 기준선이다.
- `factory-a` Safe-Edge 기준선은 실제 K3s/Longhorn/GitOps/모니터링/failover 테스트까지 완료됐다.
- 현재 프로젝트는 Safe-Edge를 폐기하지 않고, 운영형 Spoke 기준선으로 삼아 멀티 공장 구조로 확장한다.

## Safe-Edge에서 계승하는 것

- K3s 기반 경량 엣지 오케스트레이션
- 3노드 라즈베리파이 클러스터 운영
- Longhorn 기반 로컬 데이터 복제
- GitHub + ArgoCD + Helm 기반 GitOps 운영
- InfluxDB 기반 센서/AI 결과 저장
- Grafana 기반 현장 대시보드
- 센서/카메라/마이크 입력 파이프라인
- 장애 시 worker1 failover, 복구 시 worker2 failback 절차

## Safe-Edge의 한계와 Aegis-Pi 확장 방향

| 구분 | 현재 `factory-a` Safe-Edge | Aegis-Pi 확장 방향 |
| --- | --- | --- |
| 범위 | 단일 공장 | 멀티 공장 |
| 운영 | GitHub repo + ArgoCD UI sync | GitHub Actions + ECR + ArgoCD ApplicationSet |
| 데이터 | 로컬 InfluxDB 1일 보존 | IoT Core + S3 + Risk 처리 |
| 관제 | 현장 Grafana | 본사 통합 Risk Twin |
| 저장 | Longhorn 로컬 복제 | S3 장기 보존 및 분석 계층 |
| 장애 대응 | worker2 장애 시 worker1 승계 | Spoke별 정책과 Hub 관제 반영 |
| 위험 표현 | 센서/AI 패널 중심 | 공장 단위 `안전 / 주의 / 위험` |

## 구현 순서

1. `factory-a` Safe-Edge 기준선 재구성 및 검증
2. AWS Hub 기준선 구성
3. Hub와 `factory-a` 연결
4. GitHub Actions/ECR/ArgoCD 배포 파이프라인 구성
5. IoT Core/S3 데이터 플레인 연결
6. `factory-b`, `factory-c` 테스트베드형 Spoke 구성
7. Risk Twin 관제 확장

## 전환 전략 핵심 원칙

- Safe-Edge 없이 바로 Hub부터 시작하지 않는다.
- 운영형 Spoke는 `factory-a` 하나를 먼저 안정화한다.
- VM 환경은 Safe-Edge 전체 복제가 아니라 표준 구조 검증용으로 사용한다.
- 로컬 `factory-a`는 클라우드 전환 전에도 독립적으로 운영 가능해야 한다.
- 클라우드 마이그레이션 전에는 InfluxDB retention policy와 snapshot cleanup으로 로컬 저장소 증가를 제한한다.

## 현재 검증 완료 항목

- ArgoCD 설치 및 GitHub repo 연동 흐름 정리
- `monitoring`, `ai-apps` 분리
- Grafana에서 InfluxDB 센서/AI 결과 대시보드 구성
- Prometheus Node Exporter Full `1860` 대시보드 구성
- InfluxDB 1일 retention policy 적용
- AI snapshot Longhorn PVC 및 24시간 cleanup 적용
- LAN 제거 기반 failover/failback 테스트
- 전원 제거 기반 failover/failback 테스트
- 이미지 prepull DaemonSet 적용

## 후속 연결 문서

- `docs/ops/05_factory_a_status.md`
- `docs/ops/06_argocd_gitops.md`
- `docs/ops/07_grafana_dashboard.md`
- `docs/ops/08_data_retention.md`
- `docs/ops/09_failover_failback_test_results.md`
