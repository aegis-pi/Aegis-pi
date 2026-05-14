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

variable "iot_factory_id" {
  description = "Factory ID used by the factory-a IoT Core topic rule."
  type        = string
  default     = "factory-a"
}

variable "iot_topic_root" {
  description = "Root MQTT topic prefix for Aegis IoT messages."
  type        = string
  default     = "aegis"
}

variable "iot_rule_enabled" {
  description = "Whether the factory-a IoT Core to S3 topic rule is enabled."
  type        = bool
  default     = true
}

variable "amp_workspace_alias" {
  description = "Alias for the Amazon Managed Service for Prometheus workspace."
  type        = string
  default     = "AEGIS-AMP-hub"
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
