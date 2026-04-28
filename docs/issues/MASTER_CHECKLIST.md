# Aegis-Pi Master Checklist

상태: working tracker
기준 문서: `docs/issues/M0_factory-a_safe-edge-baseline.md` ~ `docs/issues/M7_integration-test.md`

## 사용 방식

- 이 파일은 진행 추적용 체크리스트다.
- 상세 완료 조건과 Acceptance Criteria는 각 원본 이슈 문서를 기준으로 본다.
- 실제로 끝난 항목만 체크한다.
- 마일스톤 완료 판단은 하위 Issue 전부 완료된 뒤 원본 문서의 완료 기준으로 다시 확인한다.

---

## M0. `factory-a` Safe-Edge 기준선 복구

원본: `docs/issues/M0_factory-a_safe-edge-baseline.md`

- [ ] Issue 1 - [Safe-Edge/OS] Raspberry Pi OS Lite 각 노드 기본 세팅
- [ ] Issue 2 - [Safe-Edge/네트워크] 하드웨어/네트워크 기준선 구성
- [ ] Issue 3 - [Safe-Edge/K3s] 3-Node 클러스터 구성 및 taint/label 적용
- [ ] Issue 4 - [Safe-Edge/MetalLB] MetalLB + Traefik 네트워크 서비스 계층 구성
- [ ] Issue 5 - [Safe-Edge/Longhorn] 3-Node 복제 구성
- [ ] Issue 6 - [Safe-Edge/NFS] Host PC NFS Cold Storage 구성
- [ ] Issue 7 - [배포/ArgoCD] GitLab + ArgoCD GitOps 복구
- [ ] Issue 8 - [관제/Grafana] Prometheus + InfluxDB + Grafana 모니터링 구성
- [ ] Issue 9 - [데이터/BME280] BME280 + 카메라 + 마이크 입력 계층 구성
- [ ] Issue 10 - [Safe-Edge/YOLOv8] YOLOv8 + YAMNet AI 파드 배포 및 Worker-2 배치
- [ ] Issue 11 - [Safe-Edge/Failover] Failover 정책 복구 (tolerationSeconds, affinity)
- [ ] Issue 12 - [자동화/Ansible] Hot/Cold 티어링 + Ansible Playbook 복구
- [ ] Issue 13 - [검증/통합] Safe-Edge 기준선 통합 검증

## M1. Hub 클라우드 기반 구성

원본: `docs/issues/M1_hub-cloud.md`

- [ ] Issue 1 - [Hub/EKS] 클러스터 생성 및 기본 설정
- [ ] Issue 2 - [Hub/Kubernetes] 네임스페이스 설계 및 생성
- [ ] Issue 3 - [Hub/ArgoCD] ArgoCD 설치 (Spoke 등록 전 단계)
- [ ] Issue 4 - [Hub/S3] 버킷 생성 및 경로 파티셔닝 설계
- [ ] Issue 5 - [Hub/IoT Core] Thing / 인증서 / 규칙 구성
- [ ] Issue 6 - [관제/AMP] AMP(Amazon Managed Prometheus) Workspace 생성 및 접근 권한 준비
- [ ] Issue 7 - [관제/Prometheus] Hub Prometheus 설치 및 AMP remote_write 구성
- [ ] Issue 8 - [관제/Grafana] Grafana Hub 설치 및 AMP 데이터 소스 연결
- [ ] Issue 9 - [Risk/Config] `runtime-config.yaml` 파일 구조 초안 작성

## M2. Mesh VPN + Hub-Spoke 연결

원본: `docs/issues/M2_mesh-vpn-hub-spoke.md`

- [ ] Issue 1 - [Mesh/Tailscale] 계정 및 Spoke별 키 발급 정책 수립
- [ ] Issue 2 - [Mesh/Tailscale] `factory-a` Master Tailscale 참여 및 확인
- [ ] Issue 3 - [Mesh/Tailscale] EKS Hub Tailscale 참여 및 확인
- [ ] Issue 4 - [Mesh/Tailscale] kubeconfig Tailscale IP 기반 구성
- [ ] Issue 5 - [배포/ArgoCD] `factory-a` Spoke 클러스터 등록
- [ ] Issue 6 - [검증/ArgoCD] Hub -> `factory-a` K3s API 접근 및 Sync 확인

## M3. 배포 파이프라인

원본: `docs/issues/M3_deploy-pipeline.md`

- [ ] Issue 1 - [배포/Helm] GitHub 저장소 구조 설계 (베이스 + 공장별 values)
- [ ] Issue 2 - [배포/ECR] 저장소 구성 및 이미지 태그 전략
- [ ] Issue 3 - [배포/GitHub Actions] 빌드/푸시 워크플로우 구성
- [ ] Issue 4 - [배포/ArgoCD] ApplicationSet 구성 (`factory-a` 기준)
- [ ] Issue 5 - [배포/ArgoCD] 운영형 동기화 정책 및 롤백 정책 적용
- [ ] Issue 6 - [배포/GitHub Actions] manifest 갱신 워크플로우 구성
- [ ] Issue 7 - [배포/GitHub Actions] 배포 검증 워크플로우 구성
- [ ] Issue 8 - [검증/ArgoCD] `factory-a` end-to-end 배포 검증

## M4. 데이터 플레인 - `factory-a` 단일 Spoke 기준

원본: `docs/issues/M4_data-plane.md`

- [ ] Issue 1 - [데이터/Schema] 표준 입력 스키마 확정
- [ ] Issue 2 - [데이터/Edge Agent] `factory-a` Edge Agent 수집/변환 로직 구현
- [ ] Issue 3 - [데이터/Container] `factory-a` Edge Agent 컨테이너화 및 K3s 배포 준비
- [ ] Issue 4 - [데이터/IoT Core] Edge Agent -> IoT Core 연결 및 수신 확인
- [ ] Issue 5 - [데이터/S3] IoT Core -> S3 적재 확인 (경로 파티셔닝 포함)
- [ ] Issue 6 - [데이터/정규화] EKS 내부 정규화/판단 서비스 구현
- [ ] Issue 7 - [데이터/Pipeline] `pipeline_status` 주기 집계 구현 (`ops-support`)
- [ ] Issue 8 - [검증/데이터] `factory-a` 데이터 플레인 end-to-end 검증

## M5. VM Spoke 확장 - `factory-b`, `factory-c`

원본: `docs/issues/M5_vm-spoke-expansion.md`

- [ ] Issue 1 - [Spoke/K3s] Mac mini VM K3s 구성 (`factory-b`)
- [ ] Issue 2 - [Spoke/K3s] Windows VM K3s 구성 (`factory-c`)
- [ ] Issue 3 - [Spoke/Tailscale] `factory-b`, `factory-c` Tailscale 참여 및 Hub 연결
- [ ] Issue 4 - [배포/ArgoCD] ApplicationSet에 `factory-b`, `factory-c` 추가
- [ ] Issue 5 - [Spoke/Dummy Sensor] Dummy Sensor 모듈 구현 및 배포
- [ ] Issue 6 - [배포/ArgoCD] 테스트베드형 동기화 정책 및 자동 롤백 적용
- [ ] Issue 7 - [검증/데이터] `factory-b`, `factory-c` 데이터 플레인 연결 확인

## M6. Risk Twin + 관제 화면

원본: `docs/issues/M6_risk-twin-dashboard.md`

- [ ] Issue 1 - [Risk/Engine] Risk Score Engine 구현 (가중치 초기안)
- [ ] Issue 2 - [Risk/Config] `runtime-config.yaml` 전역 설정 적용 및 필드 제어 구현
- [ ] Issue 3 - [Risk/Config] 온도/습도 이상 기준값 초안 적용
- [ ] Issue 4 - [Risk/Twin] Risk Twin 출력 구조 구현
- [ ] Issue 5 - [관제/Grafana] 메인 대시보드 - 공장별 위험도 카드
- [ ] Issue 6 - [관제/Grafana] 메인 대시보드 - 센서 현황 + 이상 시스템 목록
- [ ] Issue 7 - [관제/Grafana] 메인 대시보드 - 하단 이벤트/상태 변화 로그
- [ ] Issue 8 - [검증/Risk] 시나리오별 Risk Score 변화 확인

## M7. 통합 검증

원본: `docs/issues/M7_integration-test.md`

- [ ] Issue 1 - [검증/운영형] `factory-a` 운영형 시나리오 검증
- [ ] Issue 2 - [검증/테스트베드] `factory-b`, `factory-c` 테스트베드형 시나리오 검증
- [ ] Issue 3 - [검증/Failover] Failover 시나리오 (Worker-2 장애 -> Worker-1 승계 -> Hub 반영)
- [ ] Issue 4 - [검증/ArgoCD] 배포 파이프라인 롤백 시나리오
- [ ] Issue 5 - [검증/Test Checklist] `docs/ops/03_test_checklist.md` 전수 보정
- [ ] Issue 6 - [문서화/Docs] `docs/` 및 `configs/` 기준 문서 최종 갱신
