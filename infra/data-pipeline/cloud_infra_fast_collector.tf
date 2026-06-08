data "archive_file" "cloud_infra_collector_zip" {
  type             = "zip"
  source_dir       = "${path.module}/../../apps/cloud-infra-collector"
  output_path      = "${path.module}/lambda_cloud_infra_collector.zip"
  output_file_mode = "0644"
  excludes         = ["**/__pycache__/**", "**/*.pyc", "**/*.pyo", "tests/**", ".pytest_cache/**"]
}

resource "aws_cloudwatch_log_group" "cloud_infra_fast_collector" {
  name              = "/aws/lambda/${var.lambda_cloud_infra_fast_collector_name}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_role" "cloud_infra_fast_collector" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-CloudInfraFastCollector"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "cloud_infra_fast_collector" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.cloud_infra_fast_collector.arn}:*"]
  }

  statement {
    sid    = "CloudWatchMetricRead"
    effect = "Allow"

    actions = ["cloudwatch:GetMetricData"]

    resources = ["*"]
  }

  statement {
    sid    = "EcsServiceRead"
    effect = "Allow"

    actions = ["ecs:DescribeServices"]

    resources = ["*"]
  }

  statement {
    sid    = "AlbTargetRead"
    effect = "Allow"

    actions = [
      "elasticloadbalancing:DescribeTargetGroups",
      "elasticloadbalancing:DescribeTargetHealth",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "SchedulerRead"
    effect = "Allow"

    actions = ["scheduler:GetSchedule"]

    resources = [
      for schedule_name in var.cloud_infra_scheduler_names :
      "arn:${data.aws_partition.current.partition}:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule/default/${schedule_name}"
    ]
  }

  statement {
    sid    = "DynamoDBCloudInfraReadWrite"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
    ]

    resources = [data.aws_dynamodb_table.factory_status.arn]
  }

  statement {
    sid    = "DataStoreInventoryRead"
    effect = "Allow"

    actions = [
      "elasticache:DescribeReplicationGroups",
      "rds:DescribeDBInstances",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "S3CloudInfraFastSnapshotWrite"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/processed/cloud_infra/fast/*"]
  }
}

resource "aws_iam_role_policy" "cloud_infra_fast_collector" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-CloudInfraFastCollector"
  role   = aws_iam_role.cloud_infra_fast_collector.id
  policy = data.aws_iam_policy_document.cloud_infra_fast_collector.json
}

resource "aws_lambda_function" "cloud_infra_fast_collector" {
  function_name    = var.lambda_cloud_infra_fast_collector_name
  role             = aws_iam_role.cloud_infra_fast_collector.arn
  runtime          = "python3.12"
  handler          = "lambda_fast.handler"
  filename         = data.archive_file.cloud_infra_collector_zip.output_path
  source_code_hash = data.archive_file.cloud_infra_collector_zip.output_base64sha256
  timeout          = var.lambda_cloud_infra_fast_collector_timeout
  memory_size      = var.lambda_cloud_infra_fast_collector_memory

  environment {
    variables = merge(
      {
        DYNAMODB_TABLE_NAME           = data.aws_dynamodb_table.factory_status.name
        S3_BUCKET_NAME                = data.aws_s3_bucket.data.bucket
        FAST_HISTORY_TTL_HOURS        = tostring(var.cloud_infra_fast_history_ttl_hours)
        FAST_METRIC_WINDOW_MINUTES    = tostring(var.cloud_infra_fast_metric_window_minutes)
        ECS_CLUSTER_NAME              = var.cloud_infra_ecs_cluster_name
        ECS_SERVICE_NAME              = var.cloud_infra_ecs_service_name
        ALB_TARGET_GROUP_NAME         = var.cloud_infra_alb_target_group_name
        PIPELINE_LAMBDA_NAMES         = join(",", var.cloud_infra_pipeline_lambda_names)
        MONITORED_DYNAMODB_TABLE_NAME = data.aws_dynamodb_table.factory_status.name
        SCHEDULER_NAMES               = join(",", var.cloud_infra_scheduler_names)
        FACTORY_IDS                   = join(",", var.cloud_infra_factory_ids)
      },
      var.cloud_infra_fast_collector_cloudfront_distribution_id == null ? {} : {
        CLOUDFRONT_DISTRIBUTION_ID = var.cloud_infra_fast_collector_cloudfront_distribution_id
      },
      var.cloud_infra_fast_collector_dlq_queue_name == null ? {} : {
        DLQ_QUEUE_NAME = var.cloud_infra_fast_collector_dlq_queue_name
      },
      var.cloud_infra_fast_collector_rds_db_instance_id == null ? {} : {
        RDS_DB_INSTANCE_ID = var.cloud_infra_fast_collector_rds_db_instance_id
      },
      var.cloud_infra_fast_collector_redis_replication_group_id == null ? {} : {
        REDIS_REPLICATION_GROUP_ID = var.cloud_infra_fast_collector_redis_replication_group_id
      }
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.cloud_infra_fast_collector,
    aws_iam_role_policy.cloud_infra_fast_collector,
  ]

  tags = local.tags
}

resource "aws_iam_role" "cloud_infra_fast_collector_scheduler" {
  name               = "${local.naming_prefix}-IAMRole-Scheduler-CloudInfraFastCollector"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "cloud_infra_fast_collector_scheduler" {
  statement {
    sid    = "InvokeCloudInfraFastCollector"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.cloud_infra_fast_collector.arn]
  }
}

resource "aws_iam_role_policy" "cloud_infra_fast_collector_scheduler" {
  name   = "${local.naming_prefix}-IAMPolicy-Scheduler-CloudInfraFastCollector"
  role   = aws_iam_role.cloud_infra_fast_collector_scheduler.id
  policy = data.aws_iam_policy_document.cloud_infra_fast_collector_scheduler.json
}

resource "aws_scheduler_schedule" "cloud_infra_fast_collector_1m" {
  name                         = "${local.naming_prefix}-Schedule-CloudInfraFastCollector1m"
  description                  = "Collect cloud infra fast dashboard metrics every minute."
  schedule_expression          = "rate(1 minute)"
  schedule_expression_timezone = "UTC"
  state                        = var.cloud_infra_fast_collector_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.cloud_infra_fast_collector.arn
    role_arn = aws_iam_role.cloud_infra_fast_collector_scheduler.arn
    input = jsonencode({
      collector = "fast"
    })
  }
}

resource "aws_lambda_permission" "cloud_infra_fast_collector_scheduler" {
  statement_id  = "AllowSchedulerInvokeCloudInfraFastCollector1m"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloud_infra_fast_collector.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.cloud_infra_fast_collector_1m.arn
}
