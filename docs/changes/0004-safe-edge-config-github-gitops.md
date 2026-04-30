# 0004. GitOps Source: Local Repo -> GitHub Repo + ArgoCD UI Sync

상태: accepted
결정일: 2026-04-28
관련 범위: M0 factory-a, deployment, GitOps

## 기존 계획

초기 작업 중에는 로컬 `safe-edge-config-main` 디렉터리를 기준으로 manifest와 chart를 관리한다.

## 변경된 실제 기준

`factory-a` Safe-Edge 배포 기준은 GitHub repository다.

```text
https://github.com/aegis-pi/safe-edge-config-main.git
```

ArgoCD Application은 아래 두 개로 분리한다.

```text
safe-edge-monitoring
safe-edge-ai-apps
```

Repository 등록과 sync는 ArgoCD UI에서 수행한다.

## 변경 이유

M0 이후 AWS Hub, ApplicationSet, GitHub Actions, ECR 기반 배포 파이프라인으로 확장하려면 GitHub repository가 기준점이어야 한다.

로컬 디렉터리 기준은 단일 장비 작업에는 편하지만, ArgoCD와 후속 자동화의 source of truth로 쓰기 어렵다.

## 영향

- GitHub push 후 ArgoCD refresh/sync로 `factory-a`에 반영한다.
- `monitoring`과 `ai-apps`를 Application 단위로 분리해 상태와 sync 범위를 나눈다.
- 후속 M3 배포 파이프라인은 같은 GitHub 기준을 이어받는다.

## 업데이트 필요한 문서

- `docs/issues/M0_factory-a_safe-edge-baseline.md`
- `docs/ops/06_argocd_gitops.md`
- `docs/architecture/00_current_architecture.md`
- `README.md`

## 검증

- GitHub repository push 완료
- ArgoCD `safe-edge-monitoring` Synced / Healthy 확인
- ArgoCD `safe-edge-ai-apps` Synced / Healthy 확인
- GitHub revision 변경 후 ArgoCD sync로 리소스 반영 확인
