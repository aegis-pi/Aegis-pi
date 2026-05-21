locals {
  naming_prefix = "AEGIS"

  data_prefixes = {
    raw       = "raw/"
    processed = "processed/"
    latest    = "latest/"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "foundation"
  }
}
