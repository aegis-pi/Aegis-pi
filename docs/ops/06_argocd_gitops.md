# ArgoCD GitOps 운영

상태: source of truth
기준일: 2026-04-29

## 목적

`factory-a`의 GitOps 배포 방식을 정리한다.

## 현재 방식

```text
GitHub repo -> ArgoCD Application -> K3s cluster
```

GitHub repo:

```text
https://github.com/aegis-pi/safe-edge-config-main.git
```

Application:

```text
safe-edge-monitoring
safe-edge-ai-apps
```

## 운영 원칙

- ArgoCD 설치는 Helm으로 한다.
- GitHub repo 등록은 ArgoCD UI에서 진행한다.
- sync도 사용자가 UI에서 확인하고 진행한다.
- monitoring과 ai-apps는 별도 Application으로 분리한다.
- 민감 정보는 repo에 기록하지 않는다.
- ArgoCD 자체는 worker1에 배치한다. ArgoCD가 worker에 있어도 실제 Deployment 갱신과 Pod scheduling은 master의 Kubernetes control-plane이 수행한다.
- ArgoCD resource requests/limits와 worker1 nodeAffinity는 Helm release values로 관리한다.

## ArgoCD 자체 배치

```text
Helm release: argocd
namespace: argocd
chart: argo/argo-cd 9.5.4
nodeAffinity: worker1 required
```

Resource 기준:

```text
application-controller:       request 100m / 256Mi, limit 500m / 512Mi
repo-server:                  request 100m / 128Mi, limit 500m / 512Mi
server:                       request 50m / 128Mi,  limit 300m / 384Mi
dex-server:                   request 50m / 128Mi,  limit 300m / 384Mi
redis:                        request 50m / 64Mi,   limit 300m / 256Mi
applicationset-controller:    request 50m / 64Mi,   limit 300m / 256Mi
notifications-controller:     request 25m / 64Mi,   limit 200m / 256Mi
```

확인:

```bash
kubectl -n argocd get pod -o wide
kubectl -n argocd top pod --containers
```

## 상태 확인

```bash
kubectl -n argocd get application -o wide
kubectl -n argocd get application safe-edge-monitoring -o yaml
kubectl -n argocd get application safe-edge-ai-apps -o yaml
```

정상 기준:

```text
SYNC STATUS: Synced
HEALTH STATUS: Healthy
REVISION: GitHub 최신 commit
```

## 배포 흐름

```text
1. safe-edge-config-main 수정
2. helm template 로컬 검증
3. git commit
4. git push
5. ArgoCD UI refresh
6. ArgoCD UI sync
7. kubectl로 리소스 확인
```

## Helm 검증

아래 명령은 `safe-edge-config-main` GitHub repository를 clone한 작업 디렉터리의 repository root에서 실행한다. Aegis-pi 문서에는 특정 사용자 PC의 절대 경로를 기록하지 않는다.

```bash
helm template safe-edge-monitoring monitoring
helm template safe-edge-ai-apps ai-apps
```

## Sync 후 확인

```bash
kubectl -n monitoring get pod -o wide
kubectl -n ai-apps get pod -o wide
kubectl -n monitoring get pvc
kubectl -n ai-apps get pvc
```

## 주의

- 자동 sync가 켜져 있지 않으면 push만으로 클러스터가 바뀌지 않는다.
- ArgoCD Application revision을 반드시 확인한다.
- repo credential과 등록은 UI에서 관리한다.
