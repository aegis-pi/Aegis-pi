resource "aws_cloudwatch_log_group" "cloud_infra_slow_collector" {
  name              = "/aws/lambda/${var.lambda_cloud_infra_slow_collector_name}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_role" "cloud_infra_slow_collector" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-CloudInfraSlowCollector"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "cloud_infra_slow_collector" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.cloud_infra_slow_collector.arn}:*"]
  }

  statement {
    sid    = "EksManagementRead"
    effect = "Allow"

    actions = [
      "eks:DescribeCluster",
      "eks:ListNodegroups",
      "eks:DescribeNodegroup",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AutoScalingRead"
    effect = "Allow"

    actions = ["autoscaling:DescribeAutoScalingGroups"]

    resources = ["*"]
  }

  statement {
    sid    = "S3FreshnessList"
    effect = "Allow"

    actions = ["s3:ListBucket"]

    resources = [data.aws_s3_bucket.data.arn]
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
    sid    = "S3CloudInfraSlowSnapshotWrite"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/processed/cloud_infra/slow/*"]
  }
}

resource "aws_iam_role_policy" "cloud_infra_slow_collector" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-CloudInfraSlowCollector"
  role   = aws_iam_role.cloud_infra_slow_collector.id
  policy = data.aws_iam_policy_document.cloud_infra_slow_collector.json
}

resource "aws_eks_access_entry" "cloud_infra_slow_collector" {
  cluster_name  = var.cloud_infra_eks_cluster_name
  principal_arn = aws_iam_role.cloud_infra_slow_collector.arn
  type          = "STANDARD"
  tags          = local.tags
}

resource "aws_eks_access_policy_association" "cloud_infra_slow_collector_view" {
  cluster_name  = var.cloud_infra_eks_cluster_name
  principal_arn = aws_iam_role.cloud_infra_slow_collector.arn
  policy_arn    = "arn:${data.aws_partition.current.partition}:eks::aws:cluster-access-policy/AmazonEKSAdminViewPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [aws_eks_access_entry.cloud_infra_slow_collector]
}

resource "aws_lambda_function" "cloud_infra_slow_collector" {
  function_name    = var.lambda_cloud_infra_slow_collector_name
  role             = aws_iam_role.cloud_infra_slow_collector.arn
  runtime          = "python3.12"
  handler          = "lambda_slow.handler"
  filename         = data.archive_file.cloud_infra_collector_zip.output_path
  source_code_hash = data.archive_file.cloud_infra_collector_zip.output_base64sha256
  timeout          = var.lambda_cloud_infra_slow_collector_timeout
  memory_size      = var.lambda_cloud_infra_slow_collector_memory

  environment {
    variables = {
      DYNAMODB_TABLE_NAME      = data.aws_dynamodb_table.factory_status.name
      S3_BUCKET_NAME           = data.aws_s3_bucket.data.bucket
      SLOW_HISTORY_TTL_HOURS   = tostring(var.cloud_infra_slow_history_ttl_hours)
      EKS_CLUSTER_NAME         = var.cloud_infra_eks_cluster_name
      S3_LATEST_LOOKBACK_HOURS = tostring(var.cloud_infra_s3_latest_lookback_hours)
      FACTORY_IDS              = join(",", var.cloud_infra_factory_ids)
      ARGOCD_NAMESPACE         = var.cloud_infra_argocd_namespace
      K8S_TOP_PODS_LIMIT       = tostring(var.cloud_infra_k8s_top_pods_limit)
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.cloud_infra_slow_collector,
    aws_iam_role_policy.cloud_infra_slow_collector,
    aws_eks_access_policy_association.cloud_infra_slow_collector_view,
  ]

  tags = local.tags
}

resource "aws_iam_role" "cloud_infra_slow_collector_scheduler" {
  name               = "${local.naming_prefix}-IAMRole-Scheduler-CloudInfraSlowCollector"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "cloud_infra_slow_collector_scheduler" {
  statement {
    sid    = "InvokeCloudInfraSlowCollector"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.cloud_infra_slow_collector.arn]
  }
}

resource "aws_iam_role_policy" "cloud_infra_slow_collector_scheduler" {
  name   = "${local.naming_prefix}-IAMPolicy-Scheduler-CloudInfraSlowCollector"
  role   = aws_iam_role.cloud_infra_slow_collector_scheduler.id
  policy = data.aws_iam_policy_document.cloud_infra_slow_collector_scheduler.json
}

resource "aws_scheduler_schedule" "cloud_infra_slow_collector_5m" {
  name                         = "${local.naming_prefix}-Schedule-CloudInfraSlowCollector5m"
  description                  = "Collect cloud infra slow dashboard metrics every 5 minutes."
  schedule_expression          = "rate(5 minutes)"
  schedule_expression_timezone = "UTC"
  state                        = var.cloud_infra_slow_collector_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.cloud_infra_slow_collector.arn
    role_arn = aws_iam_role.cloud_infra_slow_collector_scheduler.arn
    input = jsonencode({
      collector = "slow"
    })
  }
}

resource "aws_lambda_permission" "cloud_infra_slow_collector_scheduler" {
  statement_id  = "AllowSchedulerInvokeCloudInfraSlowCollector5m"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloud_infra_slow_collector.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.cloud_infra_slow_collector_5m.arn
}
