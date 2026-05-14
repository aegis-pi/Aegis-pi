# Mesh VPN Infrastructure

이 디렉터리는 Tailscale 기반 Hub-Spoke 연결 구성과 관련된 인프라 또는 운영 설정 파일을 둔다.

Tailscale은 Hub가 Spoke K3s API에 접근하고 ArgoCD가 배포를 제어하기 위한 운영/제어망이다.

관리자 대시보드는 Tailscale에 의존하지 않고 별도 Data / Dashboard VPC에서 제공한다. Dashboard VPC는 DynamoDB LATEST/HISTORY와 S3 processed를 조회하며 Spoke API를 직접 호출하지 않는다.

## M2 Issue 1 정책 상태

상태: 완료

기준 issue: `docs/issues/M2_mesh-vpn-hub-spoke.md`

Tailscale Admin 콘솔에서 Tailnet과 tag owner 정책을 확인했고, `factory-a-master`를 Tailnet에 참여시켰다. 실제 key 값, 계정 이메일, Tailnet 이름, secret 값은 이 파일에 기록하지 않는다.

2026-05-07 기준 현재 참여 상태:

| 대상 | Device name | Tailscale IPv4 | 상태 |
| --- | --- | --- | --- |
| `factory-a` Raspberry Pi master | `factory-a-master` | `100.117.40.125` | Connected, tagged |
| EKS operator | `tailscale-operator` | `100.92.186.18` | Connected, tagged |
| ArgoCD -> factory-a egress proxy | `argocd-factory-a-master-tailnet` | `100.104.73.68` | Connected, tagged |
| Windows 운영자 PC | `minsoog14` | `100.67.181.8` | Connected |

`factory-a-master` 적용 tag:

```text
tag:aegis-spoke-prod
tag:factory-a
```

## Tailnet 역할

Tailscale은 아래 경로에만 사용한다.

```text
Hub EKS / ArgoCD
  -> Tailscale
  -> Spoke K3s API
```

아래 경로에는 사용하지 않는다.

```text
Dashboard Web/API -> Tailscale
Dashboard Web/API -> EKS API
Dashboard Web/API -> ArgoCD API
Dashboard Web/API -> Spoke K3s API
Spoke -> 다른 Spoke 직접 접근
```

## Device Naming

Tailnet device 이름은 공장/역할을 바로 식별할 수 있게 둔다.

| 대상 | Device name |
| --- | --- |
| `factory-a` Raspberry Pi master | `factory-a-master` |
| `factory-b` Mac VM | `factory-b` |
| `factory-c` Windows VM | `factory-c` |
| EKS Hub 연결 지점 | `aegis-hub` |

초기 M2에서는 `factory-a` master만 Spoke 대표 노드로 참여한다. `factory-a` worker 노드는 초기 참여 대상에서 제외한다.

## Auth Key 발급 정책

환경별로 Auth Key를 분리한다. 한 키를 여러 공장 또는 Hub에 재사용하지 않는다.

| 대상 | 기본 키 유형 | 태그/식별 기준 | 운영 기준 |
| --- | --- | --- | --- |
| `factory-a` | One-off, pre-approved, tagged | `tag:aegis-spoke-prod`, `tag:factory-a` | 운영형이므로 reusable key 금지 |
| `factory-b` | One-off 우선 | `tag:aegis-spoke-testbed`, `tag:factory-b` | VM 재생성 반복 중에만 7일 이하 reusable 허용 |
| `factory-c` | One-off 우선 | `tag:aegis-spoke-testbed`, `tag:factory-c` | VM 재생성 반복 중에만 7일 이하 reusable 허용 |
| EKS Hub | Issue 3에서 결정 | `tag:aegis-hub` | Operator/DaemonSet/Subnet Router 결정 전 실제 발급 보류 |

기본값은 One-off Auth Key다. reusable key는 도난 시 영향 범위가 크므로 테스트베드 VM bootstrap 반복처럼 명확한 임시 목적이 있을 때만 사용한다. reusable key를 사용한 경우 VM bootstrap 완료 직후 revoke한다.

EKS Hub 연결 방식은 M2 Issue 3에서 Tailscale Kubernetes Operator로 결정했다. Hub operator는 Tailscale OAuth client로 설치하고, Spoke K3s API 접근은 ExternalName Service egress proxy로 시작한다.

## Secret 보관

금지:

```text
Git commit
issue 본문에 secret 값 기록
README/evidence/screenshot에 key 노출
command output에 key 노출
공장 간 Auth Key 재사용
```

로컬 임시 보관이 필요하면 repository 밖의 사용자 전용 경로에 둔다.

```text
~/.aegis/secrets/tailscale/
```

Hub Kubernetes에서 사용할 값은 수동 생성 Kubernetes Secret으로 시작한다. 이후 반복 생성이 필요해지면 External Secrets, SOPS, SealedSecrets 중 하나를 별도 issue로 검토한다.

## 접근 정책 초안

최소 허용:

```text
tag:aegis-hub -> tag:aegis-spoke-prod:tcp/6443
tag:aegis-hub -> tag:aegis-spoke-testbed:tcp/6443
operator device -> spoke nodes:tcp/22
operator device -> spoke nodes:tcp/6443
```

기본 차단:

```text
factory-a -> factory-b/factory-c
factory-b -> factory-a/factory-c
factory-c -> factory-a/factory-b
spoke -> EKS API
spoke -> ArgoCD API
Dashboard VPC -> any Tailscale device
```

## 장애 대응

`factory-a` 운영형:

Tailscale 장애가 발생하면 ArgoCD 기반 배포와 원격 운영을 중단한다. 로컬 Safe-Edge workload는 계속 운영하고, 복구 전까지 수동 배포와 설정 변경을 보류한다.

`factory-b`, `factory-c` 테스트베드형:

Tailscale 장애가 발생하면 해당 테스트를 중단하고 VM/Tailscale 재참여 후 재시도한다. 테스트 데이터 누락은 실패 evidence로 기록한다.

Hub Tailscale:

Hub 연결 지점 장애가 발생하면 신규 Sync와 검증을 중단한다. 이미 배포된 Spoke workload는 유지되며, 복구 후 ArgoCD cluster connection과 test Application sync를 다시 확인한다.

2026-05-07 장애/복구 검증:

```text
failure injection:
  argocd/factory-a-master-tailnet Service 삭제
  EKS 내부 DNS 해석 실패
  argocd app sync factory-a-podinfo-smoke --timeout 60 실패

recovery:
  argocd/factory-a-master-tailnet Service 재생성
  Tailscale proxy pod 재생성
  factory-a-master-tailnet:6443 TCP open
  argocd app sync factory-a-podinfo-smoke --timeout 180 성공
  Application Synced / Healthy
```

## 다음 실행 체크

- [x] Tailscale Admin 콘솔에서 Aegis-Pi 전용 Tailnet 생성 확인
- [x] `factory-a` one-off tagged auth key 생성 정책 확인
- [ ] `factory-b` one-off 또는 short-lived reusable tagged auth key 생성
- [ ] `factory-c` one-off 또는 short-lived reusable tagged auth key 생성
- [x] M2 Issue 3 운영 방식 결정 후 EKS Hub용 OAuth client 준비
- [x] EKS Hub Tailscale Kubernetes Operator 설치
- [x] EKS 내부에서 `factory-a-master` K3s API TCP `6443` reachability 확인
- [x] ArgoCD/Grafana Tailscale IP UI 접근 확인
- [x] Tailscale egress 차단 시 ArgoCD sync failure 및 복구 확인
- [x] Tailnet tag owner 정책 반영
- [x] 실제 key 값 없이 `docs/issues/M2_mesh-vpn-hub-spoke.md` 완료 기록 갱신

## Reference

- Tailscale Auth Keys: https://tailscale.com/docs/features/access-control/auth-keys
- Tailscale Tags: https://tailscale.com/kb/1068/acl-tags
