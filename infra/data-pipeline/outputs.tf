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
