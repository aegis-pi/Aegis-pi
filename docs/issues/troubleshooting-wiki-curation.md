# Troubleshooting Wiki Curation

상태: 완료
기준일: 2026-05-26
원본: `docs/ops/04_troubleshooting.md`, `docs/ops/21_build_all_admin_ui_troubleshooting.md`, Hub/Cloud 관련 운영 문서
산출물: `docs/wiki/troubleshooting/`

## 목적

`docs/ops/04_troubleshooting.md`와 Hub/Cloud 운영 문서에 누적된 트러블슈팅 중 Git Wiki에 남길 가치가 있는 항목을 선별하고, GitHub Issue 템플릿에 맞는 리포트 형식으로 정리한다.

이 체크리스트는 이후 새 트러블슈팅이 원본 문서에 추가됐을 때, 어디까지 Wiki/Issue 정리가 끝났는지 구분하기 위한 기준선이다. `04_troubleshooting.md`의 완료선은 해당 파일에만 적용하고, Cloud/AWS Hub 항목은 별도 체크 섹션으로 관리한다.

## 정리 완료 기준선

`docs/ops/04_troubleshooting.md` 마지막의 아래 표시 위에 있는 항목은 정리 완료로 본다.

```text
이 선 위 트러블슈팅 항목은 Git Wiki / Issue 리포트 정리 완료
```

## 완료 체크

- [x] Git Wiki 포함 대상 선별
- [x] 트러블슈팅 리포트 템플릿 필드 적용
- [x] 카테고리별 Wiki 문서 생성
- [x] 문서 인덱스 연결
- [x] 원본 troubleshooting 문서에 정리 완료 기준선 추가

## 정리 완료 항목

### OS / Raspberry Pi

- [x] cgroup 설정 확인 중 `cgroup_disable=memory` 표시
- [x] I2C 장치 파일 없음

### K3s / Kubernetes

- [x] K3s master INTERNAL-IP Wi-Fi 대역 오인식
- [x] Longhorn manager master 배치 누락
- [x] 원격 비대화형 SSH에서 `i2cdetect` 명령 PATH 누락

### Storage / Longhorn

- [x] Longhorn 데이터 경로 없음
- [x] Longhorn KernelModulesLoaded 조건 False
- [x] Longhorn LoadBalancer Service 삭제 지연
- [x] Longhorn RWO PVC로 인한 AI failover 차단

### LoadBalancer / MetalLB

- [x] K3s ServiceLB와 MetalLB 역할 충돌
- [x] Longhorn UI LoadBalancer 노출 필요
- [x] K3s ServiceLB에서 MetalLB 전환 이슈
- [x] MetalLB IP 충돌과 어노테이션 충돌
- [x] Grafana IP와 Traefik IP 충돌 위험

### Monitoring / DB

- [x] Grafana PVC 권한 문제
- [x] InfluxDB retention policy 1일 설정 중 shard duration 오류
- [x] AI 이벤트 스냅샷 보존 기간 혼동

### AI / Hardware

- [x] 하드웨어 의존 Pod RollingUpdate 갱신 충돌
- [x] `safe-edge-integrated-ai` ai_detection 미기록 문제

### Automation / Script

- [x] K3s 설치 중 `curl | sudo -S` 비밀번호 입력 실패
- [x] ai-apps 배포 중 대용량 이미지 pull 지연
- [x] `argocd --core` argocd-cm ConfigMap 조회 실패
- [x] Hub 재생성 후 build/register 스크립트 선택 혼동
- [x] `manage-dummy-generators.sh` 권한, 원격 shell, 서비스 상태 혼동

### Operations / DR

- [x] Kubernetes CronJob 기반 Failback 재생성 루프 위험
- [x] latest 이미지 pull로 인한 Pod 복구 실패
- [x] 랜선 제거 테스트 상태 판정 오류 위험

### Network

- [x] worker2 k3s-agent flannel/default route 기동 실패
- [x] `start_test.yml` Tailscale 검증 실패와 master `wlan0` 인터넷 단절
- [x] worker1 `eth0` IPv4 미할당과 NetworkManager connection profile 삭제 후 단절
- [x] factory-a `eth0`/`wlan0` 역할 고정과 `/24` 정상화 접근 경로 변경

### Cloud / AWS Hub

- [x] MFA helper sandbox 파일 쓰기와 AWS STS 접근 실패
- [x] EKS CloudWatch Log Group 중복 생성 실패
- [x] EC2 Security Group read-after-write UnknownError
- [x] IAM ListRolePolicies timeout
- [x] CloudWatch ListTagsForResource timeout
- [x] ArgoCD Helm 설치 중 EKS API 연결 손실
- [x] Helm http2 client connection loss 반복
- [x] ACM ISSUED 전 Admin Ingress 활성화 위험
- [x] ArgoCD smoke app ARM64 exec format error
- [x] Tailscale egress 삭제로 인한 ArgoCD sync 실패
- [x] IoT Rule S3 raw 적재 실패
- [x] factory-c Flannel DNS/MQTT 연결 실패
- [x] 엣지 서버와 클라우드간 시각 비동기화
- [x] Factory-A ECR pull secret 만료로 adapter rollout 실패
- [x] Lambda stale bytecode로 processed schema 변경 미반영
- [x] 중복 KJW IoT Rule이 processed 결과를 덮어씀

## GitHub Issue Comment Draft

- 상태: 완료
- 진행 요약: `docs/ops/04_troubleshooting.md`와 Hub/Cloud 운영 문서의 Git Wiki 포함 대상 트러블슈팅 44개를 10개 카테고리 문서로 재구성했다. 이후 추가되는 원본 문서 항목을 구분하기 위해 원본 troubleshooting 마지막에 정리 완료 기준선을 추가했다.
- 변경/확인: `docs/wiki/troubleshooting/`, `docs/wiki/README.md`, `docs/issues/troubleshooting-wiki-curation.md`, `docs/issues/MASTER_CHECKLIST.md`, `docs/issues/README.md`, `docs/ops/04_troubleshooting.md`
- 검증: 리포트 제목 목록과 필수 섹션 개수를 grep으로 확인했다.
- 후속: 기준선 아래에 새 트러블슈팅이 추가되면 다음 정리 대상 issue로 분리한다.

2026-05-27 추가 정리:

- Factory-A ECR pull secret 만료로 adapter rollout 실패
- Lambda stale bytecode로 processed schema 변경 미반영
- 중복 KJW IoT Rule이 processed 결과를 덮어씀
