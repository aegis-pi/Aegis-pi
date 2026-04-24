# 구현 전략 및 단계 계획

상태: draft
기준일: 2026-04-24

## 목적

프로젝트를 어떤 순서로 구현할지, 각 단계에서 무엇을 만들어야 하고 어떤 조건이 만족되면 다음 단계로 넘어갈 수 있는지 정리한다.

## 현재 상태

- 구조 설계는 1차 정리 완료
- 실제 구현 단계는 아직 시작 전
- 현재 구현은 `factory-a` Safe-Edge 기준선 복구부터 시작하는 것으로 정리돼 있다.
- `docs/issues/` 하위 마일스톤 문서를 기준으로 구현 순서를 M0~M7로 정리한다.

## 범위

- 단계별 구현 순서
- 단계별 완료 조건
- 후속 보정 항목 위치
- 단계 간 선행 관계
- 각 단계의 주요 산출물

## 상세 내용

## 단계 계획

### Phase 0. 문서 기준선 고정

- `docs/` 기준 문서 정리
- 역할, 아키텍처, 테스트 전략 고정

완료 조건:
- 현재 기준 문서가 충돌 없이 읽힌다

주요 산출물:
- `docs/`
- 현재 구조/운영/스펙 기준 문서

### Phase 1. M0 `factory-a` Safe-Edge 기준선 재구성

선행 조건:
- Phase 0 문서 기준선 고정
- 하드웨어 / 네트워크 준비 가능

주요 작업:
- Raspberry Pi OS 기본 세팅
- 고정 IP 및 내부망 기준선 구성
- K3s 3노드 클러스터 구성
- MetalLB / Traefik
- Longhorn / NFS
- GitLab + ArgoCD 기준선
- Prometheus / InfluxDB / Grafana
- 센서 / 카메라 / 마이크 입력 복구
- Failover / 운영 자동화 기준 확인

완료 조건:
- Safe-Edge 핵심 동작 복구
- 센서/상태/모니터링 경로 확인
- `factory-a`가 운영형 Spoke 기준선으로 설명 가능

주요 산출물:
- `factory-a` 3노드 K3s
- Longhorn / NFS 기준선
- GitLab + ArgoCD 기준선
- Prometheus / InfluxDB / Grafana 기준선
- 실제 센서/카메라/마이크 입력 경로
- Failover / 운영 자동화 기준선

다음 단계로 넘어가는 조건:
- `docs/ops/safe_edge_bootstrap.md`의 최소 완료 기준 충족
- Safe-Edge 기준선이 다시 설명 가능

### Phase 2. M1 Hub 기준선 구성

선행 조건:
- Phase 1 완료
- `factory-a` 기준선 복구 확인

주요 작업:
- AWS EKS
- Hub 네임스페이스 구성
- ArgoCD 설치
- S3 버킷 및 경로 파티셔닝 설계
- IoT Core Thing / 인증서 / 규칙
- AMP Workspace
- Hub Prometheus / Grafana
- `runtime-config.yaml` 구조 초안

완료 조건:
- Hub 자체가 독립적으로 배치되어 있음
- Spoke 연결을 받을 준비가 완료됨

주요 산출물:
- EKS 기본 클러스터
- `argocd`, `observability`, `risk`, `ops-support` 배치 기준
- S3 / IoT Core / AMP 기준선
- `configs/runtime/runtime-config.yaml` 경로 및 구조 초안

다음 단계로 넘어가는 조건:
- Hub 핵심 서비스 배치 가능
- Spoke 연결을 받을 준비 완료

### Phase 3. M2 Mesh VPN + Hub-Spoke 연결

선행 조건:
- Phase 2 완료
- `factory-a` Master 접근 준비 가능

주요 작업:
- Tailscale 계정 및 Spoke별 키 정책
- `factory-a` Master Tailscale 참여
- EKS Hub Tailscale 참여
- kubeconfig Tailscale IP 기반 구성
- ArgoCD `factory-a` 등록
- Hub -> `factory-a` Sync 검증

완료 조건:
- Hub에서 `factory-a` Spoke API 접근 가능
- ArgoCD가 `factory-a`에 테스트 배포 가능

주요 산출물:
- Tailscale Tailnet
- `factory-a.kubeconfig`
- Hub -> `factory-a` 접근 경로
- ArgoCD 등록된 운영형 Spoke

다음 단계로 넘어가는 조건:
- ArgoCD에서 `factory-a` 대상 Sync 확인 가능
- Mesh 기반 API 접근이 안정적으로 설명 가능

### Phase 4. M3 배포 파이프라인 구성

선행 조건:
- Phase 3 완료
- 기준 앱과 공통 차트 구조 준비

주요 작업:
- Helm 베이스 + 공장별 values 구조
- ECR 저장소 및 태그 전략
- GitHub Actions 빌드/푸시
- ArgoCD ApplicationSet
- manifest 갱신 워크플로우
- 배포 검증 워크플로우

완료 조건:
- push -> 이미지 갱신 -> ArgoCD Sync -> `factory-a` 롤아웃 확인

주요 산출물:
- 공통 차트 구조
- `envs/factory-a/values.yaml`
- GitHub Actions 워크플로우
- `factory-a` end-to-end 배포 흐름

다음 단계로 넘어가는 조건:
- 운영형 Spoke 자동 배포 경로 설명 가능
- 배포 성공 기준(`Sync`, `Healthy`, `Running`) 확인 가능

### Phase 5. M4 데이터 플레인 - `factory-a` 단일 Spoke 기준

선행 조건:
- Phase 3, 4 완료
- `factory-a` Edge Agent 구현 준비

주요 작업:
- 표준 입력 스키마 확정
- Edge Agent 구현 / 컨테이너화
- IoT Core 연결
- S3 적재
- 정규화/판단 서비스
- `pipeline_status` 집계

완료 조건:
- `factory-a` 데이터가 S3까지 실제 적재되고 Hub에서 처리 가능

주요 산출물:
- 표준 입력 스키마
- `factory-a` Edge Agent 이미지/배포 준비
- IoT Core -> S3 경로
- `pipeline-status-aggregator`

다음 단계로 넘어가는 조건:
- `factory-a` 데이터 플레인 end-to-end 검증 가능
- `sensor` / `system_status` 경로가 구분돼 적재됨

### Phase 6. M5 VM Spoke 확장 - `factory-b`, `factory-c`

선행 조건:
- Phase 4, 5 완료
- 운영형 Spoke 배포 및 데이터 플레인 기준선 확인

주요 작업:
- `factory-b` K3s
- `factory-c` K3s
- 두 VM의 Tailscale 참여
- ApplicationSet 확장
- Dummy Sensor 구현 / 배포
- 테스트베드형 자동 롤백 정책 적용
- 두 VM의 S3 적재 및 `pipeline_status` 확인

완료 조건:
- 3개 공장이 Hub에서 독립 공장으로 배포/수집 가능

주요 산출물:
- `factory-b.kubeconfig`
- `factory-c.kubeconfig`
- Dummy Sensor 파드
- 테스트베드형 정책 반영 Application

다음 단계로 넘어가는 조건:
- `factory-a`, `factory-b`, `factory-c` 3개 공장 상태 구분 가능
- 세 공장 모두 S3 적재 및 `pipeline_status` 집계 가능

### Phase 7. M6 Risk Twin + 관제 화면

선행 조건:
- Phase 5, 6 완료
- 3개 공장 데이터가 Hub에서 읽힘

주요 작업:
- Risk Score Engine 구현
- `runtime-config.yaml` 적용
- 온도/습도 기준 초안 반영
- Risk Twin 출력 구조 구현
- Grafana 메인 대시보드 구현

완료 조건:
- 상태 변화 -> Risk Score -> 관제 화면 반영 end-to-end 확인

주요 산출물:
- Risk Score Engine
- Risk Twin 메트릭 구조
- 공장별 위험도 카드
- 센서 현황 / 이상 시스템 / 로그 패널

### Phase 8. M7 통합 검증 및 문서 보정

선행 조건:
- Phase 1~7 완료

주요 작업:
- 운영형 시나리오 검증
- 테스트베드형 시나리오 검증
- Failover 검증
- 롤백 검증
- `docs/ops/test_checklist.md` 보정
- `docs/` 및 `configs/` 기준 문서 최종 갱신

완료 조건:
- 문서와 실제 구현 상태가 일치
- MVP 완료 선언 가능

## 단계별 선행 관계 요약

| 단계 | 선행 조건 | 핵심 산출물 |
| --- | --- | --- |
| Phase 0 | 없음 | 기준 문서 |
| Phase 1 (M0) | 문서 기준선 | Safe-Edge 기준선 |
| Phase 2 (M1) | Phase 1 | Hub 핵심 서비스 |
| Phase 3 (M2) | Phase 2 | Mesh 기반 `factory-a` 연결 |
| Phase 4 (M3) | Phase 3 | 배포 파이프라인 |
| Phase 5 (M4) | Phase 3, 4 | `factory-a` 데이터 플레인 |
| Phase 6 (M5) | Phase 4, 5 | VM Spoke 확장 |
| Phase 7 (M6) | Phase 5, 6 | Risk Twin + 관제 |
| Phase 8 (M7) | Phase 1~7 | 통합 검증 + 문서 보정 |

## 구현 중 테스트로 결정할 항목

- 온도/습도 임계값
- source_type별 지연 기준
- 보존 기간 수치
- Dummy 시나리오 값
- 가중치 보정
- `pipeline_status` 주기 집계 간격
- 배포 지연 시간 수치
- null 허용 정책 세부값

## TODO

- TODO: 각 Phase별 예상 기간 기입
- TODO: 실제 작업 담당자 기입
- TODO: 각 Phase별 실제 산출물 경로 연결
