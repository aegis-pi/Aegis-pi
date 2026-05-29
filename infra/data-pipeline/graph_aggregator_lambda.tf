data "archive_file" "graph_aggregator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../apps/graph-metrics-aggregator"
  output_path = "${path.module}/lambda_graph_metrics_aggregator.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc", "**/*.pyo", "tests/**", ".pytest_cache/**"]
}

resource "aws_cloudwatch_log_group" "graph_aggregator" {
  name              = "/aws/lambda/${var.lambda_graph_aggregator_name}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_role" "graph_aggregator" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-GraphAggregator5m"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "graph_aggregator" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.graph_aggregator.arn}:*"]
  }

  statement {
    sid    = "DynamoDBGraphReadWrite"
    effect = "Allow"

    actions = [
      "dynamodb:Query",
      "dynamodb:PutItem",
    ]

    resources = [data.aws_dynamodb_table.factory_status.arn]
  }

  statement {
    sid    = "S3GraphAggregateWrite"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/processed_agg/*"]
  }
}

resource "aws_iam_role_policy" "graph_aggregator" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-GraphAggregator5m"
  role   = aws_iam_role.graph_aggregator.id
  policy = data.aws_iam_policy_document.graph_aggregator.json
}

resource "aws_lambda_function" "graph_aggregator" {
  function_name    = var.lambda_graph_aggregator_name
  role             = aws_iam_role.graph_aggregator.arn
  runtime          = "python3.12"
  handler          = "lambda_function.handler"
  filename         = data.archive_file.graph_aggregator_zip.output_path
  source_code_hash = data.archive_file.graph_aggregator_zip.output_base64sha256
  timeout          = var.lambda_graph_aggregator_timeout
  memory_size      = var.lambda_graph_aggregator_memory

  environment {
    variables = {
      DYNAMODB_TABLE_NAME              = data.aws_dynamodb_table.factory_status.name
      S3_BUCKET_NAME                   = data.aws_s3_bucket.data.bucket
      FACTORY_IDS                      = join(",", var.graph_aggregator_factory_ids)
      BUCKET_MINUTES                   = tostring(var.graph_bucket_minutes)
      LOOKBACK_BUCKETS                 = tostring(var.graph_aggregator_lookback_buckets)
      GRAPH_TTL_HOURS                  = tostring(var.graph_bucket_ttl_hours)
      EXPECTED_SAMPLE_INTERVAL_SECONDS = tostring(var.graph_expected_sample_interval_seconds)
      AI_SCORE_THRESHOLD               = tostring(var.graph_ai_score_threshold)
      S3_OUTPUT_PREFIX                 = "processed_agg"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.graph_aggregator,
    aws_iam_role_policy.graph_aggregator,
  ]

  tags = local.tags
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "graph_aggregator_scheduler" {
  name               = "${local.naming_prefix}-IAMRole-Scheduler-GraphAggregator5m"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "graph_aggregator_scheduler" {
  statement {
    sid    = "InvokeGraphAggregator"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.graph_aggregator.arn]
  }
}

resource "aws_iam_role_policy" "graph_aggregator_scheduler" {
  name   = "${local.naming_prefix}-IAMPolicy-Scheduler-GraphAggregator5m"
  role   = aws_iam_role.graph_aggregator_scheduler.id
  policy = data.aws_iam_policy_document.graph_aggregator_scheduler.json
}

resource "aws_scheduler_schedule" "graph_aggregator_5m" {
  name                         = "${local.naming_prefix}-Schedule-GraphAggregator5m"
  description                  = "Aggregate factory graph metrics every 5 minutes."
  schedule_expression          = "rate(5 minutes)"
  schedule_expression_timezone = "UTC"
  state                        = var.graph_aggregator_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.graph_aggregator.arn
    role_arn = aws_iam_role.graph_aggregator_scheduler.arn
    input = jsonencode({
      bucket_minutes = var.graph_bucket_minutes
    })
  }
}

resource "aws_lambda_permission" "graph_aggregator_scheduler" {
  statement_id  = "AllowSchedulerInvokeGraphAggregator5m"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.graph_aggregator.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.graph_aggregator_5m.arn
}

