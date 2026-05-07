# Tailscale Hub-Spoke Runbook

상태: source of truth
기준 issue: `docs/issues/M2_mesh-vpn-hub-spoke.md`  
정책 기준: `infra/mesh-vpn/README.md`

이 문서는 M2에서 Tailscale을 통해 Hub EKS와 Spoke K3s를 연결하는 실행 절차를 정리한다. 실제 key, OAuth secret, kubeconfig credential, Tailnet 이름, 계정 이메일은 이 문서에 기록하지 않는다.

## 범위

Tailscale은 제어/운영망이다.

```text
Hub EKS / ArgoCD
  -> Tailscale
  -> factory-a / factory-b / factory-c K3s API
```

Tailscale은 관리자 대시보드 접근망이 아니다. Dashboard Web/API는 Dashboard VPC에서 제공하고, processed S3와 latest status store만 read-only로 조회한다.

## 현재 선행 상태

필수 선행:

- M0 `factory-a` Safe-Edge 기준선 완료
- M1 Hub EKS active
- Hub kubeconfig 로컬 설정 완료
- `kubectl get nodes`로 Hub EKS 접근 가능
- ArgoCD는 Hub EKS 안에서 ClusterIP/port-forward 방식으로 동작

완료된 것:

- Tailnet 생성 확인
- Tailnet policy/tag owner 반영
- `factory-a-master` Tailscale 설치 및 Tailnet 참여
- `factory-a-master` ACL tag 적용
- Windows 운영자 PC Tailnet 참여
- Windows 운영자 PC에서 `factory-a-master` Tailscale IP ping 및 SSH 접근 확인

아직 하지 않은 것:

- Tailscale OAuth client 생성
- Hub EKS Tailscale operator 설치
- EKS 내부에서 `factory-a-master` Tailscale IP reachability 확인
- Tailscale IP 기반 `factory-a` kubeconfig 생성
- ArgoCD `factory-a` cluster 등록
- `factory-b`, `factory-c` Auth Key 발급 및 VM Spoke Tailnet 참여

현재 확인된 Tailnet device:

| 대상 | Device name | Tailscale IPv4 | 상태 |
| --- | --- | --- | --- |
| `factory-a` Raspberry Pi master | `factory-a-master` | `100.117.40.125` | Connected, tagged |
| Windows 운영자 PC | `minsoog14` | `100.67.181.8` | Connected |

## 방식 결정

EKS Hub는 Tailscale Kubernetes Operator 방식으로 시작한다.

선택 이유:

- Hub가 이미 EKS 위에 올라와 있다.
- Operator가 Kubernetes 안에서 Tailscale device/proxy를 관리할 수 있다.
- 후속 ArgoCD, multi-cluster, service exposure 흐름과 맞는다.
- 별도 EC2 Subnet Router보다 현재 Terraform/EKS 운영 경계에 잘 맞는다.

보류하는 방식:

- 별도 EC2 Subnet Router: 운영 방식은 단순하지만 Hub EKS 외부 리소스가 늘어난다.
- 단순 DaemonSet/sidecar: 초기 검증은 가능하지만 operator가 제공하는 Kubernetes-native 관리 흐름보다 장기 운영성이 낮다.

## 1. Tailnet Policy 준비

Tailscale Admin Console의 policy editor에서 tag owner를 먼저 정의한다.

필수 tag:

```text
tag:k8s-operator
tag:k8s
tag:aegis-hub
tag:aegis-spoke-prod
tag:aegis-spoke-testbed
tag:factory-a
tag:factory-b
tag:factory-c
```

현재 적용 기준:

```json
{
  "tagOwners": {
    "tag:k8s-operator": ["autogroup:admin"],
    "tag:k8s": ["tag:k8s-operator"],
    "tag:aegis-hub": ["tag:k8s-operator"],
    "tag:aegis-spoke-prod": ["autogroup:admin"],
    "tag:aegis-spoke-testbed": ["autogroup:admin"],
    "tag:factory-a": ["autogroup:admin"],
    "tag:factory-b": ["autogroup:admin"],
    "tag:factory-c": ["autogroup:admin"]
  }
}
```

접근 정책 의도:

```text
tag:aegis-hub -> tag:aegis-spoke-prod:tcp/6443
tag:aegis-hub -> tag:aegis-spoke-testbed:tcp/6443
operator device -> spoke nodes:tcp/22
operator device -> spoke nodes:tcp/6443
spoke -> spoke 직접 접근 차단
spoke -> EKS/ArgoCD admin API 직접 접근 차단
Dashboard VPC -> Tailnet 접근 없음
```

Tailnet policy는 콘솔 validation을 통과한 뒤 저장한다. policy 원문에 사용자 이메일이나 조직 정보가 들어가면 repository에 그대로 복사하지 않는다.

## 2. OAuth Client 생성

Tailscale Admin Console에서 EKS operator용 OAuth client를 만든다.

상태: 다음 작업

설정:

- Credential type: OAuth client
- Scopes:
  - `Devices Core` write
  - `Auth Keys` write
  - `Services` write
- Tag:
  - `tag:k8s-operator`

생성 후 client ID와 client secret은 한 번만 안전하게 보관한다. repository 안에는 저장하지 않는다.

로컬 보관 예시:

```text
~/.aegis/secrets/tailscale/operator.env
```

파일 형식:

```bash
TAILSCALE_OAUTH_CLIENT_ID="REDACTED"
TAILSCALE_OAUTH_CLIENT_SECRET="REDACTED"
```

권한:

```bash
chmod 600 ~/.aegis/secrets/tailscale/operator.env
```

## 3. Spoke Auth Key 생성

Tailscale Admin Console에서 Spoke별 Auth Key를 만든다. 실제 key 값은 문서에 기록하지 않는다.

| 대상 | Key type | Device setting | Tags | 만료/운영 기준 |
| --- | --- | --- | --- | --- |
| `factory-a` | One-off | Pre-approved | `tag:aegis-spoke-prod`, `tag:factory-a` | 운영형이므로 reusable 금지 |
| `factory-b` | One-off 우선 | Pre-approved | `tag:aegis-spoke-testbed`, `tag:factory-b` | VM 재생성 반복 중에만 7일 이하 reusable 허용 |
| `factory-c` | One-off 우선 | Pre-approved | `tag:aegis-spoke-testbed`, `tag:factory-c` | VM 재생성 반복 중에만 7일 이하 reusable 허용 |

로컬 임시 보관 예시:

```text
~/.aegis/secrets/tailscale/factory-a.env
~/.aegis/secrets/tailscale/factory-b.env
~/.aegis/secrets/tailscale/factory-c.env
```

파일 형식:

```bash
TAILSCALE_AUTH_KEY="REDACTED"
```

현재 상태:

- `factory-a`용 one-off tagged Auth Key는 생성했지만 secret 노출을 피하기 위해 실제 등록에는 사용하지 않았다.
- `factory-a-master`는 interactive login 후 Admin Console에서 ACL tag를 수동 적용했다.
- 미사용 `factory-a-master` Auth Key는 revoke한다.
- `factory-b`, `factory-c` Auth Key는 각 VM K3s 기준선 준비 시점에 별도 생성한다.

## 4. Hub EKS에 Tailscale Operator 설치

로컬 shell에서 Hub kubeconfig가 EKS를 가리키는지 먼저 확인한다.

상태: 다음 작업

```bash
kubectl config current-context
kubectl get nodes
```

OAuth client 값을 shell에 로드한다.

```bash
set -a
. ~/.aegis/secrets/tailscale/operator.env
set +a
```

Helm repository를 추가하고 operator를 설치한다.

```bash
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update

helm upgrade --install tailscale-operator tailscale/tailscale-operator \
  --namespace tailscale \
  --create-namespace \
  --set-string oauth.clientId="${TAILSCALE_OAUTH_CLIENT_ID}" \
  --set-string oauth.clientSecret="${TAILSCALE_OAUTH_CLIENT_SECRET}" \
  --wait
```

검증:

```bash
kubectl -n tailscale get pods
kubectl -n tailscale get deploy
kubectl get crd | grep tailscale
```

Tailscale Admin Console의 Machines 화면에서 operator device가 보이는지 확인한다. 예상 기준:

```text
device: tailscale-operator 또는 operator 관련 이름
tag: tag:k8s-operator
status: connected
```

검증 결과를 기록할 때 secret 값이나 device private detail은 남기지 않는다.

## 5. Hub EKS Egress 방식 결정

M2의 목적은 Hub/ArgoCD가 Spoke K3s API에 접근하는 것이다. Spoke가 Tailnet device로 참여하면 Hub operator 또는 operator가 관리하는 egress proxy가 Tailnet 대상에 접근할 수 있어야 한다.

초기 검증 순서:

1. Operator 설치 확인
2. `factory-a-master` Tailnet 참여
3. EKS 내부 임시 debug pod 또는 operator/proxy 경로에서 `factory-a-master` Tailscale IP reachability 확인
4. `factory-a` kubeconfig의 server 주소를 Tailscale IP로 바꿔 `kubectl get nodes` 확인
5. ArgoCD cluster 등록

EKS에서 Tailnet egress가 별도 Connector를 요구하는 경우, Tailscale Operator의 Connector CRD를 사용한다. Connector 사용 여부는 M2 Issue 3의 운영 방식 결정에 기록한다.

## 6. `factory-a` Master Tailnet 참여

상태: 완료

완료 기록:

```text
device: factory-a-master
tailscale_ipv4: 100.117.40.125
tailscale_fqdn: factory-a-master.tailf83767.ts.net
tags: tag:aegis-spoke-prod, tag:factory-a
tailscale_version: 1.96.4
operator_windows_device: minsoog14
operator_windows_tailscale_ipv4: 100.67.181.8
verification: Windows PC -> 100.117.40.125 ping and SSH success
```

실제 설치는 `factory-a` master에서 공식 install script로 진행했다.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

설치 후 interactive login 방식으로 등록했다.

```bash
sudo tailscale up --hostname=factory-a-master
```

등록 후 Admin Console에서 `factory-a-master`에 ACL tag를 수동 적용했다.

수동 재진행이 필요하면 아래 기준을 따른다.

```bash
sudo apt-get update
sudo apt-get install -y tailscale
```

Auth Key를 환경변수로 로드한다.

```bash
set -a
. ~/.aegis/secrets/tailscale/factory-a.env
set +a
```

Tailnet 참여:

```bash
sudo tailscale up \
  --authkey="${TAILSCALE_AUTH_KEY}" \
  --hostname=factory-a-master
```

확인:

```bash
tailscale status
tailscale ip -4
```

Tailscale Admin Console에서 확인:

```text
device: factory-a-master
tags: tag:aegis-spoke-prod, tag:factory-a
status: connected
tailscale_ipv4: 100.117.40.125
```

초기 M2에서는 worker node를 Tailnet에 참여시키지 않는다.

## 7. `factory-b`, `factory-c` 준비

VM K3s 기준선이 먼저 있어야 한다.

참조:

- `docs/ops/18_factory_b_mac_utm_k3s.md`
- `docs/ops/19_factory_c_windows_virtualbox_k3s.md`

각 VM에서 Tailscale을 설치하고 각자 전용 Auth Key로 참여한다.

`factory-b`:

```bash
sudo tailscale up \
  --authkey="${TAILSCALE_AUTH_KEY}" \
  --hostname=factory-b
```

`factory-c`:

```bash
sudo tailscale up \
  --authkey="${TAILSCALE_AUTH_KEY}" \
  --hostname=factory-c
```

테스트베드형 Spoke는 VM 재생성 반복 중 short-lived reusable key를 사용할 수 있다. bootstrap이 끝나면 해당 reusable key를 revoke한다.

## 8. Tailscale IP 기반 kubeconfig 생성

각 Spoke의 Tailscale IP를 확인한다.

```bash
tailscale ip -4
```

기존 kubeconfig를 복사해서 `server` 주소만 Tailscale IP로 바꾼다.

예:

```yaml
clusters:
- cluster:
    server: https://<tailscale-ip>:6443
```

주의:

- `factory-a.kubeconfig`, `factory-b.kubeconfig`, `factory-c.kubeconfig`에는 credential이 들어갈 수 있으므로 Git에 커밋하지 않는다.
- K3s API server certificate SAN이 Tailscale IP를 허용하지 않으면 TLS 오류가 날 수 있다. 이 경우 M2 Issue 4에서 K3s SAN 설정 또는 접근 방식을 조정한다.

로컬 검증:

```bash
kubectl --kubeconfig factory-a.kubeconfig get nodes
kubectl --kubeconfig factory-b.kubeconfig get nodes
kubectl --kubeconfig factory-c.kubeconfig get nodes
```

## 9. ArgoCD Cluster 등록

M2 Issue 4의 kubeconfig 검증이 끝난 뒤 진행한다.

```bash
argocd cluster add factory-a --kubeconfig factory-a.kubeconfig
```

M5에서 VM Spoke를 추가할 때:

```bash
argocd cluster add factory-b --kubeconfig factory-b.kubeconfig
argocd cluster add factory-c --kubeconfig factory-c.kubeconfig
```

확인:

```bash
argocd cluster list
```

ArgoCD UI에서 cluster connection status가 `Successful`인지 확인한다.

## 10. ArgoCD UI Private Access 전환

M1에서는 ArgoCD UI를 로컬 `kubectl port-forward`로 접근한다.

M2 이후 목표:

- public LoadBalancer를 만들지 않는다.
- Tailscale 기반 private access로 ArgoCD UI 접근 경로를 정리한다.
- EKS API endpoint public CIDR `0.0.0.0/0` 축소 기준을 수립한다.

구체 방식은 M2 Issue 3에서 operator/proxy/Connector 구성을 검증한 뒤 확정한다.

## 11. 장애 검증

검증 항목:

- `factory-a-master` Tailscale 연결 정상 시 ArgoCD cluster connection `Successful`
- Tailscale 연결 차단 시 ArgoCD cluster 상태 `Unknown` 또는 sync failure 확인
- 복구 후 ArgoCD cluster connection 정상화 확인
- 테스트 Application sync 성공

운영형 대응:

```text
factory-a Tailscale 장애:
  ArgoCD 배포 중단
  원격 운영 중단
  로컬 Safe-Edge workload 유지
  복구 전까지 변경 보류
```

테스트베드형 대응:

```text
factory-b/c Tailscale 장애:
  테스트 중단
  VM/Tailscale 재참여
  시나리오 재시도
  누락 데이터는 실패 evidence로 기록
```

## 12. Issue 갱신 기준

M2 Issue 1 완료 처리:

- 완료: Tailnet 생성 확인
- 완료: Tailnet policy/tag owner 반영
- 완료: `factory-a` one-off tagged Auth Key 생성 정책 확인
- 완료: 정책 문서화 완료
- 완료: 실제 key 값이 문서/Git에 없는지 확인

M2 Issue 2 완료 처리:

- 완료: `factory-a-master` Tailnet 참여
- 완료: Tailscale IP 기록은 secret 없이 운영 노트에 남김
- 완료: Windows 운영자 PC에서 ping 및 SSH 접근 확인

M2 Issue 3 완료 처리:

- EKS Hub operator 또는 선택한 방식 적용
- Tailscale Admin Console에서 Hub 연결 확인
- EKS에서 `factory-a-master` Tailscale IP reachability 확인
- ArgoCD UI private access 기준 기록
- EKS API endpoint public CIDR 축소 기준 기록

M2 Issue 4 완료 처리:

- Tailscale IP 기반 kubeconfig 생성
- TLS/인증 오류 없이 `kubectl get nodes` 성공
- kubeconfig 보관 방식 기록

M2 Issue 5/6 완료 처리:

- ArgoCD cluster 등록
- test Application sync
- Tailscale 차단 시 failure 동작 확인

## Reference

- Tailscale Kubernetes Operator: https://tailscale.com/docs/features/kubernetes-operator/
- Tailscale OAuth Clients: https://tailscale.com/kb/1215/oauth-clients
- Tailscale Auth Keys: https://tailscale.com/docs/features/access-control/auth-keys
- Tailscale Tags: https://tailscale.com/kb/1068/acl-tags
