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

variable "lambda_cloud_infra_fast_collector_name" {
  description = "Lambda function name for the 1-minute cloud infra fast collector."
  type        = string
  default     = "AEGIS-Lambda-CloudInfraFastCollector"
}

variable "lambda_cloud_infra_fast_collector_timeout" {
  description = "Cloud infra fast collector Lambda timeout in seconds."
  type        = number
  default     = 60
}

variable "lambda_cloud_infra_fast_collector_memory" {
  description = "Cloud infra fast collector Lambda memory in MB."
  type        = number
  default     = 512
}

variable "cloud_infra_fast_collector_enabled" {
  description = "Whether the 1-minute cloud infra fast collector schedule is enabled."
  type        = bool
  default     = true
}

variable "cloud_infra_fast_history_ttl_hours" {
  description = "TTL in hours for CLOUD#infra HISTORY#FAST DynamoDB items."
  type        = number
  default     = 6
}

variable "cloud_infra_factory_ids" {
  description = "Factories included in cloud infra factory freshness summaries."
  type        = list(string)
  default     = ["factory-a", "factory-b", "factory-c"]
}

variable "cloud_infra_ecs_cluster_name" {
  description = "ECS cluster monitored by the cloud infra fast collector."
  type        = string
  default     = "KJW-AEGIS-Data-ECSCluster"
}

variable "cloud_infra_ecs_service_name" {
  description = "ECS service monitored by the cloud infra fast collector."
  type        = string
  default     = "KJW-AEGIS-Data-Service-Backend"
}

variable "cloud_infra_alb_target_group_name" {
  description = "ALB target group monitored by the cloud infra fast collector."
  type        = string
  default     = "kjw-aegis-data-tg-backend"
}

variable "cloud_infra_pipeline_lambda_names" {
  description = "Pipeline Lambda functions monitored by the cloud infra fast collector."
  type        = list(string)
  default     = ["AEGIS-Lambda-DataProcessor", "AEGIS-Lambda-GraphAggregator5m"]
}

variable "cloud_infra_scheduler_names" {
  description = "EventBridge Scheduler schedules monitored by the cloud infra fast collector."
  type        = list(string)
  default     = ["AEGIS-Schedule-DataProcessorRefresh1m", "AEGIS-Schedule-GraphAggregator5m"]
}

variable "cloud_infra_fast_metric_window_minutes" {
  description = "CloudWatch metric lookback window for the fast collector."
  type        = number
  default     = 5
}

variable "lambda_cloud_infra_slow_collector_name" {
  description = "Lambda function name for the 5-minute cloud infra slow collector."
  type        = string
  default     = "AEGIS-Lambda-CloudInfraSlowCollector"
}

variable "lambda_cloud_infra_slow_collector_timeout" {
  description = "Cloud infra slow collector Lambda timeout in seconds."
  type        = number
  default     = 60
}

variable "lambda_cloud_infra_slow_collector_memory" {
  description = "Cloud infra slow collector Lambda memory in MB."
  type        = number
  default     = 512
}

variable "cloud_infra_slow_collector_enabled" {
  description = "Whether the 5-minute cloud infra slow collector schedule is enabled."
  type        = bool
  default     = true
}

variable "cloud_infra_slow_history_ttl_hours" {
  description = "TTL in hours for CLOUD#infra HISTORY#SLOW DynamoDB items."
  type        = number
  default     = 24
}

variable "cloud_infra_eks_cluster_name" {
  description = "EKS cluster monitored by the cloud infra slow collector."
  type        = string
  default     = "AEGIS-EKS"
}

variable "cloud_infra_s3_latest_lookback_hours" {
  description = "Number of recent hours to scan for S3 latest freshness prefixes."
  type        = number
  default     = 24
}

variable "cloud_infra_argocd_namespace" {
  description = "ArgoCD namespace queried by the cloud infra slow collector."
  type        = string
  default     = "argocd"
}

variable "cloud_infra_k8s_top_pods_limit" {
  description = "Number of top Kubernetes pods to keep by CPU and memory usage."
  type        = number
  default     = 5
}
