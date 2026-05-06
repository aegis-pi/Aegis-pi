output "aws_region" {
  description = "AWS region for the Hub infrastructure."
  value       = var.aws_region
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint."
  value       = module.eks.cluster_endpoint
}

output "vpc_id" {
  description = "Hub Processing VPC ID."
  value       = aws_vpc.hub.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for EKS worker nodes."
  value       = [for zone in local.zone_names : aws_subnet.private[zone].id]
}

output "public_subnet_ids" {
  description = "Public subnet IDs for ingress/NAT resources."
  value       = [for zone in local.zone_names : aws_subnet.public[zone].id]
}

output "update_kubeconfig_command" {
  description = "Command to configure local kubectl access after apply."
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "oidc_provider_arn" {
  description = "EKS OIDC provider ARN used for IRSA."
  value       = module.eks.oidc_provider_arn
}

output "risk_normalizer_irsa_role_arn" {
  description = "IAM role ARN assumed by the risk normalizer Kubernetes service account."
  value       = aws_iam_role.risk_normalizer_irsa.arn
}

output "risk_normalizer_service_account" {
  description = "Kubernetes service account identity for the risk normalizer IRSA role."
  value = {
    namespace = var.risk_normalizer_namespace
    name      = var.risk_normalizer_service_account
    subject   = local.risk_normalizer_subject
  }
}

output "prometheus_remote_write_irsa_role_arn" {
  description = "IAM role ARN assumed by the Prometheus remote_write Kubernetes service account."
  value       = aws_iam_role.prometheus_remote_write_irsa.arn
}

output "prometheus_remote_write_service_account" {
  description = "Kubernetes service account identity for AMP remote_write."
  value = {
    namespace = var.prometheus_remote_write_namespace
    name      = var.prometheus_remote_write_service_account
    subject   = local.prometheus_remote_write_subject
  }
}

output "amp_workspace_arn" {
  description = "AMP workspace ARN consumed from infra/foundation."
  value       = data.terraform_remote_state.foundation.outputs.amp_workspace_arn
}

output "amp_remote_write_endpoint" {
  description = "AMP remote_write endpoint consumed from infra/foundation."
  value       = data.terraform_remote_state.foundation.outputs.amp_remote_write_endpoint
}
