output "iot_rule_name" {
  description = "IoT Core topic rule name for factory-a raw S3 ingestion."
  value       = aws_iot_topic_rule.factory_raw_to_s3.name
}

output "iot_rule_factory_b_name" {
  description = "IoT Core topic rule name for factory-b."
  value       = aws_iot_topic_rule.factory_b_raw_s3.name
}

output "iot_rule_factory_c_name" {
  description = "IoT Core topic rule name for factory-c."
  value       = aws_iot_topic_rule.factory_c_raw_s3.name
}

output "iot_topic_filter" {
  description = "MQTT topic filter consumed by the factory-a IoT rule."
  value       = "${local.iot_topic_prefix}/+"
}

output "iot_rule_s3_key_template" {
  description = "IoT Core S3 action key template for factory-a."
  value       = local.iot_s3_key
}

output "iot_rule_role_arn" {
  description = "IAM role ARN assumed by AWS IoT Core to write raw objects to S3."
  value       = aws_iam_role.iot_rule_s3.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for factory status (managed by infra/foundation)."
  value       = data.aws_dynamodb_table.factory_status.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN for factory status (managed by infra/foundation)."
  value       = data.aws_dynamodb_table.factory_status.arn
}

output "lambda_data_processor_name" {
  description = "Lambda function name for the Aegis data processor."
  value       = aws_lambda_function.data_processor.function_name
}

output "lambda_data_processor_arn" {
  description = "Lambda function ARN for the Aegis data processor."
  value       = aws_lambda_function.data_processor.arn
}

output "graph_aggregator_lambda_name" {
  description = "Graph aggregator Lambda name."
  value       = aws_lambda_function.graph_aggregator.function_name
}

output "graph_aggregator_lambda_arn" {
  description = "Graph aggregator Lambda ARN."
  value       = aws_lambda_function.graph_aggregator.arn
}

output "graph_aggregator_schedule_name" {
  description = "Graph aggregator schedule name."
  value       = aws_scheduler_schedule.graph_aggregator_5m.name
}

output "cloud_infra_fast_collector_lambda_name" {
  description = "Cloud infra fast collector Lambda name."
  value       = aws_lambda_function.cloud_infra_fast_collector.function_name
}

output "cloud_infra_fast_collector_lambda_arn" {
  description = "Cloud infra fast collector Lambda ARN."
  value       = aws_lambda_function.cloud_infra_fast_collector.arn
}

output "cloud_infra_fast_collector_schedule_name" {
  description = "Cloud infra fast collector schedule name."
  value       = aws_scheduler_schedule.cloud_infra_fast_collector_1m.name
}

output "cloud_infra_slow_collector_lambda_name" {
  description = "Cloud infra slow collector Lambda name."
  value       = aws_lambda_function.cloud_infra_slow_collector.function_name
}

output "cloud_infra_slow_collector_lambda_arn" {
  description = "Cloud infra slow collector Lambda ARN."
  value       = aws_lambda_function.cloud_infra_slow_collector.arn
}

output "cloud_infra_slow_collector_schedule_name" {
  description = "Cloud infra slow collector schedule name."
  value       = aws_scheduler_schedule.cloud_infra_slow_collector_5m.name
}

output "risk_alert_dispatcher_lambda_name" {
  description = "Risk alert dispatcher Lambda name."
  value       = aws_lambda_function.risk_alert_dispatcher.function_name
}

output "risk_alert_dispatcher_lambda_arn" {
  description = "Risk alert dispatcher Lambda ARN."
  value       = aws_lambda_function.risk_alert_dispatcher.arn
}

output "risk_alert_dispatcher_slack_secret_name" {
  description = "Secrets Manager secret name for the RiskAlertDispatcher Slack webhook URL."
  value       = aws_secretsmanager_secret.risk_alert_slack_webhook.name
}

output "risk_alert_dispatcher_slack_secret_arn" {
  description = "Secrets Manager secret ARN for the RiskAlertDispatcher Slack webhook URL."
  value       = aws_secretsmanager_secret.risk_alert_slack_webhook.arn
}

output "risk_alert_dispatcher_factory_slack_secret_names" {
  description = "Factory-specific Secrets Manager secret names for RiskAlertDispatcher Slack webhook URLs."
  value       = { for scope, secret in aws_secretsmanager_secret.risk_alert_slack_webhook_factory : scope => secret.name }
}
