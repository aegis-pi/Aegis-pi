locals {
  naming_prefix = "AEGIS"

  data_prefixes = {
    raw       = "raw/"
    processed = "processed/"
    latest    = "latest/"
  }

  admin_ui_argocd_host  = coalesce(var.admin_ui_argocd_host, "argocd.${var.admin_ui_domain_name}")
  admin_ui_grafana_host = coalesce(var.admin_ui_grafana_host, "grafana.${var.admin_ui_domain_name}")

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "foundation"
  }
}
