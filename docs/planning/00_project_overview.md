# 프로젝트 개요

상태: source of truth
기준일: 2026-05-06

## 목적

Aegis-Pi 프로젝트의 문제 정의, 목표, 사용자, 핵심 기능, 현재 구현 기준을 한 문서에서 빠르게 이해하기 위한 기준 문서다.

## 현재 상태

- 현재 완료된 범위는 `factory-a` Safe-Edge 기준선 구축/실장 테스트와 M1 Hub Issue 0~10이다.
- `factory-a`는 로컬 K3s 3노드, ArgoCD, Helm, Longhorn, InfluxDB, Grafana, AI 앱 failover/failback 기준선을 갖는다.
- GitOps 원격 저장소는 `https://github.com/aegis-pi/safe-edge-config-main.git`를 사용한다.
- AWS Hub EKS/VPC/namespace/ArgoCD bootstrap 기준선, foundation S3/AMP, AWS Load Balancer Controller, Route53/ACM, Admin UI HTTPS Ingress는 2026-05-06 `build-all --admin-ui` 및 `build-hub`로 active 상태를 확인했다.
- M1 Issue 5에서 IoT Rule -> S3 raw 적재와 `risk/risk-normalizer` IRSA S3 권한 검증을 완료했다.
- M1 Issue 6에서 AMP Workspace와 `observability/prometheus-agent` IRSA remote_write 권한 검증을 완료했다.
- M1 Issue 7에서 Hub Prometheus Agent를 설치하고 AMP Query API로 기본 메트릭 수신을 검증했다.
- M1 Issue 8에서 내부 Grafana를 설치하고 AMP datasource query를 검증했다.
- M1 Issue 9에서 AWS Load Balancer Controller를 설치하고 IRSA/subnet discovery 기준을 검증했다.
- M1 Issue 10에서 ArgoCD/Grafana HTTPS Admin Ingress를 공유 Public ALB로 검증했다.
- 구현 책임 경계는 Terraform = 인프라, Ansible = bootstrap/설정/소프트웨어, GitHub Actions = CI, GitHub+ArgoCD = CD로 고정한다.
- M1 Issue 12에서 `configs/runtime/runtime-config.yaml`과 VM dummy data 추천값을 작성했다.
- 다음 작업은 M2 Issue 1 Tailnet 생성 및 Spoke별 Auth Key 실발급이다. M1 Issue 11 운영 보안 강화는 MVP 이후로 보류했다.
- `factory-b`, `factory-c`, Edge Agent, Risk Twin은 후속 확장 단계다.

## 프로젝트명

- Aegis-Pi Risk Twin

## 한 줄 소개

- Safe-Edge 기반 단일 공장 생존형 엣지를 멀티 공장 중앙 관제 구조로 확장하는 Risk Twin 프로젝트

## 문제 정의

기존 Safe-Edge는 단일 공장, 폐쇄망, 라즈베리파이 3노드 K3s 기준선으로 의미 있는 성과를 냈다. 그러나 다음 한계가 있었다.

1. 여러 공장을 중앙에서 함께 보는 운영 구조가 없다.
2. 공장 단위 위험 상태를 표준화해 보여주는 상위 관제가 없다.
3. 로컬 엣지 운영 기준선이 멀티 환경 Fleet 운영과 클라우드 데이터 플레인으로 확장돼야 한다.

## 해결 방향

Aegis-Pi는 아래 방향으로 Safe-Edge를 확장한다.

- `factory-a`에 Safe-Edge 기준선을 실제로 복구하고 검증한다.
- 로컬 GitOps는 GitHub repository와 ArgoCD UI sync를 기준으로 운영한다.
- Grafana는 InfluxDB 센서/AI 결과와 Prometheus 노드 상태를 함께 보여준다.
- `factory-b`, `factory-c`를 테스트베드형 Spoke로 추가한다.
- AWS EKS Hub에서 여러 Spoke를 중앙 배포/처리한다.
- IoT Core -> S3 -> Risk Score 처리 흐름으로 공장별 위험 상태를 만든다.
- 관리자 대시보드는 Tailscale에 의존하지 않는 Dashboard VPC에서 Route53/ALB/WAF/Auth 뒤에 제공하고, processed S3와 latest status store를 read-only로 조회한다.

## 대상 사용자

- 1차 사용자: 본사 관제 담당자
- 2차 사용자: 현장 운영자, 배포 담당 개발자, 시스템 관리자
- 후속 사용자: 발표/검토/지도용 이해관계자

## 핵심 기능

- `factory-a` 로컬 생존형 엣지 운영
- ArgoCD/Helm 기반 GitOps 배포
- Longhorn 기반 엣지 데이터 복제
- Grafana 기반 센서/AI/노드 상태 시각화
- AI 앱 failover/failback 검증
- 멀티 공장 Fleet 운영으로 확장
- AWS IoT Core/S3 기반 중앙 수집으로 확장
- 공장별 위험 상태 시각화로 확장

## 현재 구현 상태

| 항목 | 상태 | 비고 |
| --- | --- | --- |
| `factory-a` K3s 3노드 | 완료 | master, worker1, worker2 |
| ArgoCD/Helm GitOps | 완료 | GitHub repo 등록 및 sync는 UI 기준 |
| Longhorn | 완료 | InfluxDB/PVC 복제 기준 |
| InfluxDB/Grafana | 완료 | Grafana `10.10.10.202` |
| Prometheus node dashboard | 완료 | Grafana dashboard ID `1860` |
| AI 앱 failover/failback | 완료 | LAN 제거 및 전원 제거 실측 |
| 이미지 prepull | 완료 | `safe-edge-image-prepull` DaemonSet |
| InfluxDB 1일 보존 | 완료 | retention policy 기준 |
| AI snapshot 1일 보존 | 완료 | `/app/snapshots` cleanup sidecar |
| AWS Hub | 진행 중 | M1 Issue 0~10/12 검증 완료, 현재 active 상태, Issue 11 보류 |
| Foundation S3 | 완료 | `aegis-bucket-data` active, IoT Rule raw 적재 검증 완료 |
| AMP/Grafana | 완료 | `AEGIS-AMP-hub` active, `observability/prometheus-agent` remote_write 수신, Grafana datasource query와 HTTPS Admin UI 검증 완료 |
| IoT Core | 완료 | `factory-a` Thing/certificate/policy, K3s Secret, IoT Rule/S3 적재 검증 완료, 현재 active |
| AWS 비용 기준 | 완료 | `docs/ops/15_aws_cost_baseline.md`, destroy 이후 `$0.0000/hour` |
| `factory-b`, `factory-c` | 후속 | 테스트베드형 Spoke |
| Risk Twin | 후속 | M6 이후 |

## 현재 freeze 범위

- `factory-a` 운영형 Spoke 기준선
- GitOps 저장소와 ArgoCD 앱 분리 방식
- `monitoring`, `ai-apps` namespace 분리
- Grafana/InfluxDB/Prometheus 관측 방식
- Longhorn 기반 로컬 데이터 보존 방식
- Failover/Failback 테스트 절차와 실측 결과

## 향후 확장

- AWS Hub와 Tailscale 기반 Hub-Spoke 연결
- Terraform / Ansible / GitHub Actions / ArgoCD 책임 경계 유지
- Dashboard VPC 기반 관리자 관제 접근
- GitHub Actions/ECR 이미지 빌드 파이프라인
- `runtime-config.yaml` 구조 초안
- Edge Agent 기반 IoT Core/S3 데이터 플레인 확장
- `factory-b`, `factory-c` 테스트베드형 Spoke
- Risk Twin 상태 카드와 공장별 위험도
- LLM 기반 일일 보고서/후처리
