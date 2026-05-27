variable "project_name" {
  description = "Project name used for AWS resource naming and tagging."
  type        = string
  default     = "AEGIS"
}

variable "environment" {
  description = "Environment name for reporting resources."
  type        = string
  default     = "foundation-mvp"
}

variable "aws_region" {
  description = "AWS region for reporting resources."
  type        = string
  default     = "ap-south-1"
}

variable "data_bucket_name" {
  description = "Existing S3 bucket name that contains processed data and receives report outputs."
  type        = string
  default     = "aegis-bucket-data"
}

variable "report_timezone" {
  description = "Timezone used for daily report windows."
  type        = string
  default     = "Asia/Seoul"
}

variable "report_factory_ids" {
  description = "Comma-separated factory IDs for daily reporting."
  type        = string
  default     = "factory-a,factory-b,factory-c"
}

variable "report_datasets" {
  description = "Comma-separated processed datasets for daily reporting."
  type        = string
  default     = "factory_state,risk_score,infra_state"
}

variable "report_output_prefix" {
  description = "S3 root prefix for generated reports."
  type        = string
  default     = "reports/daily"
}

variable "schedule_expression" {
  description = "EventBridge Scheduler cron expression. Default is 00:30 KST as UTC 15:30."
  type        = string
  default     = "cron(30 15 * * ? *)"
}

variable "lambda_timeout_seconds" {
  description = "Default Lambda timeout in seconds."
  type        = number
  default     = 300
}

variable "lambda_memory_mb" {
  description = "Default Lambda memory size in MB."
  type        = number
  default     = 1024
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for GenerateFactoryReport."
  type        = string
  default     = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "bedrock_max_tokens" {
  description = "Max output tokens for Bedrock report generation."
  type        = number
  default     = 3000
}

variable "bedrock_temperature" {
  description = "Bedrock generation temperature."
  type        = number
  default     = 0.2
}
