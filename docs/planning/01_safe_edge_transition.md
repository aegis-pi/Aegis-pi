# Safe-Edge에서 Aegis-Pi로의 전환 전략

상태: source of truth
기준일: 2026-04-24

## 목적

왜 Safe-Edge를 먼저 복구해야 하는지, 그리고 어떤 설계 자산을 Aegis-Pi에서 계승하는지 정리한다.

## 현재 상태

- Safe-Edge는 Aegis-Pi의 선행 기준선이다.
- 현재 프로젝트는 Safe-Edge를 폐기하지 않고, 기준선으로 삼아 멀티 공장 구조로 확장한다.

## 범위

- Safe-Edge 핵심 자산
- 반드시 계승할 항목
- 확장해야 할 항목
- 구현 순서상의 의미

## 상세 내용

## Safe-Edge에서 계승하는 것

- K3s 기반 경량 엣지 오케스트레이션 경험
- 3노드 라즈베리파이 클러스터 운영 경험
- Longhorn 기반 데이터 보존 구조
- 폐쇄망 GitOps 운영 감각
- 센서/카메라/마이크 입력 파이프라인 경험

## Safe-Edge의 한계와 Aegis-Pi 확장 방향

| 구분 | Safe-Edge | Aegis-Pi 확장 방향 |
| --- | --- | --- |
| 범위 | 단일 공장 | 멀티 공장 |
| 운영 | 로컬 GitLab + ArgoCD | GitHub Actions + ECR + ArgoCD |
| 데이터 | 로컬 보존 중심 | IoT Core + S3 + Risk 처리 |
| 관제 | 현장 중심 | 본사 통합 관제 |
| 위험 표현 | 이벤트/개별 상태 중심 | 공장 단위 Risk Twin |

## 구현 순서

1. `factory-a` Safe-Edge 기준선 재구성
2. `factory-b`, `factory-c` 테스트베드형 Spoke 구성
3. AWS Hub 연결
4. 데이터 플레인 연결
5. Risk Twin 관제 확장

## 전환 전략 핵심 원칙

- Safe-Edge 없이 바로 Hub부터 시작하지 않는다.
- 실제 운영형 Spoke는 `factory-a` 하나를 먼저 안정화한다.
- VM 환경은 Safe-Edge 전체 복제가 아니라 표준 구조 검증용으로 사용한다.

## TODO

- TODO: Safe-Edge 실제 복구 완료 후 검증 결과를 여기에 연결한다.
