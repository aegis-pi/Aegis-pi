locals {
  hub_namespaces = {
    argocd = {
      component   = "gitops"
      description = "Hub에서 Spoke 배포 제어"
    }
    observability = {
      component   = "observability"
      description = "Grafana, AMP 연동 메트릭 관제"
    }
    risk = {
      component   = "risk"
      description = "Risk Score Engine, 정규화 서비스"
    }
    ops-support = {
      component   = "ops-support"
      description = "pipeline_status 집계 보조 기능"
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "platform"
  }
}
