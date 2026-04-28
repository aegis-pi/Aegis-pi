# 프로젝트 개요

상태: source of truth
기준일: 2026-04-28

## 목적

Aegis-Pi 프로젝트의 문제 정의, 목표, 사용자, 핵심 기능, 현재 구현 기준을 한 문서에서 빠르게 이해하기 위한 기준 문서다.

## 현재 상태

- 현재 완료된 범위는 `factory-a` Safe-Edge 기준선 구축 및 실장 테스트다.
- `factory-a`는 로컬 K3s 3노드, ArgoCD, Helm, Longhorn, InfluxDB, Grafana, AI 앱 failover/failback 기준선을 갖는다.
- GitOps 원격 저장소는 `https://github.com/aegis-pi/safe-edge-config-main.git`를 사용한다.
- AWS Hub, `factory-b`, `factory-c`, IoT Core, S3, Risk Twin은 다음 확장 단계다.

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
- AWS EKS Hub에서 여러 Spoke를 중앙 배포/관제한다.
- IoT Core -> S3 -> Risk Score 처리 흐름으로 공장별 위험 상태를 만든다.

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
| AWS Hub | 후속 | M1 이후 |
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
- GitHub Actions/ECR 이미지 빌드 파이프라인
- IoT Core/S3 데이터 플레인
- `factory-b`, `factory-c` 테스트베드형 Spoke
- Risk Twin 상태 카드와 공장별 위험도
- LLM 기반 일일 보고서/후처리
