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
