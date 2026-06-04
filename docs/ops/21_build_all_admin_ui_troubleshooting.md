# build-all --admin-ui Troubleshooting

Status: working note
Date: 2026-05-19

현재 Hub-only 데이터 수집 유지 build 경로는 `build-hub.sh` 이후 `build-admin-ui-after-ns.sh`와 `HUB_ONLY_RECONNECT=true register-spoke-factory-a/b/c.sh`를 실행하는 방식이다. `build-hub.sh`는 유지 중인 SlowCollector EKS access binding을 자동 복구한다. 이 문서는 과거 `build-all.sh --admin-ui` 실행 중 발생한 장애 기록이며, `--admin-ui` 옵션은 현재 no-op으로 남아 있다.

## Command

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi/scripts/build
./build-all.sh --admin-ui
```

## Failure 1 - sandboxed MFA and AWS API access

The first run reached the MFA prompt, then failed after OTP entry:

```text
/home/vicbear/Aegis/.tools/aws-mfa-script/mfa.sh: line 50: /home/vicbear/.token_file: Read-only file system
aws: [ERROR]: Could not connect to the endpoint URL: "https://sts.ap-south-1.amazonaws.com/"
```

Cause:

- The MFA helper writes `~/.token_file`.
- AWS API access is required for STS and Terraform.
- The default Codex sandbox did not allow that home-file write or network access.

Resolution:

- Run the build command with elevated execution permissions when using Codex tooling.
- Run from a normal local shell when operating manually.

## Failure 2 - EKS CloudWatch Log Group already exists

The elevated run passed preflight, completed foundation apply, and started Hub apply. Hub Terraform partially created VPC networking resources, then failed:

```text
Error: creating CloudWatch Logs Log Group (/aws/eks/AEGIS-EKS/cluster):
ResourceAlreadyExistsException: The specified log group already exists

with module.eks.aws_cloudwatch_log_group.this[0]
on .terraform/modules/eks/main.tf line 230
```

Observed state:

```text
module.eks.aws_cloudwatch_log_group.this[0]
status: tainted
id: /aws/eks/AEGIS-EKS/cluster
arn: arn:aws:logs:ap-south-1:611058323802:log-group:/aws/eks/AEGIS-EKS/cluster
```

Cause:

- The log group exists in AWS.
- The Terraform state entry is tainted, so Terraform tries to replace it.
- CloudWatch Logs log group names are unique per account/region, so replacement attempts fail when the existing log group is still present.

Resolution:

```bash
cd /home/vicbear/Aegis/git_clone/Aegis-pi
terraform -chdir=infra/hub untaint 'module.eks.aws_cloudwatch_log_group.this[0]'
scripts/build/build-all.sh --admin-ui
```

If the log group exists in AWS but is missing from Terraform state instead of tainted, import it:

```bash
terraform -chdir=infra/hub import \
  'module.eks.aws_cloudwatch_log_group.this[0]' \
  '/aws/eks/AEGIS-EKS/cluster'
```

## Failure 3 - transient EC2 Security Group read

The same failed apply also printed:

```text
Error: reading Security Group (sg-0e492e6c86142fcab):
operation error EC2: DescribeSecurityGroups, StatusCode: 400, api error UnknownError

with module.eks.aws_security_group_rule.node["ingress_cluster_4443_webhook"]
```

Cause:

- Terraform had just created `sg-0e492e6c86142fcab` and several node security group rules.
- AWS EC2 returned `UnknownError` during a read-after-write refresh.
- This is likely transient if the security group and rules are now in state.

Resolution:

1. Fix the tainted CloudWatch Log Group state first.
2. Re-run `scripts/build/build-all.sh --admin-ui`.
3. If the same EC2 read error repeats, verify the security group directly:

```bash
aws ec2 describe-security-groups \
  --region ap-south-1 \
  --group-ids sg-0e492e6c86142fcab
```

If AWS can read it, rerun Terraform. If AWS cannot read it and the resource remains in state, inspect `infra/hub/terraform.tfstate` before deciding whether to remove/import resources.

## Preflight improvement

`scripts/build/preflight.sh` now checks for tainted resources in `infra/hub/terraform.tfstate` before build execution. This should catch the CloudWatch Log Group replacement condition before Terraform reaches apply.

Deposed tainted resources are not treated as preflight blockers because they can remain temporarily after an interrupted create-before-destroy replacement. Terraform should clean those up on the next successful apply.

## Failure 4 - IAM ListRolePolicies timeout during foundation refresh

After untainting the CloudWatch Log Group and rerunning with the existing MFA token, the next run failed during the `infra/foundation` plan:

```text
Error: reading inline policies for IAM role AEGIS-GitHubActions-ECRPush
operation error IAM: ListRolePolicies, StatusCode: 408, api error UnknownError

with aws_iam_role.github_actions_ecr_push
on github_actions_ecr_push.tf line 30
```

Cause:

- Terraform was refreshing existing foundation resources.
- AWS IAM returned a 408 `UnknownError` while listing inline policies.
- This is an AWS API/read timeout class failure, not a Terraform configuration diff.

Resolution:

Retry the build. If the 408 repeats during refresh, reduce Terraform request concurrency for the retry:

```bash
TF_CLI_ARGS_plan="-parallelism=1" \
TF_CLI_ARGS_apply="-parallelism=1" \
scripts/build/build-all.sh --admin-ui
```

If the error remains specific to one IAM role, verify the role directly:

```bash
aws iam list-role-policies --role-name AEGIS-GitHubActions-ECRPush
aws iam get-role --role-name AEGIS-GitHubActions-ECRPush
```

## Failure 5 - repeated CloudWatch ListTagsForResource timeout

After the IAM timeout retry, foundation passed and Hub refresh progressed further. Hub then failed again on the EKS log group tag read:

```text
Error: listing tags for CloudWatch Logs Log Group
arn:aws:logs:ap-south-1:611058323802:log-group:/aws/eks/AEGIS-EKS/cluster
operation error CloudWatch Logs: ListTagsForResource, StatusCode: 408, api error UnknownError
```

Cause:

- The log group is now correctly untainted in Terraform state.
- The failure is an AWS CloudWatch Logs API read timeout during Terraform refresh/plan.
- Similar 408 `UnknownError` responses were also seen from IAM and EC2 reads.

Resolution:

- `scripts/lib/terraform.sh` now defaults Terraform AWS SDK calls to:

```bash
AWS_RETRY_MODE=adaptive
AWS_MAX_ATTEMPTS=10
```

- For this run, continue retrying with reduced Terraform parallelism:

```bash
TF_CLI_ARGS_plan="-parallelism=1" \
TF_CLI_ARGS_apply="-parallelism=1" \
scripts/build/build-all.sh --admin-ui
```

## Failure 6 - ArgoCD Helm install lost Kubernetes API connection

After Hub Terraform completed successfully and wrote `secret/admin-ui-nameservers.txt`, Ansible started the Hub ArgoCD bootstrap. Helm failed during the first ArgoCD install:

```text
Error: Unable to continue with install:
could not get information about the resource Role "argocd-application-controller" in namespace "argocd":
Get "https://BDDC0AD2C02AFCCD63D401C6D397EE45.sk1.ap-south-1.eks.amazonaws.com/...":
http2: client connection lost
```

Observed after the failure:

```bash
helm list -n argocd --all --output json
# []

kubectl -n argocd get all,role,rolebinding,secret,configmap --ignore-not-found
# only kube-root-ca.crt ConfigMap was present
```

Cause:

- The EKS control plane and node group had just been created.
- The Kubernetes API connection dropped while Helm was checking whether ArgoCD chart resources already existed.
- No Helm release remained installed, so this was safe to retry.

Resolution:

Re-run the same build command. If this repeats, retry only Hub bootstrap after kube API stabilizes:

```bash
aws eks update-kubeconfig --region ap-south-1 --name AEGIS-EKS
kubectl cluster-info
helm list -n argocd --all
scripts/build/build-all.sh --admin-ui
```

## Failure 7 - repeated Helm http2 client connection loss

The ArgoCD Helm install was retried after confirming no Helm release remained. It failed again:

```text
Error: Get "https://BDDC0AD2C02AFCCD63D401C6D397EE45.sk1.ap-south-1.eks.amazonaws.com/api/v1/namespaces/argocd/services/argocd-applicationset-controller":
http2: client connection lost
```

Cause:

- The failure is reproducible at the Helm/Kubernetes API client layer.
- `helm` and `kubectl` are Go binaries and use Go's HTTP/2 client behavior by default.
- The EKS public API endpoint connection is being dropped while Helm is checking/creating chart resources.

Resolution:

`scripts/build/build-hub.sh` now exports this default for Hub Ansible bootstrap:

```bash
GODEBUG=http2client=0
```

This disables Go HTTP/2 client use for `helm`/`kubectl` calls launched by the Hub build. Re-run:

```bash
TF_CLI_ARGS_plan="-parallelism=1" \
TF_CLI_ARGS_apply="-parallelism=1" \
scripts/build/build-all.sh --admin-ui
```
