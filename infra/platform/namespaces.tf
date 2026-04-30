resource "kubernetes_namespace_v1" "hub" {
  for_each = local.hub_namespaces

  metadata {
    name = each.key

    labels = {
      "app.kubernetes.io/part-of" = "aegis-hub"
      "aegis.io/component"        = each.value.component
    }

    annotations = {
      "aegis.io/role" = each.value.description
    }
  }
}

resource "kubernetes_limit_range_v1" "hub_default" {
  for_each = local.hub_namespaces

  metadata {
    name      = "default-limits"
    namespace = kubernetes_namespace_v1.hub[each.key].metadata[0].name
  }

  spec {
    limit {
      type = "Container"

      default = {
        cpu    = "500m"
        memory = "512Mi"
      }

      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
    }
  }
}
