output "data_bucket_name" {
  description = "S3 bucket name for Aegis data."
  value       = aws_s3_bucket.data.bucket
}

output "data_bucket_arn" {
  description = "S3 bucket ARN for Aegis data."
  value       = aws_s3_bucket.data.arn
}

output "data_bucket_prefixes" {
  description = "Standard data prefixes used by the Aegis data bucket."
  value       = local.data_prefixes
}

output "raw_object_key_template" {
  description = "Recommended raw object key template for IoT Core Rule S3 actions."
  value       = "raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json"
}

output "iot_rule_name" {
  description = "IoT Core topic rule name for factory raw S3 ingestion."
  value       = aws_iot_topic_rule.factory_raw_to_s3.name
}

output "iot_topic_filter" {
  description = "MQTT topic filter consumed by the factory raw S3 IoT rule."
  value       = "${local.iot_topic_prefix}/+"
}

output "iot_rule_s3_key_template" {
  description = "Concrete IoT Core S3 action key template with substitution expressions."
  value       = local.iot_s3_key
}

output "iot_rule_role_arn" {
  description = "IAM role ARN assumed by AWS IoT Core to write raw objects to S3."
  value       = aws_iam_role.iot_rule_s3.arn
}

output "processed_object_key_template" {
  description = "Recommended processed object key template for normalized datasets."
  value       = "processed/{dataset}/{factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json"
}

output "amp_workspace_alias" {
  description = "Alias of the Hub Amazon Managed Service for Prometheus workspace."
  value       = aws_prometheus_workspace.hub.alias
}

output "amp_workspace_id" {
  description = "Identifier of the Hub Amazon Managed Service for Prometheus workspace."
  value       = aws_prometheus_workspace.hub.id
}

output "amp_workspace_arn" {
  description = "ARN of the Hub Amazon Managed Service for Prometheus workspace."
  value       = aws_prometheus_workspace.hub.arn
}

output "amp_prometheus_endpoint" {
  description = "Prometheus endpoint for the Hub AMP workspace."
  value       = aws_prometheus_workspace.hub.prometheus_endpoint
}

output "amp_remote_write_endpoint" {
  description = "Remote write endpoint for Prometheus Agent or Prometheus remote_write."
  value       = "${aws_prometheus_workspace.hub.prometheus_endpoint}api/v1/remote_write"
}

output "edge_agent_ecr_repository_name" {
  description = "ECR repository name for the edge-agent image."
  value       = aws_ecr_repository.edge_agent.name
}

output "edge_agent_ecr_repository_url" {
  description = "ECR repository URL for the edge-agent image."
  value       = aws_ecr_repository.edge_agent.repository_url
}

output "edge_agent_ecr_repository_arn" {
  description = "ECR repository ARN for the edge-agent image."
  value       = aws_ecr_repository.edge_agent.arn
}

output "edge_agent_image_tag_strategy" {
  description = "Image tag strategy for the edge-agent deployment pipeline."
  value = {
    deployment_tag = "sha-<7-char-git-sha>"
    moving_tags    = ["main", "latest"]
  }
}
