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

variable "lambda_snapshot_presigner_name" {
  description = "Lambda function name for image snapshot presigned PUT URL generation."
  type        = string
  default     = "AEGIS-Lambda-SnapshotPresigner"
}

variable "lambda_snapshot_presigner_timeout" {
  description = "Snapshot presigner Lambda timeout in seconds."
  type        = number
  default     = 10
}

variable "lambda_snapshot_presigner_memory" {
  description = "Snapshot presigner Lambda memory allocation in MB."
  type        = number
  default     = 128
}

variable "snapshot_presigner_allowed_factory_ids" {
  description = "Factory IDs allowed to request image snapshot presigned PUT URLs."
  type        = list(string)
  default     = ["factory-a"]
}

variable "snapshot_presigner_max_file_bytes" {
  description = "Maximum image snapshot upload size accepted by the presigner."
  type        = number
  default     = 5242880
}

variable "snapshot_presigner_expires_in_seconds" {
  description = "Presigned PUT URL expiration in seconds."
  type        = number
  default     = 300
}

variable "snapshot_presigner_shared_token" {
  description = "Optional bearer token required by the snapshot presigner HTTP endpoint. Leave empty to disable token auth."
  type        = string
  default     = ""
  sensitive   = true
}

variable "snapshot_presigner_throttle_burst_limit" {
  description = "HTTP API burst throttle limit for snapshot presign requests."
  type        = number
  default     = 20
}

variable "snapshot_presigner_throttle_rate_limit" {
  description = "HTTP API steady-state throttle rate limit for snapshot presign requests."
  type        = number
  default     = 5
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

variable "cloud_infra_fast_collector_cloudfront_distribution_id" {
  description = "Optional CloudFront distribution ID monitored by the cloud infra fast collector. Set via tfvars or TF_VAR in operations; do not hard-code environment-specific values in source."
  type        = string
  default     = null
  nullable    = true
}

variable "cloud_infra_fast_collector_dlq_queue_name" {
  description = "Optional SQS DLQ queue name monitored by the cloud infra fast collector. Set via tfvars or TF_VAR in operations; do not hard-code environment-specific values in source."
  type        = string
  default     = null
  nullable    = true
}

variable "cloud_infra_fast_collector_rds_db_instance_id" {
  description = "Optional RDS DB instance ID monitored by the cloud infra fast collector. Set via tfvars or TF_VAR in operations; do not hard-code environment-specific values in source."
  type        = string
  default     = null
  nullable    = true
}

variable "cloud_infra_fast_collector_redis_replication_group_id" {
  description = "Optional ElastiCache Redis replication group ID monitored by the cloud infra fast collector. Set via tfvars or TF_VAR in operations; do not hard-code environment-specific values in source."
  type        = string
  default     = null
  nullable    = true
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

variable "lambda_risk_alert_dispatcher_name" {
  description = "Lambda function name for S3 processed snapshot risk alert dispatching."
  type        = string
  default     = "AEGIS-Lambda-RiskAlertDispatcher"
}

variable "lambda_risk_alert_dispatcher_timeout" {
  description = "Risk alert dispatcher Lambda timeout in seconds."
  type        = number
  default     = 30
}

variable "lambda_risk_alert_dispatcher_memory" {
  description = "Risk alert dispatcher Lambda memory in MB."
  type        = number
  default     = 256
}

variable "lambda_risk_alert_dispatcher_reserved_concurrency" {
  description = "Reserved concurrency for the risk alert dispatcher Lambda."
  type        = number
  default     = 3
}

variable "risk_alert_dispatcher_s3_trigger_enabled" {
  description = "Whether to attach S3 ObjectCreated notifications for processed alert source snapshots."
  type        = bool
  default     = true
}

variable "risk_alert_dispatcher_s3_prefixes" {
  description = "S3 processed prefixes that invoke the risk alert dispatcher. S3 notifications do not support middle wildcards, so factory prefixes are explicit."
  type        = list(string)
  default = [
    "processed/factory-a/state_snapshot/",
    "processed/factory-b/state_snapshot/",
    "processed/factory-c/state_snapshot/",
    "processed/cloud_infra/fast/",
    "processed/cloud_infra/slow/",
  ]
}

variable "risk_alert_slack_webhook_secret_arn" {
  description = "Optional external Secrets Manager secret ARN containing the Slack webhook URL. Leave empty to use the data-pipeline managed secret."
  type        = string
  default     = ""
  sensitive   = true
}

variable "risk_alert_slack_webhook_secret_name" {
  description = "Secrets Manager secret name managed by the data-pipeline layer for the RiskAlertDispatcher Slack webhook URL."
  type        = string
  default     = "AEGIS/foundation-mvp/risk-alert/slack-webhook-url"
}

variable "risk_alert_factory_slack_webhook_secret_names" {
  description = "Secrets Manager secret names managed by the data-pipeline layer for factory-specific RiskAlertDispatcher Slack webhook URLs."
  type        = map(string)
  default = {
    factory-a = "AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-a"
    factory-b = "AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-b"
    factory-c = "AEGIS/foundation-mvp/risk-alert/slack-webhook/factory-c"
  }
}

variable "risk_alert_slack_webhook_ssm_parameter_name" {
  description = "SSM SecureString parameter name containing the Slack webhook URL. Leave empty when using Secrets Manager or when alerts are not ready to send."
  type        = string
  default     = ""
  sensitive   = true
}

variable "risk_alert_state_ttl_seconds" {
  description = "TTL in seconds for ALERT# DynamoDB state items."
  type        = number
  default     = 604800
}

variable "risk_alert_factory_warning_cooldown_seconds" {
  description = "Factory warning Slack resend cooldown in seconds."
  type        = number
  default     = 900
}

variable "risk_alert_factory_danger_cooldown_seconds" {
  description = "Factory danger Slack resend cooldown in seconds."
  type        = number
  default     = 300
}

variable "risk_alert_cloud_warning_cooldown_seconds" {
  description = "Cloud infra warning Slack resend cooldown in seconds."
  type        = number
  default     = 900
}

variable "risk_alert_cloud_danger_cooldown_seconds" {
  description = "Cloud infra danger Slack resend cooldown in seconds."
  type        = number
  default     = 300
}

variable "risk_alert_slack_http_timeout_seconds" {
  description = "Slack webhook HTTP timeout in seconds."
  type        = number
  default     = 4
}
