locals {
  naming_prefix = "AEGIS"

  resource_names = {
    eks_cluster                  = "${local.naming_prefix}-EKS"
    eks_cluster_iam_role         = "${local.naming_prefix}-IAMRole-EKS-cluster"
    eks_cluster_security         = "${local.naming_prefix}-SG-EKS"
    eks_node_group               = "${local.naming_prefix}-EKS-node"
    eks_node_iam_role            = "${local.naming_prefix}-IAMRole-EKS-node"
    eks_node_launch_template     = "${local.naming_prefix}-LT-EKS-node"
    aws_lb_controller_irsa       = "${local.naming_prefix}-IAMRole-IRSA-aws-load-balancer-controller"
    aws_lb_controller_policy     = "${local.naming_prefix}-IAMPolicy-IRSA-aws-load-balancer-controller"
    grafana_amp_query_irsa       = "${local.naming_prefix}-IAMRole-IRSA-grafana-amp-query"
    prometheus_remote_write_irsa = "${local.naming_prefix}-IAMRole-IRSA-prometheus-remote-write"
    risk_normalizer_irsa         = "${local.naming_prefix}-IAMRole-IRSA-risk-normalizer"
    vpc                          = "${local.naming_prefix}-VPC"
  }

  azs = [
    for suffix in var.availability_zone_suffixes : "${var.aws_region}${suffix}"
  ]

  zone_names = [
    for az in local.azs : "${upper(regex("[a-z]$", az))}zone"
  ]

  public_subnets = [
    for index in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, index)
  ]

  private_subnets = [
    for index in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, index + 10)
  ]

  public_subnet_names = [
    for zone in local.zone_names : "${local.naming_prefix}-Subnet-public-${zone}"
  ]

  private_subnet_names = [
    for zone in local.zone_names : "${local.naming_prefix}-Subnet-private-${zone}"
  ]

  risk_normalizer_subject         = "system:serviceaccount:${var.risk_normalizer_namespace}:${var.risk_normalizer_service_account}"
  aws_lb_controller_subject       = "system:serviceaccount:${var.aws_lb_controller_namespace}:${var.aws_lb_controller_service_account}"
  grafana_amp_query_subject       = "system:serviceaccount:${var.grafana_namespace}:${var.grafana_service_account}"
  prometheus_remote_write_subject = "system:serviceaccount:${var.prometheus_remote_write_namespace}:${var.prometheus_remote_write_service_account}"

  admin_ui_argocd_host  = coalesce(var.admin_ui_argocd_host, "argocd.${var.admin_ui_domain_name}")
  admin_ui_grafana_host = coalesce(var.admin_ui_grafana_host, "grafana.${var.admin_ui_domain_name}")

  zone_config = {
    for index, zone in local.zone_names : zone => {
      az                  = local.azs[index]
      public_subnet_cidr  = local.public_subnets[index]
      private_subnet_cidr = local.private_subnets[index]
      public_subnet_name  = local.public_subnet_names[index]
      private_subnet_name = local.private_subnet_names[index]
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "hub"
  }
}
