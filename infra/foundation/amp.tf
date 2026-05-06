resource "aws_prometheus_workspace" "hub" {
  alias = var.amp_workspace_alias
  tags  = local.tags
}
