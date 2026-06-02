locals {
  naming_prefix = var.project_name

  lambda_functions = {
    prepare_report_window = {
      name    = "${local.naming_prefix}-Lambda-PrepareReportWindow"
      handler = "lambda_prepare_report_window.handler"
      memory  = 512
      timeout = 60
    }
    aggregate_factory_hour = {
      name    = "${local.naming_prefix}-Lambda-AggregateFactoryHour"
      handler = "lambda_aggregate_factory_hour.handler"
      memory  = var.lambda_memory_mb
      timeout = var.lambda_timeout_seconds
    }
    merge_factory_daily = {
      name    = "${local.naming_prefix}-Lambda-MergeFactoryDaily"
      handler = "lambda_merge_factory_daily.handler"
      memory  = 512
      timeout = 120
    }
    generate_factory_report = {
      name    = "${local.naming_prefix}-Lambda-GenerateFactoryReport"
      handler = "lambda_generate_factory_report.handler"
      memory  = 512
      timeout = 120
    }
    aggregate_cloud_infra_hour = {
      name    = "${local.naming_prefix}-Lambda-AggregateCloudInfraHour"
      handler = "lambda_aggregate_cloud_infra_hour.handler"
      memory  = var.lambda_memory_mb
      timeout = var.lambda_timeout_seconds
    }
    merge_cloud_infra_daily = {
      name    = "${local.naming_prefix}-Lambda-MergeCloudInfraDaily"
      handler = "lambda_merge_cloud_infra_daily.handler"
      memory  = 512
      timeout = 120
    }
    generate_cloud_infra_report = {
      name    = "${local.naming_prefix}-Lambda-GenerateCloudInfraReport"
      handler = "lambda_generate_cloud_infra_report.handler"
      memory  = 512
      timeout = 120
    }
  }

  state_machine_name = "${local.naming_prefix}-DailyFactoryReportStateMachine"
  scheduler_name     = "${local.naming_prefix}-Schedule-DailyFactoryReport"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "reporting"
  }
}
