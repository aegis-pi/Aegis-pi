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
  default     = 2
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

variable "data_processor_refresh_enabled" {
  description = "Whether the data processor freshness refresh schedule is enabled."
  type        = bool
  default     = true
}

variable "data_processor_factory_ids" {
  description = "Factories refreshed by the data processor freshness schedule."
  type        = list(string)
  default     = ["factory-a", "factory-b", "factory-c"]
}

variable "lambda_graph_aggregator_name" {
  description = "Lambda function name for 5-minute graph metric aggregation."
  type        = string
  default     = "AEGIS-Lambda-GraphAggregator5m"
}

variable "lambda_graph_aggregator_timeout" {
  description = "Graph aggregator Lambda timeout in seconds."
  type        = number
  default     = 60
}

variable "lambda_graph_aggregator_memory" {
  description = "Graph aggregator Lambda memory in MB."
  type        = number
  default     = 512
}

variable "graph_aggregator_enabled" {
  description = "Whether the 5-minute graph aggregator schedule is enabled."
  type        = bool
  default     = true
}

variable "graph_aggregator_factory_ids" {
  description = "Factories processed by the 5-minute graph aggregator."
  type        = list(string)
  default     = ["factory-a", "factory-b", "factory-c"]
}

variable "graph_bucket_minutes" {
  description = "Graph aggregation bucket size in minutes."
  type        = number
  default     = 5
}

variable "graph_aggregator_lookback_buckets" {
  description = "Number of closed buckets to aggregate on each scheduled run."
  type        = number
  default     = 1
}

variable "graph_bucket_ttl_hours" {
  description = "TTL in hours for GRAPH#5M DynamoDB items."
  type        = number
  default     = 48
}

variable "graph_expected_sample_interval_seconds" {
  description = "Expected state snapshot interval used for graph bucket quality."
  type        = number
  default     = 3
}

variable "graph_ai_score_threshold" {
  description = "Default threshold for AI detection score graph markers."
  type        = number
  default     = 0.7
}
