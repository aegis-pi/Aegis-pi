variable "project_name" {
  description = "Project name used for AWS resource naming and tagging."
  type        = string
  default     = "AEGIS"
}

variable "environment" {
  description = "Environment name for foundation resources."
  type        = string
  default     = "foundation-mvp"
}

variable "aws_region" {
  description = "AWS region for foundation resources."
  type        = string
  default     = "ap-south-1"
}

variable "data_bucket_name" {
  description = "S3 bucket name for Aegis raw, processed, and latest data."
  type        = string
  default     = "aegis-bucket-data"
}

variable "data_bucket_force_destroy" {
  description = "Whether Terraform destroy should delete all objects and versions in the data bucket before deleting the bucket."
  type        = bool
  default     = true
}

variable "raw_archive_transition_days" {
  description = "Days before raw objects transition from Standard to Glacier Instant Retrieval."
  type        = number
  default     = 90
}

variable "processed_ia_transition_days" {
  description = "Days before processed objects transition from Standard to Standard-IA."
  type        = number
  default     = 365
}

variable "noncurrent_version_expiration_days" {
  description = "Days before noncurrent object versions are expired."
  type        = number
  default     = 90
}

variable "ecr_edge_agent_repository_name" {
  description = "ECR repository name for the edge-agent container image."
  type        = string
  default     = "aegis/edge-agent"
}

variable "ecr_edge_agent_image_tag_mutability" {
  description = "ECR image tag mutability for edge-agent. Keep MUTABLE so CI can move main/latest tags while deployments pin sha-* tags."
  type        = string
  default     = "MUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.ecr_edge_agent_image_tag_mutability)
    error_message = "ecr_edge_agent_image_tag_mutability must be MUTABLE or IMMUTABLE."
  }
}

variable "ecr_edge_agent_scan_on_push" {
  description = "Whether ECR scans edge-agent images when they are pushed."
  type        = bool
  default     = true
}

variable "ecr_repository_force_delete" {
  description = "Whether Terraform destroy should delete images before deleting ECR repositories."
  type        = bool
  default     = true
}

variable "ecr_edge_agent_keep_sha_images" {
  description = "Number of sha-* tagged edge-agent images to keep."
  type        = number
  default     = 50
}

variable "ecr_edge_agent_expire_untagged_days" {
  description = "Days before untagged edge-agent images expire."
  type        = number
  default     = 7
}

variable "ecr_factory_a_log_adapter_repository_name" {
  description = "ECR repository name for the factory-a-log-adapter container image."
  type        = string
  default     = "aegis/factory-a-log-adapter"
}

variable "ecr_edge_iot_publisher_repository_name" {
  description = "ECR repository name for the edge-iot-publisher container image."
  type        = string
  default     = "aegis/edge-iot-publisher"
}

variable "ecr_snapshot_uploader_repository_name" {
  description = "ECR repository name for the snapshot-uploader container image."
  type        = string
  default     = "aegis/snapshot-uploader"
}

variable "github_actions_oidc_thumbprints" {
  description = "Thumbprints accepted by the GitHub Actions OIDC provider. AWS currently treats token.actions.githubusercontent.com as a trusted provider, but IAM still requires at least one value."
  type        = list(string)
  default     = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

variable "github_actions_ecr_push_role_name" {
  description = "IAM role name assumed by GitHub Actions to push edge-agent images to ECR."
  type        = string
  default     = "AEGIS-GitHubActions-ECRPush"
}

variable "github_actions_ecr_push_subjects" {
  description = "Allowed GitHub OIDC sub claims for ECR push. Keep this scoped to the code repository main branch."
  type        = list(string)
  default     = ["repo:aegis-pi/Aegis-pi:ref:refs/heads/main"]
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for factory status (LATEST and HISTORY items)."
  type        = string
  default     = "AEGIS-DynamoDB-FactoryStatus"
}

variable "admin_ui_domain_name" {
  description = "Base domain name delegated to Route53 for Admin UI."
  type        = string
  default     = "minsoo-tech.cloud"
}

variable "admin_ui_argocd_host" {
  description = "FQDN for the ArgoCD Admin UI. Defaults to argocd.<admin_ui_domain_name>."
  type        = string
  default     = null
}

variable "admin_ui_grafana_host" {
  description = "FQDN for the Grafana Admin UI. Defaults to grafana.<admin_ui_domain_name>."
  type        = string
  default     = null
}
