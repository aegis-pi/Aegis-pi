# Cloud / AWS Hub Troubleshooting

원본:

- `docs/ops/21_build_all_admin_ui_troubleshooting.md`
- `docs/ops/21_hub_admin_ui_ingress.md`
- `docs/ops/20_tailscale_hub_spoke_runbook.md`
- `docs/ops/19_factory_c_windows_virtualbox_k3s.md`

## 🐛 트러블슈팅 리포트 - MFA helper sandbox 파일 쓰기와 AWS STS 접근 실패

### 📌 현상 요약

Codex sandbox 환경에서 Hub build 실행 중 MFA token 파일 쓰기와 AWS STS endpoint 접근이 실패했다.

### 🖥️ 환경 정보

- 클러스터: Hub AWS/EKS build 전 단계
- 노드: 운영 PC
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: AWS CLI, MFA helper, Terraform, Codex sandbox
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. Codex 기본 sandbox에서 `scripts/build/build-all.sh --admin-ui`를 실행한다.
2. MFA OTP를 입력한다.
3. MFA helper와 AWS STS 호출 결과를 확인한다.

### ✅ 기대 동작

MFA helper가 token 파일을 쓰고 AWS STS 호출이 성공해야 한다.

### ❌ 실제 동작

```text
/home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh: line 50: /home/vicbear/.token_file: Read-only file system
aws: [ERROR]: Could not connect to the endpoint URL: "https://sts.ap-south-1.amazonaws.com/"
```

### 🔍 시도한 것들

- [x] MFA helper가 home directory에 token file을 쓰는지 확인
- [x] STS/Terraform에 외부 AWS API 접근이 필요한지 확인
- [x] Codex tooling에서는 elevated execution으로 실행
- [x] 수동 운영 시 normal local shell 사용 기준 정리

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, Automation / Script

### 💡 해결 방법

**근본 원인:**

기본 sandbox가 home 파일 쓰기와 외부 AWS API 네트워크 접근을 제한했다.

**해결 방법:**

Codex tooling에서는 AWS build 명령을 elevated execution으로 실행한다. 수동 운영자는 일반 로컬 shell에서 실행한다.

**재발 방지:**

AWS API, MFA token 파일, Terraform backend/state 접근이 필요한 명령은 sandbox 제약을 사전 점검한다.

## 🐛 트러블슈팅 리포트 - EKS CloudWatch Log Group 중복 생성 실패

### 📌 현상 요약

Hub Terraform apply 중 EKS CloudWatch Log Group이 이미 존재해 생성에 실패했다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS
- 노드: 해당 없음
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Terraform, AWS EKS, CloudWatch Logs
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. Hub Terraform apply가 중간 실패한 상태를 만든다.
2. CloudWatch Log Group resource가 tainted 상태인지 확인한다.
3. build를 재실행한다.

### ✅ 기대 동작

기존 Log Group을 Terraform state와 일관되게 관리해야 한다.

### ❌ 실제 동작

```text
Error: creating CloudWatch Logs Log Group (/aws/eks/AEGIS-EKS/cluster):
ResourceAlreadyExistsException: The specified log group already exists

module.eks.aws_cloudwatch_log_group.this[0]
status: tainted
```

### 🔍 시도한 것들

- [x] Terraform state에서 tainted resource 확인
- [x] `terraform -chdir=infra/hub untaint` 실행
- [x] state에 없고 AWS에만 있으면 import하는 절차 정리
- [x] preflight에서 tainted resource 검사 추가

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Terraform, EKS

### 💡 해결 방법

**근본 원인:**

CloudWatch Log Group은 AWS에 이미 존재했지만 Terraform state entry가 tainted여서 Terraform이 replacement 생성을 시도했다.

**해결 방법:**

AWS 리소스가 정상이고 state만 tainted라면 `terraform untaint`로 교정한다. state에 없으면 `terraform import`로 가져온다.

**재발 방지:**

Hub build preflight에서 tainted resource를 apply 전에 감지한다.

## 🐛 트러블슈팅 리포트 - EC2 Security Group read-after-write UnknownError

### 📌 현상 요약

Terraform apply 중 막 생성된 Security Group 조회가 AWS EC2 `UnknownError`로 실패했다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS
- 노드: 해당 없음
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Terraform, AWS EC2 Security Group
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. Hub Terraform apply 중 Security Group과 rule을 생성한다.
2. Terraform refresh/read 단계에서 Security Group을 조회한다.
3. EC2 API 오류를 확인한다.

### ✅ 기대 동작

생성된 Security Group을 AWS EC2 API가 정상 조회해야 한다.

### ❌ 실제 동작

```text
Error: reading Security Group (sg-...):
operation error EC2: DescribeSecurityGroups, StatusCode: 400, api error UnknownError
```

### 🔍 시도한 것들

- [x] CloudWatch Log Group taint 문제를 먼저 해결
- [x] build 재실행
- [x] 반복 시 `aws ec2 describe-security-groups`로 직접 조회
- [x] state와 실제 AWS resource 일치 여부 확인 기준 정리

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, Terraform, AWS EC2

### 💡 해결 방법

**근본 원인:**

AWS EC2 API의 read-after-write refresh 중 일시적인 `UnknownError`가 발생했다.

**해결 방법:**

일시 오류이면 재실행한다. 반복되면 AWS CLI로 직접 resource를 조회하고, state와 실제 resource를 대조한 뒤 import/remove 여부를 판단한다.

**재발 방지:**

AWS API read 오류는 Terraform 설정 diff와 구분한다. 반복 오류만 state 수정을 검토한다.

## 🐛 트러블슈팅 리포트 - IAM ListRolePolicies timeout

### 📌 현상 요약

Foundation Terraform refresh 중 IAM role inline policy 조회가 408 timeout으로 실패했다.

### 🖥️ 환경 정보

- 클러스터: Hub foundation
- 노드: 해당 없음
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Terraform, AWS IAM
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. `infra/foundation` Terraform plan/apply를 실행한다.
2. 기존 IAM role refresh 단계로 진입한다.
3. `ListRolePolicies` 호출 결과를 확인한다.

### ✅ 기대 동작

Terraform이 IAM role inline policy를 조회하고 plan을 계속 진행해야 한다.

### ❌ 실제 동작

```text
Error: reading inline policies for IAM role AEGIS-GitHubActions-ECRPush
operation error IAM: ListRolePolicies, StatusCode: 408, api error UnknownError
```

### 🔍 시도한 것들

- [x] AWS IAM read timeout으로 분류
- [x] build 재시도
- [x] 반복 시 Terraform parallelism 축소
- [x] `aws iam list-role-policies`, `aws iam get-role` 직접 확인

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, Terraform, AWS IAM

### 💡 해결 방법

**근본 원인:**

Terraform refresh 중 AWS IAM API가 408 `UnknownError`를 반환했다. 구성 변경 문제가 아니라 AWS API read timeout 계열이다.

**해결 방법:**

재시도하고, 반복되면 `TF_CLI_ARGS_plan="-parallelism=1"` 및 `TF_CLI_ARGS_apply="-parallelism=1"`로 요청 동시성을 낮춘다.

**재발 방지:**

AWS API timeout이 반복되는 build에는 adaptive retry와 낮은 parallelism을 적용한다.

## 🐛 트러블슈팅 리포트 - CloudWatch ListTagsForResource timeout

### 📌 현상 요약

Hub Terraform refresh 중 EKS CloudWatch Log Group tag 조회가 408 timeout으로 반복 실패했다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS
- 노드: 해당 없음
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: Terraform, CloudWatch Logs
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. CloudWatch Log Group taint를 해소한다.
2. Hub Terraform refresh/plan을 재실행한다.
3. Log Group tag 조회 단계의 오류를 확인한다.

### ✅ 기대 동작

Terraform이 CloudWatch Log Group tag를 조회하고 plan을 계속 진행해야 한다.

### ❌ 실제 동작

```text
Error: listing tags for CloudWatch Logs Log Group
operation error CloudWatch Logs: ListTagsForResource, StatusCode: 408, api error UnknownError
```

### 🔍 시도한 것들

- [x] Log Group state가 untainted인지 확인
- [x] AWS API read timeout으로 분류
- [x] `AWS_RETRY_MODE=adaptive`, `AWS_MAX_ATTEMPTS=10` 기본값 적용
- [x] Terraform parallelism 축소 재시도

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, Terraform, CloudWatch Logs

### 💡 해결 방법

**근본 원인:**

CloudWatch Logs API가 Terraform refresh 중 tag 조회 요청에 408 timeout을 반환했다.

**해결 방법:**

Terraform AWS SDK 호출에 adaptive retry와 충분한 max attempts를 적용하고, 필요하면 parallelism을 낮춘다.

**재발 방지:**

`scripts/lib/terraform.sh`에 AWS retry 기본값을 유지한다.

## 🐛 트러블슈팅 리포트 - ArgoCD Helm 설치 중 EKS API 연결 손실

### 📌 현상 요약

Hub EKS 생성 직후 ArgoCD Helm install 중 Kubernetes API 연결이 끊겼다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS
- 노드: EKS node group
- 네임스페이스: argocd
- 관련 컴포넌트/버전: Helm, Argo CD chart, EKS public API endpoint
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. Hub Terraform으로 EKS control plane과 node group을 생성한다.
2. Ansible로 ArgoCD Helm install을 시작한다.
3. Helm install 중 API 조회 오류를 확인한다.

### ✅ 기대 동작

Helm이 ArgoCD chart resource를 생성하고 release를 남겨야 한다.

### ❌ 실제 동작

```text
Error: Unable to continue with install:
could not get information about the resource Role "argocd-application-controller" in namespace "argocd":
http2: client connection lost

helm list -n argocd --all
[]
```

### 🔍 시도한 것들

- [x] Helm release가 남지 않았는지 확인
- [x] `argocd` namespace resource 상태 확인
- [x] kube API 안정화 후 같은 build 재시도
- [x] `aws eks update-kubeconfig`, `kubectl cluster-info`, `helm list` 확인 절차 정리

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, EKS, GitOps / Argo CD

### 💡 해결 방법

**근본 원인:**

EKS control plane과 node group이 막 생성된 직후 Helm이 resource existence를 확인하는 동안 Kubernetes API 연결이 끊겼다.

**해결 방법:**

Helm release가 남지 않았으면 kube API가 안정화된 뒤 같은 build 또는 Hub bootstrap을 재시도한다.

**재발 방지:**

EKS 생성 직후 bootstrap 전 `kubectl cluster-info`와 Helm release 상태를 확인한다.

## 🐛 트러블슈팅 리포트 - Helm http2 client connection loss 반복

### 📌 현상 요약

ArgoCD Helm install 재시도 후에도 Go HTTP/2 client 연결 손실이 반복됐다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS
- 노드: EKS node group
- 네임스페이스: argocd
- 관련 컴포넌트/버전: Helm, kubectl, Go HTTP/2 client, EKS public API endpoint
- 발생 시각: 2026-05-19

### 🔁 재현 순서

1. ArgoCD Helm install을 재시도한다.
2. Helm이 Kubernetes API resource를 조회한다.
3. http2 client connection loss가 반복되는지 확인한다.

### ✅ 기대 동작

Helm/kubectl이 EKS API endpoint와 안정적으로 통신해야 한다.

### ❌ 실제 동작

```text
Error: Get "https://...eks.amazonaws.com/api/v1/namespaces/argocd/services/argocd-applicationset-controller":
http2: client connection lost
```

### 🔍 시도한 것들

- [x] Helm release 잔존 여부 확인
- [x] Helm/kubectl Go HTTP/2 client 동작으로 분류
- [x] Hub Ansible bootstrap에 `GODEBUG=http2client=0` 적용
- [x] build 재실행

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, EKS, GitOps / Argo CD

### 💡 해결 방법

**근본 원인:**

EKS public API endpoint 연결이 Helm/kubectl의 Go HTTP/2 client 사용 중 반복적으로 끊겼다.

**해결 방법:**

Hub build에서 `GODEBUG=http2client=0`을 export해 Helm/kubectl 호출이 HTTP/2 client를 사용하지 않도록 한다.

**재발 방지:**

Hub bootstrap 실행 환경에 `GODEBUG=http2client=0` 기본값을 유지한다.

## 🐛 트러블슈팅 리포트 - ACM ISSUED 전 Admin Ingress 활성화 위험

### 📌 현상 요약

ACM certificate가 `ISSUED` 되기 전 Admin UI Ingress를 활성화하면 HTTPS listener/ALB 구성이 실패할 수 있다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS
- 노드: EKS node group
- 네임스페이스: argocd, observability
- 관련 컴포넌트/버전: AWS Load Balancer Controller, ACM, Route53, Public ALB
- 발생 시각: 2026-05-19 기준 운영 결정

### 🔁 재현 순서

1. Route53 Hosted Zone을 새로 만든다.
2. Gabia NS 위임과 ACM DNS validation이 끝나기 전 Admin Ingress를 활성화한다.
3. AWS Load Balancer Controller가 HTTPS listener를 구성하는지 확인한다.

### ✅ 기대 동작

ACM certificate가 `ISSUED` 된 뒤 Admin UI Ingress와 ALB가 생성되어야 한다.

### ❌ 실제 동작

ACM 발급 전에는 HTTPS listener가 정상 구성될 수 없고, 불필요한 ALB 비용이 발생할 수 있다.

### 🔍 시도한 것들

- [x] `ADMIN_UI_INGRESS_ENABLED=false` 기본값 유지
- [x] Route53 NS 위임 후 ACM `ISSUED` 확인
- [x] `build-admin-ui-after-ns.sh`로 Admin Ingress 별도 활성화
- [x] destroy 시 Ingress cleanup을 Terraform destroy 전에 실행

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, LoadBalancer / MetalLB, Network

### 💡 해결 방법

**근본 원인:**

Public ALB HTTPS listener는 유효한 ACM certificate가 필요하다. DNS 위임 전에는 certificate validation이 완료되지 않는다.

**해결 방법:**

Hub build에서는 Route53, ACM, AWS Load Balancer Controller까지만 준비하고 Admin Ingress는 비활성화한다. ACM `ISSUED` 확인 후 별도 스크립트로 활성화한다.

**재발 방지:**

Admin UI Ingress 활성화는 NS 위임과 ACM 발급 완료 이후 단계로 분리한다.

## 🐛 트러블슈팅 리포트 - ArgoCD smoke app ARM64 exec format error

### 📌 현상 요약

ArgoCD smoke test 후보로 사용한 guestbook image가 Raspberry Pi ARM64에서 실행되지 않았다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s, Hub ArgoCD
- 노드: Raspberry Pi ARM64 worker
- 네임스페이스: smoke test namespace
- 관련 컴포넌트/버전: ArgoCD, `argoproj/argocd-example-apps`, `gcr.io/google-samples/gb-frontend:v5`
- 발생 시각: 2026-05-07 문서화

### 🔁 재현 순서

1. Hub ArgoCD에서 guestbook smoke app을 factory-a에 배포한다.
2. Pod 상태와 container log를 확인한다.
3. ARM64 node에서 image 실행 가능 여부를 확인한다.

### ✅ 기대 동작

Smoke app Pod가 ARM64 node에서 정상 실행되어야 한다.

### ❌ 실제 동작

```text
gcr.io/google-samples/gb-frontend:v5
exec format error
```

### 🔍 시도한 것들

- [x] guestbook smoke 후보 제외
- [x] Bitnami nginx Helm chart도 repo-server restart 문제로 제외
- [x] factory-a에 맞는 podinfo smoke app 사용
- [x] Sync/Healthy 확인

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, GitOps / Argo CD, K3s / Kubernetes

### 💡 해결 방법

**근본 원인:**

Smoke test image가 Raspberry Pi ARM64 아키텍처와 맞지 않았다.

**해결 방법:**

ARM64 호환 smoke app을 사용한다.

**재발 방지:**

Spoke smoke app 후보는 node architecture와 manifest generation 안정성을 검증한 뒤 채택한다.

## 🐛 트러블슈팅 리포트 - Tailscale egress 삭제로 인한 ArgoCD sync 실패

### 📌 현상 요약

Hub에서 factory-a master로 가는 Tailscale egress Service를 삭제하자 ArgoCD sync가 실패했다.

### 🖥️ 환경 정보

- 클러스터: AEGIS-EKS Hub, factory-a K3s
- 노드: factory-a master
- 네임스페이스: argocd, tailscale
- 관련 컴포넌트/버전: Tailscale Operator, ArgoCD cluster connection, ExternalName Service
- 발생 시각: 2026-05-07

### 🔁 재현 순서

1. 정상 상태에서 `argocd cluster list`와 smoke app sync를 확인한다.
2. `argocd/factory-a-master-tailnet` Service를 삭제한다.
3. ArgoCD app sync를 실행한다.
4. Service를 재생성하고 복구 여부를 확인한다.

### ✅ 기대 동작

Tailscale egress 경로가 살아 있으면 ArgoCD가 factory-a K3s API에 접근해야 한다.

### ❌ 실제 동작

```text
argocd app sync factory-a-podinfo-smoke --timeout 60 -> Failed
failure message -> no such host for factory-a-master-tailnet.argocd.svc.cluster.local
```

### 🔍 시도한 것들

- [x] egress Service 삭제로 failure injection
- [x] EKS busybox `nc`로 DNS/6443 접근 실패 확인
- [x] Service 재생성
- [x] Tailscale proxy Pod Running 확인
- [x] ArgoCD sync/wait 성공 확인

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Network, GitOps / Argo CD

### 💡 해결 방법

**근본 원인:**

ArgoCD factory-a cluster connection은 Hub 내부 Tailscale egress Service DNS와 proxy 경로에 의존한다.

**해결 방법:**

삭제된 egress Service를 재생성하고 Tailscale proxy Pod가 Running인지 확인한다. 이후 `argocd app sync`와 `argocd cluster list`로 복구를 검증한다.

**재발 방지:**

Tailscale 장애 시 ArgoCD 배포 변경을 보류하고, 로컬 Safe-Edge workload 유지 상태로 복구를 먼저 수행한다.

## 🐛 트러블슈팅 리포트 - IoT Rule S3 raw 적재 실패

### 📌 현상 요약

MQTT publish는 성공하지만 IoT Rule을 통한 S3 `raw/factory-c` 적재가 되지 않았다.

### 🖥️ 환경 정보

- 클러스터: factory-c VM Spoke, AWS foundation/data pipeline
- 노드: factory-c worker VM
- 네임스페이스: edge data-plane namespace
- 관련 컴포넌트/버전: AWS IoT Core, IoT Rule, S3, IAM Role, edge-iot-publisher
- 발생 시각: factory-c data-plane 문서화 시점

### 🔁 재현 순서

1. factory-c에서 MQTT publish를 실행한다.
2. `mosquitto_pub exit=0`을 확인한다.
3. S3 `raw/factory-c` prefix에 object가 생성되는지 확인한다.
4. IoT Rule, IAM Role, bucket policy, CloudWatch IoT Logging을 확인한다.

### ✅ 기대 동작

IoT Rule이 `aegis/factory-c/+` topic을 받아 S3 `raw/factory-c/*`에 JSON을 저장해야 한다.

### ❌ 실제 동작

```text
mosquitto_pub exit=0
S3 raw/factory-c 비어 있음
CloudWatch IoT Logging에 AccessDenied 가능
```

### 🔍 시도한 것들

- [x] IoT Rule 존재와 `disabled=false` 확인
- [x] Rule SQL topic filter 확인
- [x] IAM Role `s3:PutObject` resource ARN 확인
- [x] S3 bucket policy 차단 여부 확인
- [x] TLS/auth, endpoint, client id 확인

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Data Pipeline, AWS IoT Core, S3

### 💡 해결 방법

**근본 원인:**

MQTT publish 성공과 S3 적재 성공은 별개다. IoT Rule SQL, Rule enabled 상태, IAM Role S3 권한, bucket policy 중 하나가 맞지 않으면 S3 object가 생성되지 않는다.

**해결 방법:**

IoT Rule enabled 상태와 SQL을 확인하고, Rule Role의 `s3:PutObject` 권한이 `arn:aws:s3:::aegis-bucket-data/raw/factory-c/*`와 정확히 일치하는지 확인한다.

**재발 방지:**

공장 추가 시 IoT Rule, Role policy, bucket policy, topic prefix를 하나의 검증 체크리스트로 묶는다.

## 🐛 트러블슈팅 리포트 - factory-c Flannel DNS/MQTT 연결 실패

### 📌 현상 요약

factory-c worker Pod에서 AWS IoT Core endpoint DNS 해석과 MQTT 연결이 실패했다.

### 🖥️ 환경 정보

- 클러스터: factory-c Windows VirtualBox K3s
- 노드: master VM, worker VM
- 네임스페이스: edge data-plane namespace
- 관련 컴포넌트/버전: K3s, Flannel VXLAN, CoreDNS, edge-iot-publisher, VirtualBox NAT/Host-only Adapter
- 발생 시각: factory-c data-plane 문서화 시점

### 🔁 재현 순서

1. VirtualBox NAT adapter만 사용해 master/worker VM K3s를 구성한다.
2. worker Pod에서 AWS IoT endpoint DNS 해석을 시도한다.
3. CoreDNS와 Pod-to-Pod 통신 상태를 확인한다.

### ✅ 기대 동작

worker Pod가 CoreDNS를 통해 AWS IoT endpoint를 해석하고 MQTT publish를 수행해야 한다.

### ❌ 실제 동작

```text
Temporary failure in name resolution
MQTT connection failed
Master/Worker INTERNAL-IP가 모두 10.0.2.15
```

### 🔍 시도한 것들

- [x] VirtualBox NAT adapter의 동일 `10.0.2.15` 할당 확인
- [x] Host-only 또는 Bridged adapter 추가
- [x] master/worker 고유 IP 대역 확보
- [x] K3s `node-ip`와 `flannel-iface` 강제 지정
- [x] `kubectl get nodes -o wide`로 INTERNAL-IP 분리 확인

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Network, K3s / Kubernetes, Data Pipeline

### 💡 해결 방법

**근본 원인:**

VirtualBox NAT adapter만 사용하면 master/worker VM이 동일한 `10.0.2.15` INTERNAL-IP를 갖게 되어 Flannel VXLAN과 Pod-to-Pod DNS 경로가 꼬인다.

**해결 방법:**

각 VM에 Host-only 또는 Bridged adapter를 추가하고, K3s config에 고유 `node-ip`와 `flannel-iface`를 명시한다.

**재발 방지:**

VM Spoke 기준선에 NAT 단독 사용 금지, 고유 internal IP, flannel interface 고정 원칙을 포함한다.

## 🐛 트러블슈팅 리포트 - Factory-A ECR pull secret 만료로 adapter rollout 실패

### 📌 현상 요약

GitOps에서 `factory-a-log-adapter`를 `main` tag로 배포했지만 새 Pod가 `ErrImagePull`로 멈췄다.

### 🖥️ 환경 정보

- 클러스터: factory-a K3s Spoke, Hub ArgoCD
- 노드: worker2
- 네임스페이스: ai-apps
- 관련 컴포넌트/버전: Amazon ECR, Kubernetes imagePullSecret, ArgoCD, factory-a-log-adapter
- 발생 시각: 2026-05-27

### 🔁 재현 순서

1. GitOps에서 `factory-a-log-adapter` image tag를 `main`으로 변경한다.
2. ArgoCD sync를 실행한다.
3. 새 ReplicaSet Pod 상태와 ArgoCD application tree를 확인한다.

### ✅ 기대 동작

Factory-A K3s가 ECR에서 새 `factory-a-log-adapter:main` 이미지를 pull하고 rollout이 완료되어야 한다.

### ❌ 실제 동작

```text
Back-off pulling image "611058323802.dkr.ecr.ap-south-1.amazonaws.com/aegis/factory-a-log-adapter:main"
unexpected status from HEAD request ... 403 Forbidden
ErrImagePull
Waiting for rollout to finish: 0 of 1 updated replicas are available
```

### 🔍 시도한 것들

- [x] ArgoCD `aegis-spoke-factory-a` sync/health 확인
- [x] ArgoCD controller 내부 `argocd --core app get -o tree=detailed`로 remote Pod event 확인
- [x] Factory-A `ai-apps/ecr-registry` Secret 생성 시각 확인
- [x] ECR pull secret 갱신 후 rollout restart
- [x] S3 raw publish 재개 확인

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Data Pipeline, K3s / Kubernetes, GitOps

### 💡 해결 방법

**근본 원인:**

Factory-A Spoke K3s는 EKS node가 아니므로 EKS node role의 ECR pull 권한을 상속받지 않는다. `ai-apps/ecr-registry`에 저장된 ECR token이 만료되어 새 이미지 pull이 `403 Forbidden`으로 실패했다.

**해결 방법:**

```bash
ECR_PULL_SECRET_NAMESPACE=ai-apps \
FACTORY_A_KUBECONFIG=/home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
scripts/ops/refresh-factory-a-ecr-pull-secret.sh

kubectl --kubeconfig /home/vicbear/Aegis/.aegis/secrets/kubeconfig/factory-a.tailscale-ip-tlsname.kubeconfig \
  -n ai-apps rollout restart deployment/aegis-spoke-factory-a-log-adapter
```

**재발 방지:**

Spoke cluster별 ECR pull secret 갱신 주기를 운영 절차에 포함한다. 장기적으로는 external-secrets 또는 ECR credential refresh automation을 붙인다.

## 🐛 트러블슈팅 리포트 - Lambda stale bytecode로 processed schema 변경 미반영

### 📌 현상 요약

DataProcessor normalizer를 수정하고 Lambda를 배포했지만 S3 `processed/` 결과는 계속 구 schema로 보였다.

### 🖥️ 환경 정보

- 클러스터: AWS data-pipeline
- 노드: N/A
- 네임스페이스: N/A
- 관련 컴포넌트/버전: AWS Lambda python3.12, Terraform `archive_file`, S3 processed, DynamoDB LATEST/HISTORY#STATE
- 발생 시각: 2026-05-27

### 🔁 재현 순서

1. `apps/data-processor/processor/normalizer.py`를 수정한다.
2. `scripts/build/build-data-pipe.sh`로 Lambda를 배포한다.
3. CloudWatch Logs와 S3 `processed/factory-a/infra_state` 결과를 비교한다.

### ✅ 기대 동작

processed object와 state_snapshot이 `node_id`, `ready`, `status=Ready`, `pods_ready`, device `available` 필드를 포함해야 한다.

### ❌ 실제 동작

```json
{
  "nodes_ready": 0,
  "nodes": [{"name": "", "status": "Unknown"}],
  "pods_ready": 0,
  "devices": {"bme280": {"status": "unknown"}}
}
```

### 🔍 시도한 것들

- [x] Lambda `CodeSha256`와 `LastModified` 확인
- [x] 실제 Lambda zip을 내려받아 파일 목록 확인
- [x] `python3 -m zipfile -l`로 `__pycache__` 포함 여부 확인
- [x] Terraform archive exclude 패턴 수정
- [x] Lambda 재배포 후 CloudWatch `nodes_ready=3/3` 로그 확인

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Data Pipeline, AWS Lambda, Terraform

### 💡 해결 방법

**근본 원인:**

Lambda zip archive에 `processor/__pycache__/*.pyc`가 포함되어 source 변경과 실제 runtime 동작이 어긋날 수 있었다.

**해결 방법:**

Terraform `archive_file` exclude를 재귀 패턴으로 수정한다.

```hcl
excludes = ["**/__pycache__/**", "**/*.pyc", "**/*.pyo", "tests/**", ".pytest_cache/**"]
```

이후 `scripts/build/build-data-pipe.sh`로 Lambda를 다시 배포한다.

**재발 방지:**

Lambda zip 검증 시 `python3 -m zipfile -l infra/data-pipeline/lambda_data_processor.zip`로 `__pycache__`와 `*.pyc`가 없는지 확인한다.

## 🐛 트러블슈팅 리포트 - 중복 KJW IoT Rule이 processed 결과를 덮어씀

### 📌 현상 요약

`AEGIS-Lambda-DataProcessor`는 정상적으로 `nodes_ready=3/3` 로그를 남겼지만, S3 `processed/` object는 구형 schema로 남았다.

### 🖥️ 환경 정보

- 클러스터: AWS IoT Core / data-pipeline
- 노드: N/A
- 네임스페이스: N/A
- 관련 컴포넌트/버전: AWS IoT Rule, AWS Lambda, S3 processed, DynamoDB
- 발생 시각: 2026-05-27

### 🔁 재현 순서

1. Factory-A에서 `aegis/factory-a/infra_state`로 메시지를 publish한다.
2. `AEGIS-Lambda-DataProcessor` CloudWatch log를 확인한다.
3. S3 `processed/factory-a/infra_state` object를 확인한다.
4. IoT Rule 목록에서 같은 topic을 받는 Rule을 찾는다.

### ✅ 기대 동작

공식 DataProcessor 하나만 `processed/` 결과를 쓰고, canonical schema가 보존되어야 한다.

### ❌ 실제 동작

구형 Lambda가 같은 topic을 받아 `processed/` result를 나중에 덮어썼다.

```text
KJW_AEGIS_Data_IoTRule_infra_state_processor
KJW_AEGIS_Data_IoTRule_factory_state_processor
```

각 Rule은 아래 topic을 수신했다.

```text
SELECT * FROM 'aegis/+/infra_state'
SELECT * FROM 'aegis/+/factory_state'
```

### 🔍 시도한 것들

- [x] `aws iot list-topic-rules`로 전체 Rule 확인
- [x] KJW Rule SQL과 Lambda action 확인
- [x] 중복 KJW Rule 비활성화
- [x] 최신 processed infra_state와 state_snapshot 재검증

### 🚨 심각도

상

### 🗂️ 영역

Cloud / AWS Hub, Data Pipeline, AWS IoT Core, AWS Lambda, S3

### 💡 해결 방법

**근본 원인:**

공식 `AEGIS_IoTRule_factory_a/b/c_raw_s3` 외에 legacy KJW Rule이 같은 topic을 수신해 구형 `KJW-AEGIS-Data-Lambda-data-processor`를 호출했다. 두 Lambda가 같은 S3 `processed/` prefix를 쓰면서 결과가 덮어써졌다.

**해결 방법:**

```bash
aws iot disable-topic-rule \
  --region ap-south-1 \
  --rule-name KJW_AEGIS_Data_IoTRule_infra_state_processor

aws iot disable-topic-rule \
  --region ap-south-1 \
  --rule-name KJW_AEGIS_Data_IoTRule_factory_state_processor
```

**재발 방지:**

운영 검증 전 `aws iot list-topic-rules`로 중복 수신 Rule을 확인한다. 같은 S3 `processed/` prefix를 쓰는 Lambda가 여러 개인지도 함께 확인한다.

## 🐛 트러블슈팅 리포트 - 엣지 서버와 클라우드간 시각 비동기화

### 📌 현상 요약

VM dummy generator timestamp가 실제 시간보다 크게 뒤처져 S3 적재 경로와 실시간 모니터링 정합성이 깨졌다.

### 🖥️ 환경 정보

- 클러스터: factory-b/c VM Spoke, AWS S3 data pipeline
- 노드: worker VM
- 네임스페이스: 해당 없음
- 관련 컴포넌트/버전: dummy-generator, S3 raw prefix, chrony/NTP
- 발생 시각: factory-c data-plane 문서화 시점

### 🔁 재현 순서

1. VM worker에서 dummy generator를 실행한다.
2. 생성 파일명과 payload timestamp를 확인한다.
3. S3 LastModified 시간과 object prefix 시간을 비교한다.
4. `chronyc tracking`으로 clock drift를 확인한다.

### ✅ 기대 동작

Edge timestamp와 cloud ingest time이 허용 가능한 범위 안에 있어야 한다.

### ❌ 실제 동작

```text
dummy-generator timestamp가 실제 시간보다 30분 이상 느림
S3 object가 예전 날짜/시간 prefix에 적재됨
```

### 🔍 시도한 것들

- [x] `chronyc tracking`으로 NTP 상태 확인
- [x] 누적 오차가 큰 경우 `sudo chronyc makestep` 실행
- [x] `date`와 generator log로 정상 시간 확인

### 🚨 심각도

중

### 🗂️ 영역

Cloud / AWS Hub, Data Pipeline, Operations / DR

### 💡 해결 방법

**근본 원인:**

VM clock drift가 누적되었고, NTP daemon이 큰 오차를 자동 보정하지 못했다.

**해결 방법:**

`chronyc tracking`으로 상태를 확인하고, 큰 오차가 있으면 `sudo chronyc makestep`으로 강제 동기화한다.

**재발 방지:**

VM Spoke 운영 기준에 chrony 상태 점검과 clock drift alert 기준을 포함한다.
