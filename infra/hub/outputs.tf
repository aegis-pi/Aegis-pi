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
  description = "Control / Management VPC ID."
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

output "aws_lb_controller_irsa_role_arn" {
  description = "IAM role ARN assumed by the AWS Load Balancer Controller service account."
  value       = aws_iam_role.aws_lb_controller_irsa.arn
}

output "aws_lb_controller_service_account" {
  description = "Kubernetes service account identity for AWS Load Balancer Controller."
  value = {
    namespace = var.aws_lb_controller_namespace
    name      = var.aws_lb_controller_service_account
    subject   = local.aws_lb_controller_subject
  }
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

output "grafana_amp_query_irsa_role_arn" {
  description = "IAM role ARN assumed by the internal Grafana Kubernetes service account for AMP query access."
  value       = aws_iam_role.grafana_amp_query_irsa.arn
}

output "grafana_service_account" {
  description = "Kubernetes service account identity for internal Grafana AMP query access."
  value = {
    namespace = var.grafana_namespace
    name      = var.grafana_service_account
    subject   = local.grafana_amp_query_subject
  }
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

output "amp_prometheus_endpoint" {
  description = "AMP Prometheus-compatible query endpoint consumed from infra/foundation."
  value       = data.terraform_remote_state.foundation.outputs.amp_prometheus_endpoint
}

output "amp_remote_write_endpoint" {
  description = "AMP remote_write endpoint consumed from infra/foundation."
  value       = data.terraform_remote_state.foundation.outputs.amp_remote_write_endpoint
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
