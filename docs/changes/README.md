# Change Records

상태: source of truth
기준일: 2026-04-30

## 목적

이 디렉터리는 초기 계획과 실제 구현/운영 기준이 달라진 결정을 추적한다.

운영 문서는 현재 기준을 설명하고, 변경 기록은 왜 계획이 바뀌었는지와 어떤 영향을 남겼는지 설명한다.

## 기록 기준

- 계획과 실제 구현이 달라진 경우 기록한다.
- 장애 테스트, 운영 안정성, 보안, 비용, 보존 정책에 영향을 주는 변경은 반드시 기록한다.
- 단순 오탈자나 문서 표현 보정은 기록하지 않는다.
- SSH 비밀번호, token, certificate private key 같은 민감 정보는 기록하지 않는다.

## 목록

| ID | 제목 | 상태 | 결정일 | 영향 범위 |
| --- | --- | --- | --- | --- |
| 0001 | AI snapshot storage: Longhorn PVC -> node-local hostPath | accepted | 2026-04-29 | M0, ai-apps, failover |
| 0002 | Failback controller: Kubernetes CronJob -> master OS cron | accepted | 2026-04-29 | M0, failback |
| 0003 | NFS cold storage and hot/cold tiering deferred | accepted | 2026-04-29 | M0, data retention |
| 0004 | GitOps source: local repo -> GitHub repo + ArgoCD UI sync | accepted | 2026-04-28 | M0, deployment |

## 파일 형식

각 변경 기록은 아래 항목을 가진다.

```text
기존 계획
변경된 실제 기준
변경 이유
영향
업데이트 필요한 문서
검증
```
