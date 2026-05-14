# Issue Docs

이 디렉터리는 Aegis-Pi 구현 마일스톤과 작업 단위를 추적하는 문서를 둔다.

## 파일

| 파일 | 내용 |
| --- | --- |
| `MASTER_CHECKLIST.md` | M0~M7 전체 진행 상태 요약 체크리스트 |
| `SESSION_STATE.md` | 현재 세션을 이어받기 위한 상태 스냅샷 |
| `M0_factory-a_safe-edge-baseline.md` | `factory-a` Safe-Edge 기준선 복구 작업 |
| `M1_hub-cloud.md` | AWS Hub, EKS, IoT Core, S3, AMP 기준 작업 |
| `M2_mesh-vpn-hub-spoke.md` | Tailscale 기반 Hub-Spoke 연결 작업 |
| `M3_deploy-pipeline.md` | GitHub Actions, ECR, ArgoCD 기반 배포 파이프라인 |
| `M4_data-plane.md` | Edge Agent, IoT Core, S3 데이터 플레인 |
| `M5_vm-spoke-expansion.md` | `factory-b`, `factory-c` VM Spoke 확장 |
| `M6_risk-twin-dashboard.md` | Lambda Risk 계산 로직과 관제 화면 |
| `M7_integration-test.md` | 전체 통합 검증 시나리오 |
| `edit.md` | 이슈 문서 보강 메모와 수정 방향 |

## 기준

- 실제 완료 여부는 `MASTER_CHECKLIST.md`와 각 마일스톤 문서를 함께 확인한다.
- 새 작업을 시작하기 전 `SESSION_STATE.md`의 다음 작업을 확인한다.
- 각 마일스톤 issue 문서를 수정할 때는 문서 상단부에 `수정 이력`을 남긴다.
- 수정 이력은 날짜, 수정 버전, 수정 요약만 간단히 기록한다.
- 각 GitHub issue 단위 작업을 진행하거나 완료하면 해당 issue 섹션 아래에 `GitHub Issue Comment Draft`를 남긴다.
- `GitHub Issue Comment Draft`는 실제 GitHub issue comment로 옮겨 적기 위한 짧은 진행 기록이다.
- comment draft는 코드, 스크립트, Terraform, Ansible, 문서 변경을 확인한 뒤 작성한다.
- 민감 정보, 비밀번호, 토큰, 인증서 private key, MFA OTP, 세션 토큰, 전체 ARN 이상의 불필요한 계정 세부정보는 comment draft에 남기지 않는다.
- 보류/미완료 이슈도 판단이 바뀌면 `상태`, `진행 요약`, `후속`을 짧게 남긴다.
- 초기 버전 확인이 필요하면 Git history에서 수정 이력 이전 버전을 확인한다.
- `SESSION_STATE.md`는 현재 상태 스냅샷이므로 누적 수정 이력을 남기지 않는다.

수정 이력 예:

```text
## 수정 이력

| 날짜 | 버전 | 내용 |
| --- | --- | --- |
| YYYY-MM-DD | rev-YYYYMMDD-XX | 수정 요약 |
```

## GitHub Issue Comment Draft 작성 규칙

각 issue 섹션 아래에 아래 형식을 추가하거나 최신 내용으로 갱신한다.

```text
### GitHub Issue Comment Draft

- 상태: 완료 / 부분 완료 / 보류 / 진행 중
- 진행 요약: 무엇을 어떤 방향으로 처리했는지 1~2문장
- 변경/확인: 주요 파일, 스크립트, Terraform/Ansible root, 운영 문서
- 검증: 실행한 명령, 확인한 상태, 테스트 결과
- 후속: 남은 작업이 없으면 `없음`, 있으면 다음 issue 또는 보류 사유
```

자동 기록 기준:

1. 작업 시작 전 대상 issue 문서와 관련 코드/문서를 확인한다.
2. 변경 후 `git diff --stat`, 관련 파일 내용, 검증 결과를 기준으로 comment draft를 작성한다.
3. 이미 같은 issue에 comment draft가 있으면 최신 진행 내용이 드러나도록 보강하되, 오래된 세부 로그를 길게 누적하지 않는다.
4. GitHub에 실제 comment를 남긴 뒤에도 이 문서의 draft는 유지한다.
