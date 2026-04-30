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
