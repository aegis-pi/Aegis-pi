# Terraform State Migration Audit

Date: 2026-06-08

Scope: audit and migration planning only. No Terraform apply, destroy, import, state rm, state mv, backend file edit, or `terraform init -migrate-state` was performed.

## 1. Current Commit / Status

- Commit: `a9fb5ab73cc3855667409631c0c2b11de8abc3bc`
- Initial `git status --short`: clean
- Status after audit commands, before this document: clean

## 2. Local State / Sensitive Artifact Discovery

| Root | `terraform.tfstate` | `.terraform/` | `terraform.tfvars` | `*.tfplan` | `*.tfstate.backup` | Local state owner |
|---|---:|---:|---:|---:|---:|---|
| `infra/foundation` | yes | yes | yes | no | yes | yes |
| `infra/hub` | yes | yes | yes | no | yes | yes |
| `infra/data-pipeline` | yes | yes | yes | yes | yes | yes |
| `infra/reporting` | yes | yes | yes | no | yes | yes |

Discovered local state files:

- `infra/foundation/terraform.tfstate`
- `infra/hub/terraform.tfstate`
- `infra/data-pipeline/terraform.tfstate`
- `infra/reporting/terraform.tfstate`

Discovered tfvars / plan / backup artifacts:

- `infra/foundation/terraform.tfvars`
- `infra/foundation/terraform.tfstate.backup`
- `infra/hub/terraform.tfvars`
- `infra/hub/terraform.tfstate.backup`
- `infra/data-pipeline/terraform.tfvars`
- `infra/data-pipeline/terraform.tfstate.backup`
- `infra/data-pipeline/*.tfplan` files exist
- `infra/reporting/terraform.tfvars`
- `infra/reporting/terraform.tfstate.backup`

No tfvars, tfstate backup, or plan file was copied into the repo.

## 3. Current Backend / Provider State

| Root | Backend block in root config | Provider summary | Notes |
|---|---|---|---|
| `infra/foundation` | none found | `aws ~> 6.0`, Terraform `>= 1.15.0` | Uses local state by default. `terraform.tfvars` sets `aws_region = "ap-south-1"`. |
| `infra/hub` | none found | `aws ~> 6.0`, Terraform `>= 1.15.0` | Uses local state by default. Reads foundation outputs through local `terraform_remote_state`. |
| `infra/data-pipeline` | none found | `aws ~> 6.0`, `archive ~> 2.7`, Terraform `>= 1.15.0` | Uses local state by default. |
| `infra/reporting` | none found | `aws ~> 6.0`, `archive ~> 2.7`, Terraform `>= 1.15.0` | Uses local state by default. |

Hub foundation dependency:

```hcl
data "terraform_remote_state" "foundation" {
  backend = "local"

  config = {
    path = var.foundation_state_path
  }
}
```

`var.foundation_state_path` defaults to `../foundation/terraform.tfstate`. After foundation is migrated to S3, hub must be updated to read foundation remote state from S3 before hub migration can be treated as clean.

## 4. Script References

References found under `scripts/`:

- `scripts/lib/terraform.sh`: runs `terraform init`
- `scripts/build/reconcile-data-pipe-eks-access.sh`: runs `terraform init`
- `scripts/destroy/*`: multiple direct local `terraform.tfstate` checks
- `scripts/build/*`: multiple direct local `terraform.tfstate` checks
- `scripts/hub/README.md` and `scripts/destroy/README.md`: document local state assumptions

Important migration impact: build/destroy/preflight scripts currently rely on local state file paths such as `infra/foundation/terraform.tfstate`, `infra/hub/terraform.tfstate`, and `infra/data-pipeline/terraform.tfstate`. These scripts should be reviewed before removing local state files or relying exclusively on S3 backend state.

## 5. State List Summary

`infra/foundation` was the only root where Terraform commands progressed far enough before a stop condition. Other root summaries below are derived from local state JSON only, without printing state values.

| Root | Terraform `state list` executed | Address count from `terraform state list` | Managed instance count from local state JSON | Summary |
|---|---:|---:|---:|---|
| `infra/foundation` | yes | 25 | 23 | ECR repositories/lifecycle policies, S3 bucket and controls, DynamoDB table, Route53 zone/records, ACM certificate, IAM/OIDC for GitHub Actions. |
| `infra/hub` | no, stopped after foundation | not run | 60 | Local state contains VPC, EKS, IAM, KMS, NAT/EIP, routing, and related module resources. |
| `infra/data-pipeline` | no, stopped after foundation | not run | 61 | Local state contains Lambda/API Gateway/IAM/EventBridge Scheduler/IoT/S3 notification/Secrets Manager/EKS access resources. |
| `infra/reporting` | no, stopped after foundation | not run | 23 | Local state contains reporting Lambda, Step Functions, scheduler, IAM, and log groups. |

Foundation `terraform state list` addresses:

```text
data.aws_iam_policy_document.github_actions_ecr_push
data.aws_iam_policy_document.github_actions_ecr_push_assume_role
aws_acm_certificate.admin_ui
aws_dynamodb_table.factory_status
aws_ecr_lifecycle_policy.edge_agent
aws_ecr_lifecycle_policy.edge_iot_publisher
aws_ecr_lifecycle_policy.factory_a_log_adapter
aws_ecr_lifecycle_policy.snapshot_uploader
aws_ecr_repository.edge_agent
aws_ecr_repository.edge_iot_publisher
aws_ecr_repository.factory_a_log_adapter
aws_ecr_repository.snapshot_uploader
aws_iam_openid_connect_provider.github_actions
aws_iam_role.github_actions_ecr_push
aws_iam_role_policy.github_actions_ecr_push
aws_route53_record.admin_ui_certificate_validation["argocd.minsoo-tech.cloud"]
aws_route53_record.admin_ui_certificate_validation["grafana.minsoo-tech.cloud"]
aws_route53_record.admin_ui_certificate_validation["minsoo-tech.cloud"]
aws_route53_zone.admin_ui
aws_s3_bucket.data
aws_s3_bucket_lifecycle_configuration.data
aws_s3_bucket_ownership_controls.data
aws_s3_bucket_public_access_block.data
aws_s3_bucket_server_side_encryption_configuration.data
aws_s3_bucket_versioning.data
```

## 6. Refresh-Only Plan Results

| Root | Result | Change summary | Blocker |
|---|---|---|---|
| `infra/foundation` | failed | Terraform detected `aws_s3_bucket.data` / `aegis-bucket-data` as deleted outside Terraform and output changes for `data_bucket_arn` / `data_bucket_name`. Full refresh did not complete. | AWS reads failed with explicit deny from `arn:aws:iam::611058323802:policy/Admin-MFA-Enforce` for Route53, ACM, DynamoDB, ECR, IAM, and S3 bucket subresources. |
| `infra/hub` | not run | not evaluated | Stopped after foundation blocker. Hub also depends on foundation local state output. |
| `infra/data-pipeline` | not run | not evaluated | Stopped after foundation blocker. |
| `infra/reporting` | not run | not evaluated | Stopped after foundation blocker. |

Foundation refresh-only command details:

- Initial sandboxed `terraform plan -refresh-only -no-color` failed because the AWS provider plugin could not be instantiated in the sandbox.
- Retried with approved read-only execution.
- The retry refreshed some resources, then failed on AWS API permissions.

Observed permission blocker:

```text
User: arn:aws:iam::611058323802:user/student05 is not authorized ...
with an explicit deny in an identity-based policy:
arn:aws:iam::611058323802:policy/Admin-MFA-Enforce
```

Observed drift warning:

```text
Terraform detected the following changes made outside of Terraform:
aws_s3_bucket.data has been deleted
```

This must be investigated before migration or any future apply. If the bucket was intentionally removed, state and configuration need an explicit decision. If it still exists but is hidden by permissions/MFA, rerun the refresh with credentials that satisfy the policy.

## 7. Normal Plan Results

| Root | Result | Create | Update | Destroy | Notes |
|---|---|---:|---:|---:|---|
| `infra/foundation` | not run | unknown | unknown | unknown | Not run because refresh-only failed and showed a blocker. |
| `infra/hub` | not run | unknown | unknown | unknown | Stopped after foundation blocker. |
| `infra/data-pipeline` | not run | unknown | unknown | unknown | Stopped after foundation blocker. |
| `infra/reporting` | not run | unknown | unknown | unknown | Stopped after foundation blocker. |

No normal plan destroy list is available because normal plans were intentionally not run after the stop condition.

## 8. State Backup

Created backup:

- `/tmp/aegis-tfstate-backups/foundation.20260608-152456.tfstate`

No backup was committed or copied into the repo.

Backups for hub, data-pipeline, and reporting were not created because execution stopped after the foundation refresh-only blocker. On the next run, create backups before each root's state list/plan.

## 9. S3 Backend Migration Candidates

Candidate backend bucket from existing dashboard VPC usage:

- Bucket: `kjw-aegis-terraform-state`
- Region: `ap-northeast-2`
- Lock: `use_lockfile = true`

| Root | Candidate key |
|---|---|
| `infra/foundation` | `aegis-pi/foundation/terraform.tfstate` |
| `infra/hub` | `aegis-pi/hub/terraform.tfstate` |
| `infra/data-pipeline` | `aegis-pi/data-pipeline/terraform.tfstate` |
| `infra/reporting` | `aegis-pi/reporting/terraform.tfstate` |

Bucket/key access was not verified in this audit because the foundation refresh-only step hit AWS explicit deny. Treat backend bucket access as unclear until confirmed with valid credentials/MFA.

## 10. Migration Readiness

| Root | S3 migration readiness | Reason |
|---|---|---|
| `infra/foundation` | not ready | Refresh-only failed due AWS explicit deny and showed possible S3 bucket drift/deletion. Backend bucket access is also unverified. |
| `infra/hub` | not ready | Foundation must be resolved first. Hub reads foundation outputs from local state and will need S3 remote_state update after foundation migration. |
| `infra/data-pipeline` | not ready | Not audited because foundation blocker stopped the run. |
| `infra/reporting` | not ready | Not audited because foundation blocker stopped the run. |

No root is currently approved for migration based on this audit.

## 11. Commands Draft For Future Migration

Do not run these until:

- AWS credentials satisfy `Admin-MFA-Enforce` or equivalent read access requirements.
- `terraform plan -refresh-only` completes without unexpected drift.
- `terraform plan` completes with no unexpected create/update and zero destroy.
- Candidate S3 key is confirmed absent or intentionally selected.
- A fresh `/tmp/aegis-tfstate-backups/<root>.<timestamp>.tfstate` backup exists.
- For hub, foundation has already been migrated and hub's `terraform_remote_state.foundation` has been updated to S3.

Preflight checks:

```bash
aws s3 ls s3://kjw-aegis-terraform-state/aegis-pi/foundation/terraform.tfstate
aws s3 ls s3://kjw-aegis-terraform-state/aegis-pi/hub/terraform.tfstate
aws s3 ls s3://kjw-aegis-terraform-state/aegis-pi/data-pipeline/terraform.tfstate
aws s3 ls s3://kjw-aegis-terraform-state/aegis-pi/reporting/terraform.tfstate
```

Backend block draft for `infra/foundation`:

```hcl
terraform {
  backend "s3" {
    bucket       = "kjw-aegis-terraform-state"
    key          = "aegis-pi/foundation/terraform.tfstate"
    region       = "ap-northeast-2"
    use_lockfile = true
  }
}
```

Migration command draft for `infra/foundation` after backend block is added:

```bash
cd infra/foundation

terraform init \
  -backend-config="bucket=kjw-aegis-terraform-state" \
  -backend-config="key=aegis-pi/foundation/terraform.tfstate" \
  -backend-config="region=ap-northeast-2" \
  -backend-config="use_lockfile=true" \
  -migrate-state
```

Hub remote_state draft after foundation migration:

```hcl
data "terraform_remote_state" "foundation" {
  backend = "s3"

  config = {
    bucket = "kjw-aegis-terraform-state"
    key    = "aegis-pi/foundation/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
```

Migration command drafts for remaining roots after their audits pass:

```bash
cd infra/hub
terraform init \
  -backend-config="bucket=kjw-aegis-terraform-state" \
  -backend-config="key=aegis-pi/hub/terraform.tfstate" \
  -backend-config="region=ap-northeast-2" \
  -backend-config="use_lockfile=true" \
  -migrate-state

cd infra/data-pipeline
terraform init \
  -backend-config="bucket=kjw-aegis-terraform-state" \
  -backend-config="key=aegis-pi/data-pipeline/terraform.tfstate" \
  -backend-config="region=ap-northeast-2" \
  -backend-config="use_lockfile=true" \
  -migrate-state

cd infra/reporting
terraform init \
  -backend-config="bucket=kjw-aegis-terraform-state" \
  -backend-config="key=aegis-pi/reporting/terraform.tfstate" \
  -backend-config="region=ap-northeast-2" \
  -backend-config="use_lockfile=true" \
  -migrate-state
```

## 12. Stop Condition

Audit stopped at `infra/foundation` because:

1. `terraform plan -refresh-only` did not complete.
2. AWS access failed with explicit deny from `Admin-MFA-Enforce`.
3. Terraform reported possible drift: `aws_s3_bucket.data` / `aegis-bucket-data` deleted outside Terraform.
4. Backend bucket access is unclear under the current credentials.

No apply/destroy/import/state rm/state mv/backend migration command was run.

---

## 13. MFA Re-Audit Session (2026-06-08)

This section supersedes the earlier readiness conclusions where results differ.
The audit remained read-only: no apply, destroy, import, state rm, state mv,
backend configuration edit, or `terraform init -migrate-state` was performed.

### 13.1 AWS Identity / Session

- Caller account: `611058323802`
- Caller ARN: `arn:aws:iam::611058323802:user/student05`
- `AWS_SESSION_TOKEN`: present (value was not printed)
- Read calls that were previously denied by `Admin-MFA-Enforce` succeeded,
  including S3, Route53, ACM, DynamoDB, ECR, IAM, VPC, and EKS refreshes.
- Conclusion: the current temporary session satisfies the MFA enforcement
  policy for the read-only audit. STS `get-caller-identity` itself reports the
  IAM user ARN and does not independently expose MFA context.

### 13.2 Commit / Worktree

- Commit: `a9fb5ab73cc3855667409631c0c2b11de8abc3bc`
- Initial and final `git status --short`: `?? TFSTATE_MIGRATION_AUDIT.md`
- No tracked infrastructure/configuration file changed during this session.

### 13.3 Backend Bucket / Candidate Keys

`aws s3api head-bucket` succeeded for `kjw-aegis-terraform-state`, so backend
access is confirmed under the current MFA session.

Important region correction:

- Requested/candidate region: `ap-northeast-2`
- Actual bucket region returned by S3: `ap-south-1`
- Migration configuration must use `ap-south-1`, unless a different bucket in
  `ap-northeast-2` was intended.

All candidate key HEAD requests returned `404 Not Found`, which means the keys
are currently empty/available candidates:

| Root | Candidate key | Result |
|---|---|---|
| `infra/foundation` | `aegis-pi/foundation/terraform.tfstate` | 404, empty candidate |
| `infra/hub` | `aegis-pi/hub/terraform.tfstate` | 404, empty candidate |
| `infra/data-pipeline` | `aegis-pi/data-pipeline/terraform.tfstate` | 404, empty candidate |
| `infra/reporting` | `aegis-pi/reporting/terraform.tfstate` | 404, empty candidate |

### 13.4 Root Audit Results

Roots were processed in the required order. Execution stopped during
`infra/hub` because its refresh-only plan showed broad unexpected changes.

| Root | Init | Backup | State addresses | Refresh-only | Normal plan | Destroy |
|---|---|---|---:|---|---|---|
| `infra/foundation` | success | `/tmp/aegis-tfstate-backups/foundation.20260608-153106.tfstate` | 25 | success; 2 external/state-normalization changes | no changes; create 0, update 0, destroy 0 | none |
| `infra/hub` | success | `/tmp/aegis-tfstate-backups/hub.20260608-153225.tfstate` | 78 | success, but broad unexpected changes; stop condition | not run due stop condition | not evaluated |
| `infra/data-pipeline` | not run | not created | not run | not run | not run | not evaluated |
| `infra/reporting` | not run | not created | not run | not run | not run | not evaluated |

The earlier foundation backup remains at
`/tmp/aegis-tfstate-backups/foundation.20260608-152456.tfstate`. No backup was
created or copied inside the repository.

Foundation refresh-only details:

- `aws_s3_bucket.data` / `aegis-bucket-data` refreshed successfully.
- Its ownership controls, public access block, versioning, encryption, and
  lifecycle configuration also refreshed successfully.
- The earlier "deleted outside Terraform" result was caused by insufficient
  non-MFA read permissions, not by actual bucket deletion.
- Refresh-only reported an empty ECR tags normalization and the current IAM
  inline policy including the snapshot-uploader repository.
- The subsequent normal plan reported `No changes`.

Hub refresh-only details:

- `data.terraform_remote_state.foundation` read completed successfully from the
  current local foundation state.
- Changes covered multiple categories: NAT EIP association details, route
  table routes, IAM policy attachments/inline policy, EKS addon/tag
  normalization, EKS access scope, security group rules, launch template
  normalization, and KMS/EKS metadata.
- Because this is a broad set of refresh changes, it meets the session's
  unexpected-large-change stop condition. No hub normal plan was run.
- After foundation migration, hub's `terraform_remote_state.foundation` must
  be changed from local state to the foundation S3 key before hub migration.

### 13.5 Migration Readiness / Decisions

| Root | Latest readiness | Required action or decision |
|---|---|---|
| `infra/foundation` | conditionally ready | Normal plan is clean and key is empty. Use the bucket's actual `ap-south-1` region, not `ap-northeast-2`. |
| `infra/hub` | user decision required; not ready | Review and accept/explain the broad refresh-only changes, then rerun refresh-only and normal plan. Update foundation remote_state to S3 after foundation migration. |
| `infra/data-pipeline` | not ready / unaudited | Resume its audit only after the hub stop condition is resolved or explicitly waived. |
| `infra/reporting` | not ready / unaudited | Resume its audit only after preceding stop conditions are resolved or explicitly waived. |

Root eligible to proceed to an actual migration in a future approved session:
`infra/foundation`, provided the backend region is corrected to `ap-south-1`
and the candidate key is rechecked immediately before migration.

### 13.6 Corrected Future Migration Draft

These commands are drafts only and were not run. The backend block must first
be reviewed and added in a future migration session.

```hcl
terraform {
  backend "s3" {
    bucket       = "kjw-aegis-terraform-state"
    key          = "aegis-pi/foundation/terraform.tfstate"
    region       = "ap-south-1"
    use_lockfile = true
  }
}
```

```bash
cd infra/foundation

mkdir -p /tmp/aegis-tfstate-backups
terraform state pull \
  > /tmp/aegis-tfstate-backups/foundation.$(date +%Y%m%d-%H%M%S).tfstate

aws s3api head-object \
  --bucket kjw-aegis-terraform-state \
  --key aegis-pi/foundation/terraform.tfstate \
  --region ap-south-1

terraform init -migrate-state -no-color
terraform state list
terraform plan -refresh-only -no-color
terraform plan -no-color
```

After foundation is migrated, the hub dependency draft is:

```hcl
data "terraform_remote_state" "foundation" {
  backend = "s3"

  config = {
    bucket = "kjw-aegis-terraform-state"
    key    = "aegis-pi/foundation/terraform.tfstate"
    region = "ap-south-1"
  }
}
```

Equivalent future backend keys, only after each remaining root passes a full
audit, are:

- `infra/hub`: `aegis-pi/hub/terraform.tfstate`
- `infra/data-pipeline`: `aegis-pi/data-pipeline/terraform.tfstate`
- `infra/reporting`: `aegis-pi/reporting/terraform.tfstate`

### 13.7 Re-Audit Stop Condition

The session stopped at `infra/hub` because refresh-only showed broad unexpected
changes. Consequently, hub normal plan and all Terraform commands for
data-pipeline and reporting were intentionally not run.

---

## 14. Foundation S3 Backend Migration (2026-06-08)

Migration time: approximately `2026-06-08 15:43 KST` (`2026-06-08 06:43 UTC`).

Scope was limited to `infra/foundation`. No backend migration or Terraform
command was run in hub, data-pipeline, or reporting.

### 14.1 Pre-Migration Checks

- AWS caller account: `611058323802`
- Caller ARN: `arn:aws:iam::611058323802:user/student05`
- MFA temporary session indicator: `AWS_SESSION_TOKEN` present
- Commit: `a9fb5ab73cc3855667409631c0c2b11de8abc3bc`
- Initial status: `?? TFSTATE_MIGRATION_AUDIT.md`
- Local `infra/foundation/terraform.tfstate`: present
- Existing configuration: no backend block, therefore default local backend
- Bucket region: confirmed `ap-south-1`
- Candidate key HEAD immediately before migration: `404 Not Found`
- Candidate key was not overwritten.

Backend:

| Setting | Value |
|---|---|
| Bucket | `kjw-aegis-terraform-state` |
| Key | `aegis-pi/foundation/terraform.tfstate` |
| Region | `ap-south-1` |
| Locking | `use_lockfile = true` |

### 14.2 Backup / Pre-Migration State

- Backup:
  `/tmp/aegis-tfstate-backups/foundation.20260608-154137.tfstate`
- SHA-256:
  `e35d134d62248f5e3a0191804287d70ad5b761068c8af502d78f19f89e52678a`
- Address list:
  `/tmp/aegis-tfstate-backups/foundation.20260608-154137.addresses.txt`
- State address count: 25
- Managed/data resource blocks in state JSON: 23
- Lineage: `a99ba8eb-76b4-5d40-8305-b4d72cd20247`
- Serial: 291

Pre-migration refresh-only completed successfully. It showed the same two
previously audited normalization/external-state details:

- empty tags normalization for `aws_ecr_repository.snapshot_uploader`
- current GitHub Actions ECR inline policy includes snapshot-uploader

The pre-migration normal plan reported `No changes`; create, update, and
destroy counts were all zero.

### 14.3 Backend Configuration / Migration

Added the S3 backend block to `infra/foundation/versions.tf`.
`terraform fmt -check versions.tf` passed.

Executed:

```bash
terraform init -migrate-state -no-color
```

Terraform reported that the previous backend was local, the new S3 backend had
no existing state, and requested confirmation to copy the existing state. Only
that copy was approved. Initialization completed successfully.

S3 object creation was confirmed:

- Last modified: `2026-06-08T06:43:25Z`
- Content length: 60007 bytes
- Version ID: `ianVFfYJdYnWmojTCelyAj5uYKPR8mas`
- Server-side encryption: `AES256`

The local files were not deleted:

- `terraform.tfstate`: present, but Terraform migration left it as a zero-byte
  local placeholder
- `terraform.tfstate.backup`: present, 60009 bytes
- `terraform.tfvars`: present

### 14.4 Post-Migration State Comparison / Stop Condition

Remote pull:

- File:
  `/tmp/aegis-tfstate-backups/foundation.20260608-154137.remote-post.tfstate`
- SHA-256:
  `d4f5859d6e10d3a40e40a9e90496653bf39b52bf78d1348ba0b2b475c64de71c`
- Address count: 25
- Address list comparison: exact match
- Remote lineage: `42cfb07c-00c3-5b13-b407-2e0bbfe07c36`
- Remote serial: 1

The resource address list and state JSON body are identical. A canonical JSON
comparison after removing only `lineage`, `serial`, and `terraform_version`
produced the same SHA-256 on both sides:

`2db95e9dbda24f38905d964bd2bfcf3c8294330df0ab6818acfae42b5c4bd1c2`

However, lineage changed unexpectedly and serial was re-based from 291 to 1.
This matched the explicit stop condition in the migration instructions.
Therefore:

- no post-migration refresh-only plan was run
- no post-migration normal plan was run
- no rollback, force push, state replacement, or additional migration command
  was attempted

The S3 backend remains configured and the migrated state object remains in
place. Resource/address content is preserved, but migration validation is not
fully approved until the lineage behavior is reviewed.

### 14.5 Source / Artifact Status

Intended source changes:

- `infra/foundation/versions.tf`
- `TFSTATE_MIGRATION_AUDIT.md`

Final tracked/untracked status at this stage:

- modified: `infra/foundation/versions.tf`
- untracked: `TFSTATE_MIGRATION_AUDIT.md`

`.terraform/`, tfstate, tfstate backup, tfvars, plan, and credential files were
not added to Git. No plan file was created.

No `terraform apply`, `terraform destroy`, `terraform import`,
`terraform state rm`, or `terraform state mv` command was run. No AWS
application resource was changed.

### 14.6 Remaining Risks / Next Step

- Existing build/destroy scripts still contain local `terraform.tfstate`
  existence assumptions. They were not modified.
- Hub was not migrated or modified.
- Hub still reads foundation through local `terraform_remote_state`; before any
  hub migration, that data source must be changed to the foundation S3 backend.
- Before proceeding with hub work, review the previously recorded broad hub
  refresh-only diff.
- The lineage/serial re-basing decision and final plans were completed in
  section 14.7. Foundation is now fully verified against the S3 state.

### 14.7 Authoritative State Acceptance / Post-Migration Verification

The lineage reissue and serial reset were explicitly accepted after confirming
that all 25 resource addresses and the state body excluding metadata matched.
The current S3 state is now accepted as the authoritative foundation state.
No attempt was made to restore the previous lineage with `terraform state
push`, `-force`, manual state editing, or S3 object replacement.

Verification identity and backend:

- AWS account: `611058323802`
- MFA temporary session indicator: `AWS_SESSION_TOKEN` present
- Backend type: `s3`
- Bucket: `kjw-aegis-terraform-state`
- Key: `aegis-pi/foundation/terraform.tfstate`
- Region: `ap-south-1`
- Locking: `use_lockfile = true`

Authoritative S3 state:

- Version ID: `ianVFfYJdYnWmojTCelyAj5uYKPR8mas`
- Lineage: `42cfb07c-00c3-5b13-b407-2e0bbfe07c36`
- Serial: 1
- State address count: 25
- State JSON resource blocks: 23
- Address comparison with the pre-migration backup: exact match
- Metadata-excluded state body comparison: exact match
- Normalized body SHA-256:
  `2db95e9dbda24f38905d964bd2bfcf3c8294330df0ab6818acfae42b5c4bd1c2`

Post-migration plan results:

- `terraform plan -refresh-only -no-color`: completed successfully
- Refresh-only showed only the same two previously audited normalization
  details for snapshot-uploader tags and the GitHub Actions ECR inline policy.
  No large or unexpected drift was found.
- `terraform plan -no-color`: `No changes`
- Create: 0
- Update: 0
- Destroy: 0
- The S3 state version ID, lineage, serial, and 25-address count remained
  unchanged after both plans.

Foundation migration and post-migration verification are complete. No AWS
application resource was changed. No apply, destroy, import, state push,
state rm, state mv, or repeated `init -migrate-state` command was run.

Hub, data-pipeline, and reporting were not touched. The next separate task is
to review hub's broad refresh-only diff and prepare hub's foundation
`terraform_remote_state` data source to read this S3 state.

---

## 15. Hub Foundation Remote-State Transition Audit (2026-06-08)

Scope was limited to changing Hub's Foundation data source from the obsolete
zero-byte local state path to the authoritative Foundation S3 state. Hub's own
state remains local. No Hub backend migration was performed.

### 15.1 Hub Backup / Backend

- Backup:
  `/tmp/aegis-tfstate-backups/hub.20260608-155235.tfstate`
- SHA-256:
  `424226f50122311fd0a3c09e28364090a46b2bc480d2056a557770e35dbb40a0`
- Address list:
  `/tmp/aegis-tfstate-backups/hub.20260608-155235.addresses.txt`
- Address count: 78
- Lineage: `6372b788-77ab-ebd0-ca75-a657112df020`
- Serial: 3912
- State JSON resource blocks: 57
- Hub Terraform backend block: none
- Hub backend after `terraform init -no-color`: local

The pulled backup and local state have different raw JSON serialization by one
byte, but canonical JSON SHA-256 values are identical:

`4083b9f05b2be0b1e3c6b292b269930f50d45efe91f4947dcc53563cc915172f`

The Hub local state was not modified.

### 15.2 Foundation Data Source Configuration

Changed `infra/hub/foundation_remote_state.tf`:

```hcl
data "terraform_remote_state" "foundation" {
  backend = "s3"

  config = {
    bucket = "kjw-aegis-terraform-state"
    key    = "aegis-pi/foundation/terraform.tfstate"
    region = "ap-south-1"
  }
}
```

`terraform init -no-color` completed successfully. No `-migrate-state` option
was used, and no Hub backend block was added.

### 15.3 Foundation Output Comparison / Stop Condition

The migration-preflight Foundation local backup and authoritative S3 state
contain the same 24 outputs. Names, types, sensitivity metadata, and values
match exactly. Their canonical output SHA-256 is:

`bcd6b5dfed73a09d0fd905956dc86f392f4146347cca4dccdc07f6f8a151f32d`

However, the `terraform_remote_state.foundation` snapshot cached in Hub local
state predates the snapshot-uploader Foundation additions:

| Output comparison | Result | Classification |
|---|---|---|
| 22 common outputs | exact value match | unchanged |
| `edge_data_plane_image_tag_strategy` | S3/local Foundation includes `aegis/snapshot-uploader`; Hub cache does not | stale Hub data-source cache |
| `snapshot_uploader_ecr_repository_url` | present in S3/local Foundation; absent from Hub cache | stale Hub data-source cache |

Neither differing output is referenced by the current Hub Terraform
configuration. Admin UI, bucket, DynamoDB, ECR, IAM, and Route53 outputs
actually consumed by Hub match.

Despite the differences being attributable to an older cached data-source
snapshot rather than a Foundation migration discrepancy, the requested stop
condition was "Foundation S3 outputs differ from existing values." The audit
therefore stopped before running either Hub plan.

### 15.4 Plan / Broad-Diff Status

| Check | Result |
|---|---|
| `terraform plan -refresh-only -no-color` | not run due output mismatch stop condition |
| `terraform plan -no-color` | not run due output mismatch stop condition |
| Create/update/destroy | not evaluated |
| Broad diff classification | not rerun; current S3-data-source plan evidence unavailable |

The previous broad refresh-only result remains relevant as preliminary
evidence, but it was produced before this S3 data-source transition. NAT/EIP,
routing, IAM, EKS, and security-group items must be rerun and classified after
the stale cached-output difference is explicitly accepted.

### 15.5 Hub Migration Readiness

Hub is not yet ready for S3 backend migration because:

- post-transition refresh-only and normal plans have not been run
- the broad refresh-only differences have not been classified against the
  current S3 Foundation data source
- create/update/destroy counts are unknown

No apply, destroy, import, state push, state rm, state mv, refresh-only apply,
or `terraform init -migrate-state` command was run. No AWS resource was
changed. Data-pipeline and reporting were not touched.

### 15.6 Accepted Cache Difference / Read-Only Plan Audit

The stale Hub data-source cache difference was explicitly accepted because:

- Foundation S3 state is authoritative and fully verified.
- The Foundation migration-preflight local state and current S3 state have the
  same 24 outputs.
- The two stale outputs are not referenced by the Hub configuration:
  `edge_data_plane_image_tag_strategy` and
  `snapshot_uploader_ecr_repository_url`.
- The 7 Foundation outputs actually referenced by Hub match exactly between
  the stale Hub cache and the authoritative S3 state:
  `admin_ui_argocd_host`, `admin_ui_certificate_arn`,
  `admin_ui_certificate_validation_records`, `admin_ui_domain_name`,
  `admin_ui_grafana_host`, `admin_ui_route53_name_servers`, and
  `admin_ui_route53_zone_id`.
- Canonical SHA-256 for those 7 used outputs:
  `4cfa7b9e284ac992fccf91c6b0e35163c599f30f8c8a98b4ab4ec78e2654d45a`
- Hub managed state remained 78 addresses and local backend.

Verification inputs:

- AWS account: `611058323802`
- MFA temporary session indicator: `AWS_SESSION_TOKEN` present
- Hub backup:
  `/tmp/aegis-tfstate-backups/hub.20260608-155235.tfstate`
- Hub backup SHA-256:
  `424226f50122311fd0a3c09e28364090a46b2bc480d2056a557770e35dbb40a0`
- Hub lineage/serial: `6372b788-77ab-ebd0-ca75-a657112df020` / `3912`
- Foundation S3 version ID:
  `ianVFfYJdYnWmojTCelyAj5uYKPR8mas`

Read-only plan artifacts:

- Refresh-only output:
  `/tmp/aegis-tfstate-backups/hub.20260608-155235.refresh-only.txt`
- Normal plan output:
  `/tmp/aegis-tfstate-backups/hub.20260608-155235.normal-plan.txt`

Refresh-only completed successfully. No resource deletion, replacement,
ownership conflict, or AWS API error was observed.

| Resource | Changed attributes | Classification | Notes |
|---|---|---|---|
| `aws_eip.nat` | NAT association fields: `association_id`, `network_interface`, `private_dns`, `private_ip` | provider/state normalization | EIP is associated with the managed NAT gateway; stale state lacked computed association fields. |
| `aws_eks_addon.metrics_server[0]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |
| `aws_iam_policy.aws_lb_controller` | `attachment_count`, `tags = {}` | provider/state normalization / AWS relationship reflection | Attachment is managed separately by `aws_iam_role_policy_attachment.aws_lb_controller`. |
| `aws_iam_role.aws_lb_controller_irsa` | `managed_policy_arns`, `tags = {}` | provider/state normalization / AWS relationship reflection | Managed policy attachment is separately managed. |
| `aws_iam_role.risk_normalizer_irsa` | `inline_policy`, `tags = {}` | provider/state normalization / AWS relationship reflection | Inline policy is separately managed by `aws_iam_role_policy.risk_normalizer_s3`. |
| `aws_route_table.private["Azone"]` | `route` to NAT gateway | provider/state normalization / AWS relationship reflection | Route is separately managed by `aws_route.private_nat_gateway["Azone"]`. |
| `aws_route_table.private["Czone"]` | `route` to NAT gateway | provider/state normalization / AWS relationship reflection | Route is separately managed by `aws_route.private_nat_gateway["Czone"]`. |
| `aws_route_table.public` | `route` to internet gateway | provider/state normalization / AWS relationship reflection | Route is separately managed by `aws_route.public_internet_gateway`. |
| `module.eks.aws_eks_access_entry.this["cluster_creator"]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |
| `module.eks.aws_eks_access_policy_association.this["cluster_creator_admin"]` | `access_scope.namespaces = []` | provider/state normalization | Empty list normalization. |
| `module.eks.aws_eks_addon.before_compute["vpc-cni"]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |
| `module.eks.aws_eks_addon.this["coredns"]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |
| `module.eks.aws_eks_addon.this["kube-proxy"]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |
| `module.eks.aws_eks_cluster.this[0]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |
| `module.eks.aws_iam_policy.cluster_encryption[0]` | `attachment_count`, `tags = {}` | provider/state normalization / AWS relationship reflection | Attachment is separately managed by module IAM attachment resources. |
| `module.eks.aws_iam_role.this[0]` | `managed_policy_arns`, `tags = {}` | provider/state normalization / AWS relationship reflection | Attachments are separately managed by module IAM attachment resources. |
| `module.eks.aws_security_group.cluster[0]` | inline `ingress` projection | provider/state normalization / AWS relationship reflection | Cluster SG rule is separately managed by `module.eks.aws_security_group_rule.cluster["ingress_nodes_443"]`. |
| `module.eks.aws_security_group.node[0]` | inline `egress` and `ingress` projection | mixed: provider/state normalization plus expected controller-managed drift | Most rules are separately managed by `module.eks.aws_security_group_rule.node[...]`. One ingress rule is external: `elbv2.k8s.aws/targetGroupBinding=shared`, tcp 3000-8080 from `sg-0628a353979ceee5a`; EC2 confirms rule `sgr-000ce99c99f3fb957`, consistent with AWS Load Balancer Controller ownership. |
| `module.eks.module.eks_managed_node_group["hub"].aws_iam_role.this[0]` | `managed_policy_arns` | provider/state normalization / AWS relationship reflection | Attachments are separately managed by module node-group IAM attachment resources. |
| `module.eks.module.eks_managed_node_group["hub"].aws_launch_template.this[0]` | `security_group_names = []` | provider/state normalization | Empty list normalization. |
| `module.eks.module.kms.aws_kms_key.this[0]` | `tags = {}` | provider/state normalization | Empty tag map normalization. |

Normal plan result:

- `terraform plan -no-color`: `No changes`
- Create: 0
- Update: 0
- Destroy: 0
- No target addresses for create/update/destroy.

State preservation after both plans:

- Address count: 78
- Lineage/serial remained:
  `6372b788-77ab-ebd0-ca75-a657112df020` / `3912`
- Local state mtime remained `2026-06-08 09:01:59.304411456 +0900`
- Canonical state SHA-256 remained:
  `4083b9f05b2be0b1e3c6b292b269930f50d45efe91f4947dcc53563cc915172f`

Hub readiness judgment:

- Hub is ready for a future S3 backend migration from a Terraform plan
  perspective: Foundation S3 remote_state is configured, used outputs match,
  refresh-only completes, and the normal plan is clean.
- The refresh-only diff should be understood before any future refresh-only
  apply, but it does not imply a required AWS infrastructure change.
- User decision still useful: accept the AWS Load Balancer Controller-managed
  node security group ingress rule as expected external controller drift.

No apply, destroy, import, state push, state rm, state mv, refresh-only apply,
`terraform init -migrate-state`, Hub backend migration, data-pipeline work, or
reporting work was performed.

---

## 16. Hub S3 Backend Migration (2026-06-08)

The Hub read-only audit findings in section 15.6 were accepted as expected
drift/normalization. Scope was limited to `infra/hub`. Foundation was not
modified, and data-pipeline/reporting were not touched.

### 16.1 Pre-Migration Checks

- AWS account: `611058323802`
- Caller ARN: `arn:aws:iam::611058323802:user/student05`
- MFA temporary session indicator: `AWS_SESSION_TOKEN` present
- Commit: `a9fb5ab73cc3855667409631c0c2b11de8abc3bc`
- Initial status included:
  - `M infra/foundation/versions.tf`
  - `M infra/hub/foundation_remote_state.tf`
  - `?? TFSTATE_MIGRATION_AUDIT.md`
- Hub backend before migration: local default, no backend metadata file
- Hub address count before migration: 78
- Hub lineage/serial before migration:
  `6372b788-77ab-ebd0-ca75-a657112df020` / `3912`
- Candidate S3 key before migration:
  `aegis-pi/hub/terraform.tfstate` returned `404 Not Found`

Backend:

| Setting | Value |
|---|---|
| Bucket | `kjw-aegis-terraform-state` |
| Key | `aegis-pi/hub/terraform.tfstate` |
| Region | `ap-south-1` |
| Locking | `use_lockfile = true` |

### 16.2 Backup / Pre-Migration Plans

- Backup:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.pre-migration.tfstate`
- SHA-256:
  `c461e3c9a686d5cd5e54bd1f6b58e3ce2840cf5bd8ec33967ea32d128198c67d`
- Address list:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.pre-migration.addresses.txt`
- Address count: 78
- State JSON resource blocks: 57

Pre-migration plan artifacts:

- Refresh-only:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.pre-refresh-only.txt`
- Normal plan:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.pre-normal-plan.txt`

Pre-migration refresh-only completed successfully and showed the same accepted
provider/state normalization, AWS relationship reflection, and AWS Load
Balancer Controller-managed security group ingress described in section 15.6.
No deletion, replacement, ownership conflict, configuration mismatch, or AWS
API error was observed.

Pre-migration normal plan result: `No changes`; create/update/destroy were
`0/0/0`.

### 16.3 Backend Configuration / Migration

Added the S3 backend block to `infra/hub/versions.tf`.
`terraform fmt -check versions.tf` passed. The candidate key was rechecked
immediately before migration and still returned `404 Not Found`.

Executed:

```bash
terraform init -migrate-state -no-color
```

Terraform reported that the previous backend was local, the new S3 backend had
no existing state, and requested confirmation to copy the existing state. Only
that copy was approved. Initialization completed successfully.

S3 object creation was confirmed:

- Version ID: `NF7g2r7AyoETmIKKlTxmz.XJHEeLDCtK`
- Last modified: `2026-06-08T07:08:45Z`
- Content length: 204220 bytes
- Server-side encryption: `AES256`

Local files were not deleted:

- `terraform.tfstate`: present as zero-byte local placeholder
- `terraform.tfstate.backup`: present, 204223 bytes
- `terraform.tfvars`: present

### 16.4 Post-Migration State Comparison

Remote pull:

- File:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.post-migration.tfstate`
- SHA-256:
  `e348932f84d0a419eccebf56cc5a74d5e13896e9eb17cffd234a3f257c406f60`
- Address count: 78
- Address list comparison: exact match
- Remote lineage/serial:
  `942243df-98e2-f6f1-8527-b76d48dc30e1` / `1`
- State JSON resource blocks: 57

As with Foundation, Terraform reissued lineage and reset serial during
local-to-S3 migration. A first normalized comparison excluding only lineage,
serial, and `terraform_version` differed. Further localization showed:

- resource identities: exact match
- `outputs`: exact match
- `resources`: exact match
- full state after removing `lineage`, `serial`, `terraform_version`, and
  top-level `check_results`: exact match
- preserved body SHA-256:
  `26017abc10cb46976fc4c6eef32dfb644068eca5f0a25e3fea6a5b462f37a25d`

The difference is therefore limited to Terraform metadata/check results, not
managed resource state or outputs.

### 16.5 Post-Migration Plans

Post-migration plan artifacts:

- Refresh-only:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.post-refresh-only.txt`
- Normal plan:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.post-normal-plan.txt`

Post-migration refresh-only completed successfully and showed the same accepted
normalization/relationship/controller-managed drift as before migration. No
delete, replacement, ownership conflict, or AWS API error was observed.

Final normal plan result:

- `terraform plan -no-color`: `No changes`
- Create: 0
- Update: 0
- Destroy: 0
- No target addresses for create/update/destroy

Final state verification:

- Final remote state:
  `/tmp/aegis-tfstate-backups/hub.20260608-160644.final.tfstate`
- Final SHA-256:
  `349ed45e6db2eba152885f9de496a6df06c6a101b08abfa3f838cd9c344acc33`
- Final address count: 78
- Final lineage/serial:
  `942243df-98e2-f6f1-8527-b76d48dc30e1` / `1`
- Address list still matched the post-migration address list.
- Body excluding metadata/check results still matched the pre-migration backup.

Hub also continued to read Foundation outputs from the Foundation S3 remote
state. A console check read `admin_ui_domain_name`, `admin_ui_argocd_host`,
`admin_ui_grafana_host`, and `admin_ui_route53_zone_id`.

### 16.6 Source / Artifact Status

Intended source changes now include:

- `infra/foundation/versions.tf`
- `infra/hub/foundation_remote_state.tf`
- `infra/hub/versions.tf`
- `TFSTATE_MIGRATION_AUDIT.md`

Final status at this stage:

- modified: `infra/foundation/versions.tf`
- modified: `infra/hub/foundation_remote_state.tf`
- modified: `infra/hub/versions.tf`
- untracked: `TFSTATE_MIGRATION_AUDIT.md`

`.terraform/`, tfstate, tfstate backup, tfvars, plan, and credential files were
not added to Git. Hub local state and backup files were not deleted.

No `terraform apply`, `terraform destroy`, `terraform import`,
`terraform state push`, `terraform state rm`, `terraform state mv`,
refresh-only apply, S3 force overwrite, Foundation state change,
data-pipeline work, or reporting work was performed.

Hub migration is complete and verified. The next step is a separate
data-pipeline read-only audit before considering any data-pipeline backend
migration.

---

## 17. Data-Pipeline Read-Only Audit (2026-06-08)

Scope was limited to `infra/data-pipeline`. No data-pipeline S3 backend block
was added and no migration was performed. Foundation and Hub remote states were
not modified. Reporting was not touched.

### 17.1 Preflight / State Backup

- AWS account: `611058323802`
- Caller ARN: `arn:aws:iam::611058323802:user/student05`
- MFA temporary session indicator: present
- Commit: `a9fb5ab73cc3855667409631c0c2b11de8abc3bc`
- Starting Git status included:
  - `M infra/foundation/versions.tf`
  - `M infra/hub/foundation_remote_state.tf`
  - `M infra/hub/versions.tf`
  - `?? TFSTATE_MIGRATION_AUDIT.md`
- data-pipeline backend: local default; no backend metadata file
- local `terraform.tfstate`: present
- `terraform init -no-color`: success
- `terraform init -migrate-state`: not run

Backup:

- File: `/tmp/aegis-tfstate-backups/data-pipeline.20260608-161556.tfstate`
- SHA-256:
  `ab2e043de363113c3860511c949fee7ad094b110e860967b2adc50fe49445f60`
- Address list:
  `/tmp/aegis-tfstate-backups/data-pipeline.20260608-161556.addresses.txt`
- Address count: 84
- Lineage: `116be331-380e-8f94-3eb1-0421109b71ed`
- Serial: 204
- State JSON resource blocks: 82

Note: the earlier audit summary had listed 61 managed instances from older
local JSON inspection. The current authoritative local state has 84 Terraform
addresses.

### 17.2 Remote-State References

No `terraform_remote_state` data source exists in `infra/data-pipeline`.
Therefore no Foundation or Hub local-state path needed conversion to S3.
data-pipeline references Foundation-managed resources through AWS data sources
and variables, including:

- `data.aws_s3_bucket.data` using `var.data_bucket_name`
- `data.aws_dynamodb_table.factory_status` using
  `var.dynamodb_table_name`
- EKS cluster name inputs for cloud infra collectors

Remote-state output equality checks are not applicable for this root.

### 17.3 Refresh-Only Result

Refresh-only output:

`/tmp/aegis-tfstate-backups/data-pipeline.20260608-161556.refresh-only.txt`

`terraform plan -refresh-only -no-color` completed successfully. No resource
deletion, replacement, ownership conflict, or AWS API error was observed.

| Resource | Changed attributes | Classification | Notes |
|---|---|---|---|
| `aws_apigatewayv2_api.snapshot_presigner` | CORS header case changed to lowercase; `expose_headers = []` | provider/state normalization | AWS/API Gateway normalizes CORS header casing and empty lists. |
| `aws_apigatewayv2_integration.snapshot_presigner` | `request_parameters = {}`, `request_templates = {}` | provider/state normalization | Empty map normalization. |
| `aws_apigatewayv2_route.snapshot_presigner` | `authorization_scopes = []`, `request_models = {}` | provider/state normalization | Empty list/map normalization. |
| `aws_apigatewayv2_stage.snapshot_presigner` | `deployment_id`, `stage_variables = {}` | provider/state normalization / AWS relationship reflection | Auto-deploy stage has current deployment ID and empty variables. |
| `aws_eks_access_policy_association.cloud_infra_slow_collector_view` | `access_scope.namespaces = []` | provider/state normalization | Empty list normalization. |
| `aws_iam_role.cloud_infra_fast_collector` | inline policy projection changed | provider/state normalization plus actual AWS drift | The separately managed `aws_iam_role_policy.cloud_infra_fast_collector` also shows policy content drift. |
| `aws_iam_role.snapshot_presigner` | inline policy projection added | provider/state normalization / AWS relationship reflection | Inline policy is separately managed by `aws_iam_role_policy.snapshot_presigner`. |
| `aws_iam_role_policy.cloud_infra_fast_collector` | policy includes `DataStoreInventoryRead` in AWS/state refresh | actual AWS drift / configuration mismatch candidate | Normal plan would remove this statement from the managed policy. |
| `aws_lambda_function.cloud_infra_fast_collector` | code hash, last modified, source size, and extra env vars | actual AWS drift / configuration mismatch candidate | AWS has newer code/env than local config/archive result. |
| `aws_lambda_function.cloud_infra_slow_collector` | code hash, last modified, source size | actual AWS drift / configuration mismatch candidate | AWS has newer code than local config/archive result. |
| `aws_lambda_function.risk_alert_dispatcher` | code hash, last modified, source size | actual AWS drift / configuration mismatch candidate | AWS has newer code than local config/archive result. |
| `aws_lambda_function.snapshot_presigner` | `layers = []` | provider/state normalization | Empty list normalization. |

Refresh-only also caused the local `archive_file` data sources to regenerate
ignored Lambda zip artifacts under `infra/data-pipeline/`. These files are
ignored by `.gitignore` and were not added to Git:

- `lambda_cloud_infra_collector.zip`
- `lambda_data_processor.zip`
- `lambda_graph_metrics_aggregator.zip`
- `lambda_risk_alert_dispatcher.zip`
- `lambda_snapshot_presigner.zip`

### 17.4 Normal Plan Result / Stop Condition

Normal plan output:

`/tmp/aegis-tfstate-backups/data-pipeline.20260608-161556.normal-plan.txt`

`terraform plan -no-color` completed, but it was not clean:

- Create: 0
- Update: 7
- Destroy: 0

Update targets:

| Address | Planned action | Reason shown by plan |
|---|---|---|
| `aws_iam_role_policy.cloud_infra_fast_collector` | update in-place | Remove `DataStoreInventoryRead` from the policy. |
| `aws_iam_role_policy.cloud_infra_fast_collector_scheduler` | update in-place | Policy JSON becomes known after apply because it depends on a Lambda with pending changes. |
| `aws_iam_role_policy.cloud_infra_slow_collector_scheduler` | update in-place | Policy JSON becomes known after apply because it depends on a Lambda with pending changes. |
| `aws_lambda_function.cloud_infra_fast_collector` | update in-place | Change source code hash and remove extra env vars: `CLOUDFRONT_DISTRIBUTION_ID`, `DLQ_QUEUE_NAME`, `RDS_DB_INSTANCE_ID`, `REDIS_REPLICATION_GROUP_ID`. |
| `aws_lambda_function.cloud_infra_slow_collector` | update in-place | Change source code hash. |
| `aws_lambda_function.risk_alert_dispatcher` | update in-place | Change source code hash. |
| `aws_lambda_function.snapshot_presigner` | update in-place | Change source code hash. |

This violates the migration precondition that the normal plan must be
`No changes`. No apply was run.

### 17.5 State / Artifact Preservation

The local state file did not change during init or plan execution:

- State mtime remained `2026-06-08 11:15:58.698757329 +0900`
- State size remained 219642 bytes
- State SHA-256 remained
  `e1bf20daac0dc7750096b90fa67aae6df2e8e20c6e5898fd48ba8c976b3270ee`
- Canonical state SHA-256 matched the fresh backup:
  `1f12e12ae0ead001a97690577403b2788aeb00d02abf924ce37983de2c61cb57`
- Address count remained 84
- Lineage/serial remained:
  `116be331-380e-8f94-3eb1-0421109b71ed` / `204`

Ignored local artifacts present in `infra/data-pipeline` include existing
`*.tfplan`, `terraform.tfstate`, `terraform.tfstate.backup`, `terraform.tfvars`,
and the regenerated Lambda zip files. None were added to Git.

### 17.6 Migration Readiness

data-pipeline is not ready for S3 backend migration yet.

Reasons:

- Normal plan proposes 7 in-place updates.
- Lambda code/package hashes in AWS and local archive outputs differ.
- `aws_lambda_function.cloud_infra_fast_collector` has extra AWS environment
  variables not represented in the current Terraform configuration.
- `aws_iam_role_policy.cloud_infra_fast_collector` has an AWS policy statement
  not represented in current Terraform configuration.

User decisions needed before migration:

- Decide whether the AWS Lambda code/env changes are authoritative and should
  be reconciled into source/config/state before migration.
- Decide whether `DataStoreInventoryRead` belongs in Terraform configuration
  for `cloud_infra_fast_collector`.
- Decide whether the existing local `*.tfplan` files are still useful
  operational artifacts; they are ignored and were not modified by this audit.

No `terraform apply`, `terraform destroy`, `terraform import`,
`terraform state push`, `terraform state rm`, `terraform state mv`,
refresh-only apply, S3 backend migration, local state deletion, Foundation/Hub
state change, reporting work, or AWS resource change was performed.

### 17.7 Drift Detail Investigation

Follow-up scope: investigate the 7 normal-plan updates only. No Terraform
source/config was changed. No AWS resource was changed. Lambda environment
values were not printed or recorded; only key names and presence were audited.
Downloaded deployment packages were stored only under `/tmp/aegis-lambda-audit`.

AWS identity remained `arn:aws:iam::611058323802:user/student05`. data-pipeline
local state remained unchanged:

- SHA-256:
  `e1bf20daac0dc7750096b90fa67aae6df2e8e20c6e5898fd48ba8c976b3270ee`
- Address count: 84
- Lineage/serial:
  `116be331-380e-8f94-3eb1-0421109b71ed` / `204`
- mtime/size:
  `2026-06-08 11:15:58.698757329 +0900` / 219642 bytes

Git history findings:

- `beae529 sync lambda code from deployed aws` added CloudFront, Redis, RDS,
  and DLQ collection code to `apps/cloud-infra-collector/`, including the
  config keys used by the extra AWS environment variables.
- The same code path uses Redis/RDS APIs that require
  `elasticache:DescribeReplicationGroups` and `rds:DescribeDBInstances`.
- `d41f7db Update image snapshot pipeline docs` changed
  `apps/snapshot-presigner/README.md`, which is currently included in the
  SnapshotPresigner Lambda zip.

Code/package comparison:

| Lambda | AWS CodeSha256 | Terraform state hash | Current archive hash | Code/content finding | Classification |
|---|---|---|---|---|---|
| CloudInfraFastCollector | `/FapoibjVCVSbJMI8n/LeJx/0K6UrE3U6MazSzCUezE=` | `uKTpHMetb7RjxE10vgYc1UYDvl1BAY+JTJyXxZNPQAQ=` | `uGZmR1ROx9ZIWvzyDS54oNX81X1ZiQKSqb2lgVGIyi8=` | AWS deployed zip and current archive have identical file contents; file order/timestamps differ. | packaging/hash-only difference |
| CloudInfraSlowCollector | `/FapoibjVCVSbJMI8n/LeJx/0K6UrE3U6MazSzCUezE=` | `uKTpHMetb7RjxE10vgYc1UYDvl1BAY+JTJyXxZNPQAQ=` | `uGZmR1ROx9ZIWvzyDS54oNX81X1ZiQKSqb2lgVGIyi8=` | Same package as fast collector; file contents match AWS, metadata/order differ. | packaging/hash-only difference |
| RiskAlertDispatcher | `/GosrfobqNAMqmWFfeTDPky/ij2LmsPQF8b83e7fDrw=` | `VY5FXzW5C9j327lpyq2sYCIB0Agnpgrr7itJnlvkG1M=` | `U3U9yDvlkS+uD69X3ogQJnlqgLQ1brHVbM6TPvQ2TMQ=` | AWS deployed zip and current archive have identical file contents; file order/timestamps differ. | packaging/hash-only difference |
| SnapshotPresigner | `O5C/uVqVU4ETXU25wjIkHcvONShkSDsSBWgvaYahtAk=` | `O5C/uVqVU4ETXU25wjIkHcvONShkSDsSBWgvaYahtAk=` | `Z8WcPwQzPsZ6CD29Vygk9ZGALUNCDRUVuCfLezBPw10=` | Runtime file `lambda_function.py` matches AWS; included `README.md` differs after docs update. | non-runtime package content difference |

Packaging notes:

- CloudInfra deployed/current zips both contain 14 files, no pycache, no tests.
- RiskAlert deployed/current zips both contain 8 files, no pycache, no tests.
- SnapshotPresigner deployed/current zips both contain 2 files. The runtime
  Python file matches; README differs.
- Current `archive_file` output uses deterministic timestamps such as
  `2049-01-01`, while older deployed packages use original timestamps and
  different file order. This explains hash drift without runtime code drift for
  CloudInfra and RiskAlert.

Environment variable audit:

| Lambda | AWS env keys vs Terraform env keys | Code usage | Assessment |
|---|---|---|---|
| CloudInfraFastCollector | AWS has four extra keys: `CLOUDFRONT_DISTRIBUTION_ID`, `DLQ_QUEUE_NAME`, `RDS_DB_INSTANCE_ID`, `REDIS_REPLICATION_GROUP_ID` | Current code reads all four keys, with defaults. | likely intended operating configuration; Terraform is missing explicit env management |
| CloudInfraSlowCollector | key sets match | current code uses configured slow collector keys | no env drift |
| RiskAlertDispatcher | key sets match | current config manages all audited keys | no env drift |
| SnapshotPresigner | key sets match | current config manages all audited keys | no env drift |

IAM policy audit:

| Policy | AWS current | Terraform current | Assessment |
|---|---|---|---|
| `aws_iam_role_policy.cloud_infra_fast_collector` | Contains `DataStoreInventoryRead` with `elasticache:DescribeReplicationGroups` and `rds:DescribeDBInstances` on `*`. | Missing this statement. | Current CloudInfra code uses both APIs, so AWS policy is functionally required unless the code path is intentionally removed. |
| `aws_iam_role_policy.cloud_infra_fast_collector_scheduler` | Single `InvokeCloudInfraFastCollector` statement. | Same logical policy. | Normal-plan diff is a known-after-apply chain from pending Lambda update, not independent drift. |
| `aws_iam_role_policy.cloud_infra_slow_collector_scheduler` | Single `InvokeCloudInfraSlowCollector` statement. | Same logical policy. | Normal-plan diff is a known-after-apply chain from pending Lambda update, not independent drift. |

Target-by-target decision table:

| Target | AWS current | Code/Terraform current | Difference cause | Recommended authoritative side | Follow-up |
|---|---|---|---|---|---|
| `aws_iam_role_policy.cloud_infra_fast_collector` | Has `DataStoreInventoryRead` for Redis/RDS describe APIs. | Terraform policy lacks that statement. | Terraform config was not updated with permissions required by current CloudInfra code. | AWS/code behavior should be reflected in Terraform. | Add the statement to Terraform config, then rerun plan. |
| `aws_iam_role_policy.cloud_infra_fast_collector_scheduler` | Logical invoke policy matches. | Logical invoke policy matches. | Dependent data source becomes known after Lambda update. | Neither side needs independent change. | Should disappear after Lambda drift is resolved. |
| `aws_iam_role_policy.cloud_infra_slow_collector_scheduler` | Logical invoke policy matches. | Logical invoke policy matches. | Dependent data source becomes known after Lambda update. | Neither side needs independent change. | Should disappear after Lambda drift is resolved. |
| `aws_lambda_function.cloud_infra_fast_collector` | Deployed code content matches current repo archive; AWS has four extra env keys. | Terraform archive content matches deployed code, but zip metadata hash differs; Terraform env omits four keys. | Packaging/hash-only drift plus missing env management. | AWS/code behavior should be reflected in Terraform; packaging reproducibility should be addressed. | Add env keys to Terraform without exposing values in docs, and consider deterministic packaging policy. |
| `aws_lambda_function.cloud_infra_slow_collector` | Deployed code content matches current repo archive. | Current archive content matches deployed code, but zip metadata hash differs. | Packaging/hash-only drift. | Current source and AWS runtime code are equivalent. | Fix/accept packaging hash churn before migration; no source rollback indicated. |
| `aws_lambda_function.risk_alert_dispatcher` | Deployed code content matches current repo archive. | Current archive content matches deployed code, but zip metadata hash differs. | Packaging/hash-only drift. | Current source and AWS runtime code are equivalent. | Fix/accept packaging hash churn before migration; no source rollback indicated. |
| `aws_lambda_function.snapshot_presigner` | Deployed runtime Python file matches current repo; package includes older README. | Current archive includes updated README, changing hash. | Non-runtime README is included in deployment package. | Packaging should exclude non-runtime docs or accept redeploy. | Prefer excluding README/non-runtime files from the Lambda archive, then rerun plan. |

Overall recommendation:

- Do not treat the Lambda code hash drift as proof that AWS has unknown code.
  For CloudInfra and RiskAlert, deployed runtime file contents match the
  current repo archive.
- Prefer "AWS current operating config into Terraform" for CloudInfraFast
  env/IAM, because current code uses those inputs and permissions.
- Prefer "packaging reproducibility first" for Lambda hash churn, especially
  excluding non-runtime files from SnapshotPresigner and avoiding metadata-only
  redeploys.
- After those decisions/changes, rerun data-pipeline plans until normal plan is
  `No changes`; only then consider data-pipeline S3 backend migration.

No apply, import, state mutation, Lambda update, IAM update, backend migration,
or reporting work was performed.

### 17.8 Data-Pipeline Drift Reconciliation Config Update

Timestamp: `2026-06-08 16:36:25 KST`

Scope: data-pipeline Terraform/source packaging only. No Terraform apply,
destroy, import, state push/rm/mv, refresh-only apply, backend migration,
Foundation/Hub state change, reporting work, Lambda update, or IAM update was
performed. No plan file was written. AWS account remained `611058323802`.

Changes made:

| File | Change |
|---|---|
| `infra/data-pipeline/cloud_infra_fast_collector.tf` | Added optional Terraform-managed env keys for CloudInfraFastCollector; added `DataStoreInventoryRead`; set `archive_file.output_file_mode = "0644"` for the CloudInfra collector zip. |
| `infra/data-pipeline/variables.tf` | Added nullable string variables for `CLOUDFRONT_DISTRIBUTION_ID`, `DLQ_QUEUE_NAME`, `RDS_DB_INSTANCE_ID`, and `REDIS_REPLICATION_GROUP_ID` injection. Defaults are `null`; no environment-specific values are committed. |
| `infra/data-pipeline/risk_alert_dispatcher.tf` | Set `archive_file.output_file_mode = "0644"` for deterministic file permissions. |
| `infra/data-pipeline/snapshot_presigner.tf` | Changed packaging from whole source directory to runtime `lambda_function.py` only and set `archive_file.output_file_mode = "0644"`. README/non-runtime files are no longer package inputs. |
| `infra/data-pipeline/terraform.tfvars.example` | Added commented placeholders documenting where operators should set the four CloudInfraFastCollector values via tfvars or `TF_VAR_*`. |

Environment variable handling:

- The four AWS operating env keys are now modeled as Terraform variables:
  `cloud_infra_fast_collector_cloudfront_distribution_id`,
  `cloud_infra_fast_collector_dlq_queue_name`,
  `cloud_infra_fast_collector_rds_db_instance_id`, and
  `cloud_infra_fast_collector_redis_replication_group_id`.
- Actual values were not printed, recorded, committed, or written into source.
- For verification only, current AWS values were injected through process-local
  `TF_VAR_*` environment variables and plan output was redacted for those keys.

IAM reconciliation:

- `DataStoreInventoryRead` was added to
  `data.aws_iam_policy_document.cloud_infra_fast_collector`.
- Actions:
  `elasticache:DescribeReplicationGroups`,
  `rds:DescribeDBInstances`.
- Resource: `*`.
- This matches the current CloudInfra fast collector code paths that read Redis
  replication group and RDS instance inventory.

Packaging reconciliation:

- CloudInfra and RiskAlert archive entries now pin `output_file_mode = "0644"`
  to avoid permission-bit hash churn.
- SnapshotPresigner now packages only `apps/snapshot-presigner/lambda_function.py`.
  The README/docs file that caused non-runtime hash drift is excluded by
  construction.
- Remaining Lambda package hash diffs are expected to require either a future
  approved Lambda deploy/apply to move AWS to the deterministic package hashes,
  or an explicit decision to preserve older AWS zip metadata hashes. The latter
  is not recommended because Terraform `archive_file` is now producing the
  reproducible source package.

Validation and plan results:

| Check | Result |
|---|---|
| `terraform fmt -check` | Passed |
| `terraform init -no-color` | Passed; local backend retained; no migrate-state |
| `terraform validate -no-color` | Passed |
| `terraform plan -refresh-only -no-color` | Succeeded; no apply; same accepted normalization/drift classes, plus redacted CloudInfraFast env reconciliation visible in refresh-only state comparison |
| `terraform plan -no-color` | `Plan: 0 to add, 6 to change, 0 to destroy` |

Normal plan after reconciliation:

| Target | Remaining reason | Classification |
|---|---|---|
| `aws_lambda_function.cloud_infra_fast_collector` | Current deterministic archive hash differs from both stale state hash and older deployed AWS zip hash. Runtime file contents were previously confirmed equivalent. | packaging/hash-only pending deploy |
| `aws_lambda_function.cloud_infra_slow_collector` | Same CloudInfra archive as fast collector. | packaging/hash-only pending deploy |
| `aws_lambda_function.risk_alert_dispatcher` | Current deterministic archive hash differs from stale state/AWS package metadata; runtime file contents were previously confirmed equivalent. | packaging/hash-only pending deploy |
| `aws_lambda_function.snapshot_presigner` | Package now contains runtime Python only; current desired hash intentionally differs from deployed package that included older README metadata/content. | packaging cleanup pending deploy |
| `aws_iam_role_policy.cloud_infra_fast_collector_scheduler` | Known-after-apply chain from pending CloudInfraFast Lambda update. | dependent scheduler policy projection |
| `aws_iam_role_policy.cloud_infra_slow_collector_scheduler` | Known-after-apply chain from pending CloudInfraSlow Lambda update. | dependent scheduler policy projection |

Drift resolved by config update:

- `aws_iam_role_policy.cloud_infra_fast_collector` is no longer in the normal
  plan when the four CloudInfraFast operating values are supplied.
- CloudInfraFast environment drift is no longer in the normal plan when the
  four values are supplied through `TF_VAR_*`.
- SnapshotPresigner README/non-runtime package input is removed.

State preservation:

- `infra/data-pipeline/terraform.tfstate` SHA-256 remained
  `e1bf20daac0dc7750096b90fa67aae6df2e8e20c6e5898fd48ba8c976b3270ee`.
- mtime/size remained `2026-06-08 11:15:58.698757329 +0900` / 219642 bytes.
- Address count remained 84.

Migration readiness:

data-pipeline is improved but still not ready for S3 backend migration because
the normal plan is not yet `No changes`. The remaining 6 changes are explained
and contain no create/destroy/replacement, but an explicit user decision is
still needed:

- Approve a future Terraform apply/Lambda deploy to move AWS to the current
  deterministic package hashes, then rerun plans until `No changes`; or
- Choose a different packaging/hash strategy if preserving the older deployed
  zip metadata is required.

### 17.9 Data-Pipeline S3 Backend Migration

Timestamp: `2026-06-08 16:42 KST`

User accepted the remaining data-pipeline normal plan as expected pending
changes before migration:

- Create: 0
- Update: 6
- Destroy: 0
- Lambda package hash updates:
  `aws_lambda_function.cloud_infra_fast_collector`,
  `aws_lambda_function.cloud_infra_slow_collector`,
  `aws_lambda_function.risk_alert_dispatcher`,
  `aws_lambda_function.snapshot_presigner`
- Dependent scheduler IAM known-after-apply updates:
  `aws_iam_role_policy.cloud_infra_fast_collector_scheduler`,
  `aws_iam_role_policy.cloud_infra_slow_collector_scheduler`

No Terraform apply, destroy, import, refresh-only apply, state push/rm/mv,
S3 object overwrite, local state/backup deletion, Foundation/Hub state change,
reporting work, Lambda update, IAM update, or environment value disclosure was
performed.

AWS/session and source context:

- AWS account: `611058323802`
- AWS ARN: `arn:aws:iam::611058323802:user/student05`
- Git commit: `a9fb5ab73cc3855667409631c0c2b11de8abc3bc`
- Pre-migration local state address count: 84
- Pre-migration lineage/serial:
  `116be331-380e-8f94-3eb1-0421109b71ed` / `204`

Backend added to `infra/data-pipeline/versions.tf`:

```hcl
backend "s3" {
  bucket       = "kjw-aegis-terraform-state"
  key          = "aegis-pi/data-pipeline/terraform.tfstate"
  region       = "ap-south-1"
  use_lockfile = true
}
```

Backup and candidate key checks:

| Item | Result |
|---|---|
| Fresh backup | `/tmp/aegis-tfstate-backups/data-pipeline.20260608-163941.pre-migration.tfstate` |
| Backup SHA-256 | `ab2e043de363113c3860511c949fee7ad094b110e860967b2adc50fe49445f60` |
| Candidate S3 key before migration | `404 Not Found`; empty candidate |
| Backend bucket/key/region | `s3://kjw-aegis-terraform-state/aegis-pi/data-pipeline/terraform.tfstate`, `ap-south-1` |

Pre-migration plan checks:

| Check | Result |
|---|---|
| `terraform plan -refresh-only -no-color` | Succeeded; no apply; accepted drift/normalization classes only |
| `terraform plan -no-color` | `Plan: 0 to add, 6 to change, 0 to destroy` |
| Normal plan targets | The accepted 4 Lambda package hash updates and 2 scheduler IAM known-after-apply updates only |
| CloudInfraFast env/IAM drift | Did not reappear when operating env values were supplied through process-local `TF_VAR_*` variables |
| Create/destroy/replacement | None |

Migration execution:

- Added S3 backend block to `infra/data-pipeline/versions.tf`.
- `terraform fmt -check`: passed.
- `terraform validate -no-color`: passed.
- Ran `terraform init -migrate-state -no-color`.
- Terraform reported no existing state in the new S3 backend and asked whether
  to copy the pre-existing local state; answered `yes`.
- Hub/Foundation state and reporting were not touched.

Post-migration state checks:

| Item | Result |
|---|---|
| S3 object exists | Yes |
| S3 version ID | `Xe1Su9GP6dNPTohAWxKNQ2osXRezrhjZ` |
| S3 content length | 219640 bytes |
| Post-migration address count | 84 |
| Post-migration lineage/serial | `6b78ee1f-782b-b060-fb63-a90a1ad533c5` / `1` |
| Lineage/serial behavior | Reissued/reset as observed for Foundation and Hub; accepted because state body was preserved |
| Resource body comparison | Matches backup |
| Outputs body comparison | Matches backup |
| Metadata-excluded state body comparison | Matches backup |

The local `infra/data-pipeline/terraform.tfstate` file is now a zero-byte
placeholder and `infra/data-pipeline/terraform.tfstate.backup` remains present.
No local state or backup file was deleted.

Post-migration plan checks:

| Check | Result |
|---|---|
| `terraform plan -refresh-only -no-color` | Succeeded; no apply; same accepted drift/normalization classes |
| `terraform plan -no-color` | `Plan: 0 to add, 6 to change, 0 to destroy` |
| Post-migration normal plan targets | Same 4 Lambda package hash updates and 2 scheduler IAM known-after-apply updates as pre-migration |
| CloudInfraFast env/IAM drift | Did not reappear |
| Create/destroy/replacement | None |

Migration result:

data-pipeline S3 backend migration succeeded. The authoritative state is now:

- `s3://kjw-aegis-terraform-state/aegis-pi/data-pipeline/terraform.tfstate`
- Region: `ap-south-1`
- Locking: `use_lockfile = true`

The state migration is complete, but the pending package changes were not
applied. Next step requires separate approval: apply the 4 Lambda package hash
updates and dependent scheduler IAM projections, then verify final
data-pipeline normal plan reaches `No changes`.

### 17.10 Data-Pipeline Approved Saved-Plan Apply

Timestamp: `2026-06-08 16:53:07 KST`

Scope: apply only the approved data-pipeline saved plan after S3 state
migration. No direct apply without a saved plan was performed. No `-target` was
used. No destroy, import, refresh-only apply, state push/rm/mv, S3 state manual
replacement/deletion, Foundation/Hub state change, reporting work, or
environment value disclosure was performed.

Pre-apply checks:

| Check | Result |
|---|---|
| AWS account | `611058323802` |
| AWS ARN | `arn:aws:iam::611058323802:user/student05` |
| Backend | `s3`, bucket `kjw-aegis-terraform-state`, key `aegis-pi/data-pipeline/terraform.tfstate`, region `ap-south-1` |
| State address count | 84 |
| State lineage/serial | `6b78ee1f-782b-b060-fb63-a90a1ad533c5` / `1` |
| Pre-apply S3 version ID | `Xe1Su9GP6dNPTohAWxKNQ2osXRezrhjZ` |
| Pre-apply state backup | `/tmp/aegis-tfstate-backups/data-pipeline.20260608-164828.pre-approved-apply.tfstate` |
| Backup SHA-256 | `b4208b3b64f0fbfb7453b291e54e952107f3af48995fbb45907a18e09d6e3838` |
| `terraform fmt -check` | Passed |
| `terraform validate -no-color` | Passed |

CloudInfraFast operating environment values were supplied through process-local
`TF_VAR_*` variables only. Actual values were not printed, written to source,
or recorded in this document.

Saved plan:

| Item | Result |
|---|---|
| Saved plan path | `/tmp/aegis-data-pipeline-approved-20260608-164903.tfplan` |
| Saved plan JSON path | `/tmp/aegis-data-pipeline-approved-20260608-164903.tfplan.json` |
| JSON inspection | Passed |
| Create/update/delete/replace | `0 / 6 / 0 / 0` |
| CloudInfraFast direct IAM drift | 0 changes |
| Backend/state related changes | 0 changes |

Approved saved-plan managed changes:

| Address | Action |
|---|---|
| `aws_lambda_function.cloud_infra_fast_collector` | update |
| `aws_lambda_function.cloud_infra_slow_collector` | update |
| `aws_lambda_function.risk_alert_dispatcher` | update |
| `aws_lambda_function.snapshot_presigner` | update |
| `aws_iam_role_policy.cloud_infra_fast_collector_scheduler` | update projection |
| `aws_iam_role_policy.cloud_infra_slow_collector_scheduler` | update projection |

Apply result:

- Command used: `terraform apply -no-color /tmp/aegis-data-pipeline-approved-20260608-164903.tfplan`
- Terraform result: `Apply complete! Resources: 0 added, 4 changed, 0 destroyed.`
- The four actual remote changes were the Lambda package updates. The two
  scheduler IAM entries were known-after-apply projections from Lambda data
  dependencies; post-apply IAM reads confirmed the invoke policies remained
  correct and final Terraform plan reached `No changes`.

Post-apply Lambda status:

| Lambda | State | LastUpdateStatus | CodeSha256 |
|---|---|---|---|
| `AEGIS-Lambda-CloudInfraFastCollector` | Active | Successful | `uGZmR1ROx9ZIWvzyDS54oNX81X1ZiQKSqb2lgVGIyi8=` |
| `AEGIS-Lambda-CloudInfraSlowCollector` | Active | Successful | `uGZmR1ROx9ZIWvzyDS54oNX81X1ZiQKSqb2lgVGIyi8=` |
| `AEGIS-Lambda-RiskAlertDispatcher` | Active | Successful | `U3U9yDvlkS+uD69X3ogQJnlqgLQ1brHVbM6TPvQ2TMQ=` |
| `AEGIS-Lambda-SnapshotPresigner` | Active | Successful | `q8X/wza1SqCRhyqdqZ/xt5tyJxtBJvgWkNoGYwVDiTk=` |

Scheduler IAM verification:

| Policy | Verification |
|---|---|
| `AEGIS-IAMPolicy-Scheduler-CloudInfraFastCollector` | Allows `lambda:InvokeFunction` on `arn:aws:lambda:ap-south-1:611058323802:function:AEGIS-Lambda-CloudInfraFastCollector` |
| `AEGIS-IAMPolicy-Scheduler-CloudInfraSlowCollector` | Allows `lambda:InvokeFunction` on `arn:aws:lambda:ap-south-1:611058323802:function:AEGIS-Lambda-CloudInfraSlowCollector` |

Post-apply state and plan checks:

| Check | Result |
|---|---|
| Post-apply S3 version ID | `lzAyUrWsiNEBD9UdIV4w7p2AScwr0I4l` |
| Post-apply S3 content length | 221330 bytes |
| State address count | 84 |
| State lineage/serial | `6b78ee1f-782b-b060-fb63-a90a1ad533c5` / `2` |
| `terraform plan -refresh-only -no-color` | `No changes. Your infrastructure still matches the configuration.` |
| `terraform plan -no-color` | `No changes. Your infrastructure matches the configuration.` |

Result:

data-pipeline is now aligned with Terraform configuration after the approved
Lambda package apply. S3 remote state remains authoritative and locked via the
S3 backend. data-pipeline final normal plan is `No changes`.

## 18. Reporting Read-Only Audit

Timestamp: `2026-06-08 16:57:55 KST`

Scope: `infra/reporting` read-only audit only. No reporting apply, destroy,
import, state push/rm/mv, refresh-only apply, S3 backend migration, local state
deletion/modification, Foundation/Hub/Data-Pipeline state change, AWS resource
change, secret/env value disclosure, or tfstate/tfvars/plan artifact Git add was
performed.

### 18.1 Session and Git Context

| Item | Result |
|---|---|
| AWS account | `611058323802` |
| AWS ARN | `arn:aws:iam::611058323802:user/student05` |
| Git commit | `a9fb5ab73cc3855667409631c0c2b11de8abc3bc` |
| Reporting backend | Local; no backend block and no backend metadata in `.terraform/terraform.tfstate` before migration audit |

Git status at audit time showed the existing Foundation/Hub/Data-Pipeline
migration/config files and this audit document as modified/untracked. No
reporting source file was modified by this audit.

### 18.2 Local State and Backup

| Item | Result |
|---|---|
| Local state file | `infra/reporting/terraform.tfstate` exists |
| Address count | 32 |
| Lineage/serial | `fab4c44a-dd32-cc33-9a68-5404dc2b4aed` / `157` |
| State SHA-256 | `82f22cc5c27d9200378d92f7da87a7162948ca2d590a53b8db7941f4778ae5ce` |
| State mtime/size | `2026-06-02 17:49:16.837905651 +0900` / 99897 bytes |
| Fresh backup | `/tmp/aegis-tfstate-backups/reporting.20260608-165611.read-only-audit.tfstate` |
| Backup SHA-256 | `7265fd3f81de27b94659dba6690ef5d10683d43512e75986d756f56cd3a0c501` |

After `terraform init`, refresh-only plan, and normal plan, the local state file
remained unchanged:

- SHA-256:
  `82f22cc5c27d9200378d92f7da87a7162948ca2d590a53b8db7941f4778ae5ce`
- mtime/size:
  `2026-06-02 17:49:16.837905651 +0900` / 99897 bytes
- Address count: 32
- Lineage/serial:
  `fab4c44a-dd32-cc33-9a68-5404dc2b4aed` / `157`

### 18.3 Cross-Root State Dependencies

No `terraform_remote_state` data source was found in `infra/reporting`.

Reporting does not read Foundation, Hub, or Data-Pipeline Terraform state
directly. The module contract is:

| Shared dependency | Mechanism | Source |
|---|---|---|
| Data bucket | `var.data_bucket_name` and `data.aws_s3_bucket.data` | Foundation-managed bucket name supplied by variable |
| Account identity | `data.aws_caller_identity.current` | AWS provider |
| Region | `var.aws_region` | Terraform variable/provider |

The reporting README explicitly states that this root intentionally does not
read foundation remote state and looks up the existing data bucket through
`var.data_bucket_name` and `data.aws_s3_bucket`. No S3 remote_state conversion
is required before reporting backend migration.

Note: the README still contains historical text saying the reporting stack was
later destroyed to stop scheduled cost. Current refresh-only and normal plans
show the AWS resources exist and match Terraform state/configuration, so that
README status appears stale and should be corrected separately if desired.

### 18.4 Init, Fmt, Validate

| Check | Result |
|---|---|
| `terraform init -no-color` | Passed; local backend retained; no `-migrate-state` |
| `terraform fmt -check` | Passed |
| `terraform validate -no-color` | Passed |
| Providers | `hashicorp/archive ~> 2.7`, `hashicorp/aws ~> 6.0` |

### 18.5 Refresh-Only Plan

`terraform plan -refresh-only -no-color` completed successfully:

- Result: `No changes. Your infrastructure still matches the configuration.`
- Provider/state normalization: none
- Expected external drift: none
- Actual AWS drift: none
- Configuration mismatch: none
- Ownership conflict: none
- Additional confirmation needed: README lifecycle/status text is stale, but
  this is documentation drift, not Terraform/AWS infrastructure drift.

### 18.6 Normal Plan

`terraform plan -no-color` completed successfully:

- Result: `No changes. Your infrastructure matches the configuration.`
- Create/update/destroy/replacement: `0 / 0 / 0 / 0`
- Changed addresses: none

### 18.7 Migration Readiness

Reporting is ready for a future S3 backend migration from an infrastructure and
state consistency perspective:

- Local state owner is clear.
- Address count is stable at 32.
- Refresh-only plan is clean.
- Normal plan is clean.
- No Terraform remote_state dependency needs to be converted first.
- Local state was preserved during read-only audit.

Required next-step decisions before actual migration:

- Confirm the desired backend target, expected to follow the established
  pattern:
  `s3://kjw-aegis-terraform-state/aegis-pi/reporting/terraform.tfstate`,
  region `ap-south-1`, `use_lockfile = true`.
- Optionally update the reporting README lifecycle/status text because it no
  longer matches observed AWS/Terraform state.

## 19. Reporting S3 Backend Migration

Timestamp: `2026-06-08 17:06:24 KST`

Scope: `infra/reporting` S3 backend migration and verification only, plus a
minimal reporting README status correction. No Terraform apply, destroy,
import, refresh-only apply, state push/rm/mv, S3 object force overwrite/delete,
local state/backup deletion, Foundation/Hub/Data-Pipeline state change, or AWS
resource change was performed.

### 19.1 Preconditions

| Item | Result |
|---|---|
| AWS account | `611058323802` |
| AWS ARN | `arn:aws:iam::611058323802:user/student05` |
| Git commit | `a9fb5ab73cc3855667409631c0c2b11de8abc3bc` |
| Pre-migration address count | 32 |
| Pre-migration lineage/serial | `fab4c44a-dd32-cc33-9a68-5404dc2b4aed` / `157` |
| Candidate S3 key | `404 Not Found`; empty candidate |
| Fresh backup | `/tmp/aegis-tfstate-backups/reporting.20260608-170200.pre-migration.tfstate` |
| Backup SHA-256 | `7265fd3f81de27b94659dba6690ef5d10683d43512e75986d756f56cd3a0c501` |

The first pre-migration refresh-only attempt collided with a concurrently
running normal plan against the same local state lock. No lock bypass was used.
The normal plan completed cleanly, then refresh-only was retried alone and
completed cleanly.

Pre-migration checks:

| Check | Result |
|---|---|
| `terraform fmt -check` | Passed |
| `terraform validate -no-color` | Passed |
| `terraform plan -refresh-only -no-color` | `No changes. Your infrastructure still matches the configuration.` |
| `terraform plan -no-color` | `No changes. Your infrastructure matches the configuration.` |

### 19.2 Backend Configuration

Added to `infra/reporting/versions.tf`:

```hcl
backend "s3" {
  bucket       = "kjw-aegis-terraform-state"
  key          = "aegis-pi/reporting/terraform.tfstate"
  region       = "ap-south-1"
  use_lockfile = true
}
```

`terraform fmt -check` and `git diff --check` passed before migration.

### 19.3 Migration Execution

Ran `terraform init -migrate-state -no-color`.

Terraform reported no existing state in the newly configured S3 backend and
asked whether to copy the pre-existing local state. Answered `yes` to copy the
local reporting state into the specified empty S3 key.

No other root was migrated or modified during this step.

### 19.4 Post-Migration State Verification

| Item | Result |
|---|---|
| Authoritative backend | `s3://kjw-aegis-terraform-state/aegis-pi/reporting/terraform.tfstate` |
| Region | `ap-south-1` |
| Locking | `use_lockfile = true` |
| S3 object exists | Yes |
| S3 version ID | `hHhuwPUFqQfWbdtNXBfR8GxcNkNeyvJu` |
| S3 content length | 99895 bytes |
| Post-migration address count | 32 |
| Post-migration lineage/serial | `345951f9-f0c5-4696-df6f-fced093edc93` / `1` |
| Lineage/serial behavior | Reissued/reset as observed for Foundation, Hub, and Data-Pipeline |
| Address list comparison | Matches backup |
| Resource body comparison | Matches backup |
| Outputs body comparison | Matches backup |
| Metadata-excluded state body comparison | Matches backup |

The local `infra/reporting/terraform.tfstate` file is now a zero-byte backend
placeholder and `infra/reporting/terraform.tfstate.backup` remains present. No
local state or backup file was deleted.

### 19.5 Post-Migration Plan Verification

The first post-migration refresh-only attempt collided with a concurrently
running normal plan against the new S3 lock. No lock bypass was used. The normal
plan completed cleanly, then refresh-only was retried alone and completed
cleanly.

| Check | Result |
|---|---|
| `terraform plan -no-color` | `No changes. Your infrastructure matches the configuration.` |
| `terraform plan -refresh-only -no-color` | `No changes. Your infrastructure still matches the configuration.` |
| Final address count | 32 |
| Final lineage/serial | `345951f9-f0c5-4696-df6f-fced093edc93` / `1` |
| Create/update/destroy/replacement | `0 / 0 / 0 / 0` |

### 19.6 README Correction

Updated `infra/reporting/README.md` to remove the stale “currently destroyed”
status and the line claiming the reporting stack was later destroyed. The
replacement states that current Terraform refresh-only and normal plans are
clean against deployed AWS resources. This is a documentation correction only.

### 19.7 Result

Reporting S3 backend migration succeeded. All four Terraform roots now use S3
remote state:

| Root | State |
|---|---|
| Foundation | `s3://kjw-aegis-terraform-state/aegis-pi/foundation/terraform.tfstate` |
| Hub | `s3://kjw-aegis-terraform-state/aegis-pi/hub/terraform.tfstate` |
| Data-Pipeline | `s3://kjw-aegis-terraform-state/aegis-pi/data-pipeline/terraform.tfstate` |
| Reporting | `s3://kjw-aegis-terraform-state/aegis-pi/reporting/terraform.tfstate` |

Next recommended phase: review and commit the accumulated backend,
remote-state, data-pipeline reconciliation, reporting README, and audit
documentation changes, then mirror the relevant backend/reconciliation changes
into the merge-side tree if that tree is still maintained separately.

## 20. Script Remote-State Readiness Update

Timestamp: `2026-06-08 17:23:52 KST`

Scope: review accumulated Aegis-pi changes and update build/destroy/preflight
scripts so they no longer use local `terraform.tfstate` file existence as a
readiness, ownership, or destroy/no-op signal. No Terraform apply, destroy,
import, state push/rm/mv, refresh-only apply, S3 object modification/deletion,
Dashboard state change, merge-side update, Git commit, or Git push was
performed.

### 20.1 Review Findings

Backend and reconciliation changes reviewed:

- Foundation, Hub, Data-Pipeline, and Reporting have S3 backend blocks using
  bucket `kjw-aegis-terraform-state`, region `ap-south-1`, and
  `use_lockfile = true`.
- Hub `terraform_remote_state.foundation` now reads Foundation from S3.
- Data-Pipeline CloudInfraFast env/IAM reconciliation and deterministic
  packaging changes match the accepted AWS operating baseline.
- Reporting README no longer claims the stack is destroyed.
- No tfstate/tfvars/plan/zip/credential artifact is staged or committed.

No code-review blocking issue was found in the intended backend/reconciliation
diff. One operational caveat remains: Foundation and Hub refresh-only plans
still show state-projection/provider refresh diffs, while normal plans are
clean. Those refresh-only diffs were not applied in this step.

### 20.2 Script Changes

Added backend-aware helpers in `scripts/lib/terraform.sh`:

| Helper | Behavior |
|---|---|
| `aegis_terraform_init_backend <root>` | Runs `terraform init -input=false -no-color` for the root. |
| `aegis_terraform_state_list_or_error <root>` | Initializes the backend and runs `terraform state list`. Backend/access errors return non-zero. |
| `aegis_terraform_state_has_resources <root>` | Returns success for non-empty state, `1` for accessible empty state, and `2` for inaccessible state. |
| `aegis_terraform_require_state_resources <root> <label>` | Fails closed if state is inaccessible or empty. |
| `aegis_terraform_state_pull_json <root>` | Initializes the backend and reads state JSON with `terraform state pull`. |

Scripts updated to use backend-aware state checks instead of local
`terraform.tfstate` file existence:

| File | Change |
|---|---|
| `scripts/build/preflight.sh` | Foundation/Hub prerequisites and Hub AWS state checks now use remote state access. State access failure is recorded as preflight failure, not empty state. |
| `scripts/build/build-hub.sh` | SlowCollector EKS access reconciliation now requires non-empty Data-Pipeline remote state instead of a local state file. |
| `scripts/build/build-admin-ui-after-ns.sh` | Requires non-empty Hub remote state before reading Hub outputs. |
| `scripts/build/verify-complete.sh` | Requires non-empty Hub remote state before verification. |
| `scripts/build/connect-hub-tailscale-ui.sh` | Requires non-empty Hub remote state. |
| `scripts/build/build-iot-factory-a.sh` | Requires non-empty Hub remote state when Hub-Spoke/Tailscale work is enabled. |
| `scripts/build/lib/connect-spoke.sh` | Requires non-empty Hub remote state. |
| `scripts/build/reconcile-data-pipe-eks-access.sh` | Requires non-empty Hub and Data-Pipeline remote states. |
| `scripts/destroy/destroy-all.sh` | Delegates reporting/data-pipeline destroy to scripts that inspect remote state; Hub destroy requires non-empty Foundation remote state. |
| `scripts/destroy/destroy-data-pipe.sh` | Empty remote state is no-op; inaccessible remote state fails closed. |
| `scripts/destroy/destroy-reporting.sh` | Empty remote state is no-op; inaccessible remote state fails closed. |
| `scripts/destroy/destroy-hub-infra.sh` | Requires non-empty Foundation remote state before Hub destroy. |
| `scripts/hub/README.md` | Documents remote state requirement for data-pipeline EKS access reconcile. |
| `scripts/destroy/README.md` | Documents remote state access/no-op/fail-closed behavior. |

Behavioral change:

- Zero-byte local backend placeholder files and local `.backup` files are no
  longer treated as authoritative deployment evidence.
- Remote backend access failure is distinct from accessible empty state.
- Destroy scripts retain or increase protection: inaccessible state fails
  closed; only accessible empty state is treated as no-op.

### 20.3 Script Verification

| Check | Result |
|---|---|
| `rg` for local `terraform.tfstate` dependencies under `scripts/` | No remaining matches in shell/script docs after updates |
| `bash -n` on modified shell scripts | Passed |
| Backend-aware helper smoke test | Foundation 25, Hub 78, Data-Pipeline 84, Reporting 32 addresses |
| `scripts/build/preflight.sh` read-only smoke test | Passed |
| `git diff --check` | Passed |

### 20.4 Terraform Verification

| Root | `terraform fmt -check` | `terraform validate -no-color` | `terraform plan -refresh-only -no-color` | `terraform plan -no-color` |
|---|---|---|---|---|
| Foundation | Passed | Passed | Succeeded with refresh-only state projection changes: `aws_ecr_repository.snapshot_uploader`, `aws_iam_role.github_actions_ecr_push` | `No changes` |
| Hub | Passed | Passed | First attempt hit transient EC2 IGW read `UnknownError`; retry succeeded with expected provider/state projection changes across EKS/IAM/route resources | `No changes` |
| Data-Pipeline | Passed | Passed | `No changes` with CloudInfraFast operating values supplied via process-local `TF_VAR_*` | `No changes` with the same `TF_VAR_*` values |
| Reporting | Passed | Passed | `No changes` | `No changes` |

Refresh-only notes:

- Foundation refresh-only would record provider/state projection updates for
  empty `tags` and the GitHub Actions ECR push inline policy view that includes
  the snapshot-uploader repository.
- Hub refresh-only would record provider/state projection updates for EKS,
  IAM, route, NAT EIP, security group, launch template, and KMS-related
  resources. This is consistent with the earlier Hub broad refresh-only audit.
- No refresh-only apply was run.

### 20.5 Status

The script migration is complete and commitable from a code/syntax/normal-plan
perspective. Remaining operational awareness:

- Foundation and Hub refresh-only plans are not fully clean because they have
  state projection/provider refresh diffs. Normal plans are clean.
- Data-Pipeline plans require the CloudInfraFast operating values to be supplied
  via the existing `TF_VAR_*` workflow; those values remain uncommitted and were
  not recorded.
- Merge-side tree has not been updated in this step.
