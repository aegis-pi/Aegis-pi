locals {
  naming_prefix = "AEGIS"

  resource_names = {
    eks_cluster              = "${local.naming_prefix}-EKS"
    eks_cluster_iam_role     = "${local.naming_prefix}-IAMRole-EKS-cluster"
    eks_cluster_security     = "${local.naming_prefix}-SG-EKS"
    eks_node_group           = "${local.naming_prefix}-EKS-node"
    eks_node_iam_role        = "${local.naming_prefix}-IAMRole-EKS-node"
    eks_node_launch_template = "${local.naming_prefix}-LT-EKS-node"
    vpc                      = "${local.naming_prefix}-VPC"
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
