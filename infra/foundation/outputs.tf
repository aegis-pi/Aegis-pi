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

output "processed_object_key_template" {
  description = "Recommended processed object key template for normalized datasets."
  value       = "processed/{factory_id}/{dataset}/yyyy={YYYY}/mm={MM}/dd={DD}/hh={HH}/{message_id}.json"
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

output "factory_a_log_adapter_ecr_repository_url" {
  description = "ECR repository URL for the factory-a-log-adapter image."
  value       = aws_ecr_repository.factory_a_log_adapter.repository_url
}

output "edge_iot_publisher_ecr_repository_url" {
  description = "ECR repository URL for the edge-iot-publisher image."
  value       = aws_ecr_repository.edge_iot_publisher.repository_url
}

output "snapshot_uploader_ecr_repository_url" {
  description = "ECR repository URL for the snapshot-uploader image."
  value       = aws_ecr_repository.snapshot_uploader.repository_url
}

output "edge_data_plane_image_tag_strategy" {
  description = "Image tag strategy for Edge data-plane deployment pipeline."
  value = {
    deployment_tag = "sha-<7-char-git-sha>"
    moving_tags    = ["main", "latest"]
    repositories = [
      aws_ecr_repository.factory_a_log_adapter.name,
      aws_ecr_repository.edge_iot_publisher.name,
      aws_ecr_repository.snapshot_uploader.name,
    ]
  }
}

output "edge_agent_image_tag_strategy" {
  description = "Image tag strategy for the legacy edge-agent smoke image."
  value = {
    deployment_tag = "sha-<7-char-git-sha>"
    moving_tags    = ["main", "latest"]
  }
}

output "github_actions_oidc_provider_arn" {
  description = "IAM OIDC provider ARN trusted by GitHub Actions."
  value       = aws_iam_openid_connect_provider.github_actions.arn
}

output "github_actions_ecr_push_role_arn" {
  description = "IAM role ARN assumed by GitHub Actions to push edge-agent images to ECR."
  value       = aws_iam_role.github_actions_ecr_push.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for factory status."
  value       = aws_dynamodb_table.factory_status.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN for factory status."
  value       = aws_dynamodb_table.factory_status.arn
}

output "admin_ui_domain_name" {
  description = "Base Route53 hosted zone domain for Admin UI."
  value       = var.admin_ui_domain_name
}

output "admin_ui_argocd_host" {
  description = "ArgoCD Admin UI hostname."
  value       = local.admin_ui_argocd_host
}

output "admin_ui_grafana_host" {
  description = "Grafana Admin UI hostname."
  value       = local.admin_ui_grafana_host
}

output "admin_ui_route53_zone_id" {
  description = "Route53 hosted zone ID for Admin UI."
  value       = aws_route53_zone.admin_ui.zone_id
}

output "admin_ui_route53_name_servers" {
  description = "Route53 name servers to configure at the domain registrar."
  value       = aws_route53_zone.admin_ui.name_servers
}

output "admin_ui_certificate_arn" {
  description = "ACM certificate ARN for Admin UI hostnames."
  value       = aws_acm_certificate.admin_ui.arn
}

output "admin_ui_certificate_validation_records" {
  description = "DNS validation records created in the Admin UI hosted zone."
  value = {
    for domain, record in aws_route53_record.admin_ui_certificate_validation : domain => {
      name    = record.name
      type    = record.type
      records = record.records
    }
  }
}
