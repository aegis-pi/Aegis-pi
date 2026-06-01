data "archive_file" "data_processor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../apps/data-processor"
  output_path = "${path.module}/lambda_data_processor.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc", "**/*.pyo", "tests/**", ".pytest_cache/**"]
}

resource "aws_cloudwatch_log_group" "data_processor" {
  name              = "/aws/lambda/${var.lambda_data_processor_name}"
  retention_in_days = 30
  tags              = local.tags
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "data_processor" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-DataProcessor"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "data_processor" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.data_processor.arn}:*"]
  }

  statement {
    sid    = "DynamoDBReadWrite"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]

    resources = [data.aws_dynamodb_table.factory_status.arn]
  }

  statement {
    sid    = "S3ProcessedWrite"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/processed/*"]
  }
}

resource "aws_iam_role_policy" "data_processor" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-DataProcessor"
  role   = aws_iam_role.data_processor.id
  policy = data.aws_iam_policy_document.data_processor.json
}

resource "aws_lambda_function" "data_processor" {
  function_name    = var.lambda_data_processor_name
  role             = aws_iam_role.data_processor.arn
  runtime          = "python3.12"
  handler          = "lambda_function.handler"
  filename         = data.archive_file.data_processor_zip.output_path
  source_code_hash = data.archive_file.data_processor_zip.output_base64sha256
  timeout          = var.lambda_data_processor_timeout
  memory_size      = var.lambda_data_processor_memory

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = data.aws_dynamodb_table.factory_status.name
      FACTORY_IDS         = join(",", var.data_processor_factory_ids)
      S3_BUCKET_NAME      = data.aws_s3_bucket.data.bucket
      HISTORY_TTL_HOURS   = tostring(var.dynamodb_history_ttl_hours)
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.data_processor,
    aws_iam_role_policy.data_processor,
  ]

  tags = local.tags
}

resource "aws_lambda_permission" "iot_factory_a" {
  statement_id  = "AllowIoTInvokeFactoryA"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_processor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.factory_raw_to_s3.arn
}

resource "aws_lambda_permission" "iot_factory_b" {
  statement_id  = "AllowIoTInvokeFactoryB"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_processor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.factory_b_raw_s3.arn
}

resource "aws_lambda_permission" "iot_factory_c" {
  statement_id  = "AllowIoTInvokeFactoryC"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_processor.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.factory_c_raw_s3.arn
}

resource "aws_iam_role" "data_processor_scheduler" {
  name               = "${local.naming_prefix}-IAMRole-Scheduler-DataProcessorRefresh"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "data_processor_scheduler" {
  statement {
    sid    = "InvokeDataProcessorRefresh"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [aws_lambda_function.data_processor.arn]
  }
}

resource "aws_iam_role_policy" "data_processor_scheduler" {
  name   = "${local.naming_prefix}-IAMPolicy-Scheduler-DataProcessorRefresh"
  role   = aws_iam_role.data_processor_scheduler.id
  policy = data.aws_iam_policy_document.data_processor_scheduler.json
}

resource "aws_scheduler_schedule" "data_processor_refresh_1m" {
  name                         = "${local.naming_prefix}-Schedule-DataProcessorRefresh1m"
  description                  = "Refresh factory pipeline freshness and risk when IoT messages stop."
  schedule_expression          = "rate(1 minute)"
  schedule_expression_timezone = "UTC"
  state                        = var.data_processor_refresh_enabled ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.data_processor.arn
    role_arn = aws_iam_role.data_processor_scheduler.arn
    input = jsonencode({
      action    = "refresh_pipeline_status"
      factories = var.data_processor_factory_ids
    })
  }
}

resource "aws_lambda_permission" "data_processor_scheduler" {
  statement_id  = "AllowSchedulerInvokeDataProcessorRefresh"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_processor.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.data_processor_refresh_1m.arn
}
