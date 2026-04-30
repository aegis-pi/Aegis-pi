locals {
  name_prefix = "${var.project_name}-${var.environment}"

  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  public_subnets = [
    for index in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, index)
  ]

  private_subnets = [
    for index in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, index + 10)
  ]

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "hub"
  }
}
