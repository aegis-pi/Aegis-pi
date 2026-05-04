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
| `M6_risk-twin-dashboard.md` | Risk Score Engine과 관제 화면 |
| `M7_integration-test.md` | 전체 통합 검증 시나리오 |
| `edit.md` | 이슈 문서 보강 메모와 수정 방향 |

## 기준

- 실제 완료 여부는 `MASTER_CHECKLIST.md`와 각 마일스톤 문서를 함께 확인한다.
- 새 작업을 시작하기 전 `SESSION_STATE.md`의 다음 작업을 확인한다.
- 각 마일스톤 issue 문서를 수정할 때는 문서 상단부에 `수정 이력`을 남긴다.
- 수정 이력은 날짜, 수정 버전, 수정 요약만 간단히 기록한다.
- 초기 버전 확인이 필요하면 Git history에서 수정 이력 이전 버전을 확인한다.
- `SESSION_STATE.md`는 현재 상태 스냅샷이므로 누적 수정 이력을 남기지 않는다.

수정 이력 예:

```text
## 수정 이력

| 날짜 | 버전 | 내용 |
| --- | --- | --- |
| YYYY-MM-DD | rev-YYYYMMDD-XX | 수정 요약 |
```
