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
