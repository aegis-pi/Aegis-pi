output "hub_namespaces" {
  description = "Hub Kubernetes namespaces managed by the platform Terraform root."
  value       = keys(local.hub_namespaces)
}
