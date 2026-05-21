variable "project_name" {
  description = "Project name used for AWS resource naming and tagging."
  type        = string
  default     = "AEGIS"
}

variable "environment" {
  description = "Environment name for data-pipeline resources."
  type        = string
  default     = "foundation-mvp"
}

variable "aws_region" {
  description = "AWS region for data-pipeline resources."
  type        = string
  default     = "ap-south-1"
}

variable "data_bucket_name" {
  description = "S3 bucket name created by the foundation layer. Used for IoT Rule S3 actions and Lambda PutObject."
  type        = string
  default     = "aegis-bucket-data"
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

variable "dynamodb_table_name" {
  description = "DynamoDB table name for factory status (LATEST and HISTORY items)."
  type        = string
  default     = "AEGIS-DynamoDB-FactoryStatus"
}

variable "dynamodb_history_ttl_hours" {
  description = "TTL in hours for DynamoDB HISTORY items."
  type        = number
  default     = 48
}

variable "lambda_data_processor_name" {
  description = "Lambda function name for the Aegis data processor."
  type        = string
  default     = "AEGIS-Lambda-DataProcessor"
}

variable "lambda_data_processor_timeout" {
  description = "Lambda execution timeout in seconds."
  type        = number
  default     = 60
}

variable "lambda_data_processor_memory" {
  description = "Lambda memory allocation in MB."
  type        = number
  default     = 512
}
