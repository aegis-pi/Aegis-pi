resource "aws_iam_role_policy_attachment" "eks_node_cloudwatch_agent" {
  count = var.enable_cloudwatch_observability ? 1 : 0

  role       = local.resource_names.eks_node_iam_role
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"

  depends_on = [module.eks]
}

resource "aws_eks_addon" "cloudwatch_observability" {
  count = var.enable_cloudwatch_observability ? 1 : 0

  cluster_name                = module.eks.cluster_name
  addon_name                  = "amazon-cloudwatch-observability"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [
    module.eks,
    aws_iam_role_policy_attachment.eks_node_cloudwatch_agent,
  ]
}

resource "aws_eks_addon" "metrics_server" {
  count = var.enable_metrics_server ? 1 : 0

  cluster_name                = module.eks.cluster_name
  addon_name                  = "metrics-server"
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  depends_on = [module.eks]
}
