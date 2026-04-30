provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}

data "aws_eks_cluster" "hub" {
  name = var.cluster_name
}

data "aws_eks_cluster_auth" "hub" {
  name = var.cluster_name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.hub.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.hub.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.hub.token
}
