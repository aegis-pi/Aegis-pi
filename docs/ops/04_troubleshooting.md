# 트러블슈팅

상태: source of truth
기준일: 2026-04-28

## 목적

`factory-a` 구축과 검증 과정에서 실제로 겪은 문제를 번호 기반으로 정리한다.

## 사용 형식

각 항목은 아래 형식을 따른다.

```text
증상
원인
확인 명령
해결/판단
재발 방지
```

## 1. ArgoCD Application이 새 Git commit을 바로 반영하지 않음

증상:
- GitHub repo에 push가 끝났는데 ArgoCD Application revision이 이전 commit에 머문다.
- 새 PVC나 새 container가 클러스터에 생성되지 않는다.

원인:
- 현재 Application은 자동 sync가 설정되어 있지 않다.
- UI refresh/sync 또는 Application operation sync가 필요하다.

확인 명령:

```bash
kubectl -n argocd get application safe-edge-ai-apps -o wide
kubectl -n argocd get application safe-edge-monitoring -o wide
```

해결/판단:
- ArgoCD UI에서 Refresh 후 Sync한다.
- CLI가 없으면 Kubernetes API로 Application sync operation을 넣을 수 있다.

재발 방지:
- repo push 후 ArgoCD UI에서 revision과 health를 반드시 확인한다.

## 2. ArgoCD repo 등록과 sync 위치 혼동

증상:
- GitHub URL을 어디에 넣어야 하는지 혼동한다.
- manifest는 push했지만 Application이 repo를 바라보지 않는다.

원인:
- repo 등록은 사용자가 ArgoCD UI에서 진행하는 운영 방식으로 정했다.

확인 명령:

```bash
kubectl -n argocd get application -o wide
```

해결/판단:
- repo URL은 `https://github.com/aegis-pi/safe-edge-config-main.git`를 사용한다.
- Application은 `safe-edge-monitoring`, `safe-edge-ai-apps`로 분리한다.

재발 방지:
- repo 등록, credential, sync는 UI 절차로 문서화한다.

## 3. Git push 시 github.com DNS resolve 실패

증상:
- `git push`가 `Could not resolve host: github.com`으로 실패한다.

원인:
- 로컬 실행 환경의 네트워크 제한 또는 DNS 접근 제한.

확인 명령:

```bash
git remote -v
git push
```

해결/판단:
- 네트워크 권한이 있는 환경에서 다시 push한다.
- 현재 `safe-edge-config-main`과 `Aegis-pi` 모두 push 완료 이력이 있다.

재발 방지:
- push 실패 시 commit은 유지되므로 네트워크 복구 후 재시도한다.

## 4. InfluxDB subquery ORDER BY 방향 오류

증상:
- Grafana 또는 InfluxDB query에서 `subqueries must be ordered in the same direction as the query itself` 오류가 난다.

원인:
- 내부 query는 `ORDER BY time DESC LIMIT 10`인데 외부 집계 또는 Grafana 처리 방향과 충돌한다.

확인 명령:

```sql
SELECT "fire_detected"
FROM "ai_detection"
WHERE $timeFilter
ORDER BY time DESC
LIMIT 10
```

해결/판단:
- Grafana panel query에는 raw query를 직접 넣고, 최근 N개 평균은 panel Transform 또는 query 구조를 맞춰 처리한다.
- InfluxQL subquery를 쓸 때는 내부/외부 정렬 방향을 맞춘다.

재발 방지:
- 최근 N개 평균 panel은 `docs/ops/07_grafana_dashboard.md`의 쿼리 기준을 따른다.

## 5. Grafana에 최근 10개 AI 값을 넣는 위치 혼동

증상:
- `SELECT ... ORDER BY time DESC LIMIT 10`을 Grafana 어디에 넣어야 하는지 혼동한다.

원인:
- Grafana panel의 Query 영역과 Transform/Calculation 영역 역할이 다르다.

확인 명령:
- Grafana panel edit에서 Query 탭을 연다.

해결/판단:
- Query 영역에 최근 10개 raw 값을 가져오는 InfluxQL을 넣는다.
- 평균/마지막값/상태 표시는 Transform 또는 Reduce calculation에서 처리한다.

재발 방지:
- Dashboard 등록은 UI에서 진행하되, query와 value mapping은 문서의 panel별 기준을 사용한다.

## 6. Grafana 0/1 값을 안전/주의/위험으로 바꾸는 방법

증상:
- 화재/넘어짐/굽힘/소리 결과가 0 또는 1로만 보인다.

원인:
- AI 결과 원본은 binary 값이고, 운영 화면은 최근 N개 평균을 상태로 해석해야 한다.

확인 명령:

```sql
SELECT "fire_detected" FROM "ai_detection" WHERE $timeFilter ORDER BY time DESC LIMIT 10
```

해결/판단:
- 최근 N개 평균을 계산한다.
- 값 범위는 아래처럼 매핑한다.

```text
0.0-0.2: 안전
0.3-0.7: 주의
0.8-1.0: 위험 레이블
```

재발 방지:
- N 값은 panel query의 `LIMIT 10` 숫자로 조정한다.

## 7. InfluxDB retention policy와 Longhorn replica 보존 범위 혼동

증상:
- InfluxDB에서 1일 지난 데이터를 삭제하면 Longhorn replica에도 남는지 혼동한다.

원인:
- Longhorn은 블록 스토리지 복제이고, 데이터 보존 정책은 InfluxDB가 결정한다.

확인 명령:

```bash
kubectl -n monitoring exec deploy/influxdb -- \
  influx -execute 'SHOW RETENTION POLICIES ON safe_edge_db'
```

해결/판단:
- InfluxDB retention이 1일이면 Longhorn replica도 삭제 후의 DB 상태를 복제한다.

재발 방지:
- 데이터 보존 기간은 Longhorn이 아니라 InfluxDB retention policy로 관리한다.

## 8. worker2에 이미 정상 Pod가 있는데 failback cron이 Pod를 죽일 위험

증상:
- worker2에 이미 대상 Pod가 Running인데 failback cron이 worker1 Pod를 삭제하며 정상 Pod까지 흔들 수 있다.

원인:
- worker2 대상 Pod 존재 여부를 먼저 확인하지 않으면 정상 Pod를 건드릴 수 있다.

확인 명령:

```bash
kubectl -n ai-apps get pod -o wide
kubectl -n monitoring get pod -o wide
```

해결/판단:
- worker2에 대상 Pod가 있으면 failback cron은 skip해야 한다.
- worker1에 남은 대상 Pod만 순차적으로 삭제한다.

재발 방지:
- failback script의 첫 조건은 `worker2 Ready`와 `worker2 대상 Pod 존재 여부`다.

## 9. Kubernetes CronJob 방식 failback이 하드웨어 연결 작업에서 불안정했던 문제

증상:
- CronJob이 Pod를 worker2로 돌리려 하지만 하드웨어 연결이 불안정하면 Pod가 계속 재생성되어 시스템이 멈춘다.

원인:
- 하드웨어 의존 워크로드를 Kubernetes CronJob으로 강제 이동하면 재시작 루프가 발생할 수 있다.

확인 명령:

```bash
kubectl -n ai-apps get pod -o wide
kubectl -n ai-apps describe pod <pod-name>
```

해결/판단:
- Kubernetes CronJob 대신 master OS cron에서 `kubectl`만 실행하는 Kubernetes-only 스크립트를 사용한다.

재발 방지:
- worker2가 Ready이고 기존 worker2 Pod 상태가 안전할 때만 worker1 Pod를 삭제한다.

## 10. preferred affinity만으로 자동 failback이 즉시 일어나지 않음

증상:
- worker2가 복구되어도 Pod가 자동으로 worker2로 바로 돌아오지 않는다.

원인:
- `preferredDuringSchedulingIgnoredDuringExecution`은 선호 조건이다.
- 이미 worker1에서 Running인 Pod를 Kubernetes가 즉시 옮기지는 않는다.

확인 명령:

```bash
kubectl -n ai-apps get pod -o wide
kubectl -n monitoring get pod -o wide
```

해결/판단:
- master OS cron이 worker2 Ready를 확인한 뒤 worker1에 남은 대상 Pod를 순차 삭제한다.

재발 방지:
- 자동 failback은 scheduler 기본 동작이 아니라 운영 자동화 정책으로 본다.

## 11. LAN 제거 테스트의 InfluxDB 데이터 공백 산정

증상:
- worker2 LAN 제거 중 InfluxDB 데이터 공백이 얼마나 발생했는지 산정해야 한다.

원인:
- worker2가 NotReady로 전환되고 worker1 Pod가 Running될 때까지 write가 끊길 수 있다.
- 1초 bucket은 세부 공백을 잘 보여주지만, BME처럼 샘플 주기가 1초보다 긴 데이터는 평상시에도 0-count가 섞인다.

확인 명령:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(10s) fill(0)
```

해결/판단:
- 10초 bucket과 1초 bucket을 함께 본다.
- 2026-04-29 test_09 LAN 제거 테스트에서는 다음과 같이 기록했다.

```text
1초 bucket 최대 연속 0-count:
ai_detection:        87초
acoustic_detection:  90초
environment_data:    83초

10초 bucket 운영 기준 0-count:
ai_detection:        80초
acoustic_detection:  80초
environment_data:    70초
```

재발 방지:
- 장애 분석은 항상 10초 bucket과 1초 bucket을 같이 남긴다.
- 운영 판단은 10초 bucket 기준을 우선 사용한다.

## 12. 전원 제거 테스트에서 1초 bucket 공백 산정 방법

증상:
- 1초 단위로 봤을 때 실제 공백이 몇 초인지 따로 계산해야 한다.

원인:
- zero bucket 개수와 연속 zero bucket 길이는 다르다.

확인 명령:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(1s) fill(0)
```

해결/판단:
- 연속 zero-count 최대 길이 기준으로 산정했다.

```text
failover environment_data: 최대 65초
failover ai_detection: 최대 72초
failover acoustic_detection: 최대 75초
failback 각 항목: 최대 2초
```

재발 방지:
- 결과 문서에는 zero bucket 총합과 최대 연속 공백을 분리해 기록한다.

## 13. Longhorn volume degraded가 worker2 복구 후 일시적으로 발생

증상:
- worker2 전원 복구 직후 Longhorn volume이 degraded로 보인다.

원인:
- worker2 전원 차단 동안 replica가 끊기고, 복구 후 재동기화가 필요하다.

확인 명령:

```bash
kubectl -n longhorn-system get volumes.longhorn.io -o wide
```

해결/판단:
- 전원 제거 테스트에서 degraded 후 healthy 복귀를 확인했다.

재발 방지:
- failback 완료 판단은 Pod Running뿐 아니라 Longhorn healthy까지 함께 본다.

## 14. safe-edge-image-prepull DaemonSet의 의미

증상:
- DaemonSet으로 이미지를 미리 받는다는 의미가 혼동된다.

원인:
- failover 시 worker1이 큰 이미지를 처음 pull하면 복구 시간이 길어질 수 있다.

확인 명령:

```bash
kubectl -n ai-apps get ds safe-edge-image-prepull -o wide
kubectl -n ai-apps describe ds safe-edge-image-prepull
```

해결/판단:
- worker1/worker2에 AI/Audio 이미지를 미리 pull해 failover 시 이미지 다운로드 지연을 줄인다.

재발 방지:
- 새 이미지 태그를 배포하면 prepull DaemonSet의 image도 같은 태그로 갱신한다.

## 15. AI 이벤트 이미지가 Pod 내부 /app/snapshots에만 저장되던 문제

증상:
- AI 감지 이미지는 `/app/snapshots`에 저장되지만 Pod 재생성 시 사라질 수 있다.

원인:
- 기존에는 `/app/snapshots`가 PVC가 아니라 컨테이너 내부 파일시스템이었다.

확인 명령:

```bash
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c ai-processor -- ls -lah /app/snapshots
```

해결/판단:
- 현재 운영 구성에서는 `/app/snapshots`를 node-local `/var/lib/safe-edge/snapshots` hostPath로 mount한다.
- AI 추론 결과는 InfluxDB를 통해 Longhorn에 저장한다.

재발 방지:
- AI snapshot 경로는 hostPath mount 여부를 함께 확인한다.

## 16. AI snapshot 저장 방식 변경 후 기존 이미지가 자동 이관되지 않음

증상:
- hostPath 전환 후 `/app/snapshots`가 비어 보일 수 있다.

원인:
- 기존 이미지는 이전 Pod 컨테이너 내부 layer 또는 과거 Longhorn PVC에 있었고, 새 node-local hostPath로 자동 복사되지 않는다.

확인 명령:

```bash
kubectl -n ai-apps get pod -l app=safe-edge-integrated-ai -o wide
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c ai-processor -- mount | grep snapshots
```

해결/판단:
- 기존 임시 이미지는 보존 대상이 아니면 이관하지 않는다.
- 앞으로 생성되는 이미지는 해당 Pod가 실행 중인 노드의 local path에 저장된다.

재발 방지:
- 저장 방식 변경 전 임시 이미지 보존이 필요하면 별도 백업 절차를 먼저 수행한다.

## 17. AI snapshot을 24시간 초과 저장하지 않게 하는 방식

증상:
- 이미지 증거를 저장해야 하지만 장기 보존은 피해야 한다.

원인:
- AI event image는 node-local hostPath에 저장되므로 별도 cleanup이 없으면 각 노드 디스크에 계속 누적된다.

확인 명령:

```bash
kubectl -n ai-apps get pod -l app=safe-edge-integrated-ai -o jsonpath='{.items[0].spec.containers[*].name}{"\n"}'
kubectl -n ai-apps exec deploy/safe-edge-integrated-ai -c snapshot-cleanup -- ps
```

해결/판단:
- `snapshot-cleanup` sidecar가 `/app/snapshots`에서 24시간 초과 jpg/jpeg/png 파일을 삭제한다.

재발 방지:
- retention은 `ai-apps/values.yaml`의 `snapshotStorage.retentionHours`로 관리한다.

## 18. cron에 비밀번호가 필요하다는 오해

증상:
- failback cron이 worker2에 SSH 접속하려면 비밀번호가 필요한지 혼동한다.

원인:
- 테스트 중 SSH 접근은 상태 확인용이었고, 실제 failback은 master에서 Kubernetes API로만 처리한다.

확인 명령:

```bash
crontab -l
kubectl get nodes
```

해결/판단:
- 실제 cron에는 worker2 SSH 비밀번호가 필요 없다.
- master에서 `kubectl` 명령만 사용한다.

재발 방지:
- failback 방식은 Kubernetes-only로 문서화한다.

## 19. worker2가 Ready로 보여도 첫 5분은 판정하지 않는 이유

증상:
- 장애 직후 worker2가 Ready처럼 보이면 failback 성공으로 판단할 수 있다.

원인:
- Kubernetes node/pod 상태는 물리 단절 직후 지연되어 보일 수 있다.

확인 명령:

```bash
kubectl get nodes -o wide
kubectl -n ai-apps get pod -o wide
```

해결/판단:
- 장애 시작 후 최소 5분은 판정 보류한다.
- 그 후 재연결/복구 단계를 진행한다.

재발 방지:
- 테스트 절차에 초기 5분 판정 보류를 고정한다.

## 20. 데이터 공백과 중복 write를 10초/1초 bucket으로 나눠 봐야 하는 이유

증상:
- 10초 bucket에서는 공백이 없는데 실제 순간 공백이 있었을 수 있다.
- failback 중 count가 증가해 중복 write처럼 보일 수 있다.

원인:
- bucket 크기에 따라 짧은 공백이나 중복 write 후보가 가려질 수 있다.

확인 명령:

```sql
SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(10s) fill(0)

SELECT count(temperature)
FROM environment_data
WHERE time >= '<START>' AND time <= '<END>'
GROUP BY time(1s) fill(0)
```

해결/판단:
- 10초 bucket은 운영 관점의 큰 공백 확인에 사용한다.
- 1초 bucket은 전환 구간의 짧은 공백 후보 확인에 사용한다.

재발 방지:
- 장애 테스트 결과에는 두 기준을 모두 기록한다.
