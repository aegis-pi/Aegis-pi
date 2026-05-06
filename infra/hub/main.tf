resource "aws_vpc" "hub" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = local.resource_names.vpc
  }
}

resource "aws_internet_gateway" "hub" {
  vpc_id = aws_vpc.hub.id

  tags = {
    Name = "${local.naming_prefix}-IGW"
  }
}

resource "aws_subnet" "public" {
  for_each = local.zone_config

  vpc_id                  = aws_vpc.hub.id
  availability_zone       = each.value.az
  cidr_block              = each.value.public_subnet_cidr
  map_public_ip_on_launch = true

  tags = {
    Name                     = each.value.public_subnet_name
    "kubernetes.io/role/elb" = "1"
  }
}

resource "aws_subnet" "private" {
  for_each = local.zone_config

  vpc_id            = aws_vpc.hub.id
  availability_zone = each.value.az
  cidr_block        = each.value.private_subnet_cidr

  tags = {
    Name                              = each.value.private_subnet_name
    "kubernetes.io/role/internal-elb" = "1"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.hub.id

  tags = {
    Name = "${local.naming_prefix}-RouteTable-public"
  }
}

resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.hub.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  for_each = local.zone_config

  domain = "vpc"

  tags = {
    Name = "${local.naming_prefix}-EIP-NAT-public-${each.key}"
  }

  depends_on = [aws_internet_gateway.hub]
}

resource "aws_nat_gateway" "public" {
  for_each = local.zone_config

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = {
    Name = "${local.naming_prefix}-NAT-public-${each.key}"
  }

  depends_on = [aws_internet_gateway.hub]
}

resource "aws_route_table" "private" {
  for_each = local.zone_config

  vpc_id = aws_vpc.hub.id

  tags = {
    Name = "${local.naming_prefix}-RouteTable-private-${each.key}"
  }
}

resource "aws_route" "private_nat_gateway" {
  for_each = local.zone_config

  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.public[each.key].id
}

resource "aws_route_table_association" "private" {
  for_each = aws_subnet.private

  subnet_id      = each.value.id
  route_table_id = aws_route_table.private[each.key].id
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.14.0"

  name               = var.cluster_name
  kubernetes_version = var.kubernetes_version

  endpoint_public_access       = true
  endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  endpoint_private_access      = false

  enable_cluster_creator_admin_permissions = true

  iam_role_name            = local.resource_names.eks_cluster_iam_role
  iam_role_use_name_prefix = false

  security_group_name            = local.resource_names.eks_cluster_security
  security_group_use_name_prefix = false

  node_security_group_name            = "${local.naming_prefix}-SG-EKS-node"
  node_security_group_use_name_prefix = false

  addons = {
    vpc-cni = {
      before_compute = true
    }
    coredns    = {}
    kube-proxy = {}
  }

  vpc_id                   = aws_vpc.hub.id
  subnet_ids               = [for zone in local.zone_names : aws_subnet.private[zone].id]
  control_plane_subnet_ids = [for zone in local.zone_names : aws_subnet.private[zone].id]

  eks_managed_node_groups = {
    hub = {
      name            = local.resource_names.eks_node_group
      use_name_prefix = false
      tags            = local.tags

      iam_role_name            = local.resource_names.eks_node_iam_role
      iam_role_use_name_prefix = false

      launch_template_name            = local.resource_names.eks_node_launch_template
      launch_template_use_name_prefix = false
      launch_template_tags            = local.tags
      tag_specifications              = ["instance", "volume", "network-interface"]

      subnet_ids = [for zone in local.zone_names : aws_subnet.private[zone].id]

      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = var.node_min_size
      desired_size = var.node_desired_size
      max_size     = var.node_max_size

      labels = {
        role = "hub"
      }
    }
  }
}
