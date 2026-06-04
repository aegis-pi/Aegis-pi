data "archive_file" "daily_report_generator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../apps/daily-report-generator"
  output_path = "${path.module}/lambda_daily_report_generator.zip"
  excludes = [
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "tests/**",
    ".pytest_cache/**",
    "scripts/backfill_daily_reports.py",
    "scripts/inventory_daily_report_backfill.py",
    "scripts/invoke_reporting_lambdas_backfill.py",
  ]
}

resource "aws_cloudwatch_log_group" "reporting_lambda" {
  for_each = local.lambda_functions

  name              = "/aws/lambda/${each.value.name}"
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

resource "aws_iam_role" "reporting_lambda" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-Reporting"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "reporting_lambda" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      for log_group in aws_cloudwatch_log_group.reporting_lambda :
      "${log_group.arn}:*"
    ]
  }

  statement {
    sid    = "S3BucketList"
    effect = "Allow"

    actions = ["s3:ListBucket"]

    resources = [data.aws_s3_bucket.data.arn]
  }

  statement {
    sid    = "S3ProcessedAndReportRead"
    effect = "Allow"

    actions = ["s3:GetObject"]

    resources = [
      "${data.aws_s3_bucket.data.arn}/processed/*",
      "${data.aws_s3_bucket.data.arn}/processed/cloud_infra/*",
      "${data.aws_s3_bucket.data.arn}/reports/daily/*",
    ]
  }

  statement {
    sid    = "S3ReportWrite"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/reports/daily/*"]
  }

  statement {
    sid    = "BedrockInvokeModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]

    resources = [
      "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}",
    ]
  }
}

resource "aws_iam_role_policy" "reporting_lambda" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-Reporting"
  role   = aws_iam_role.reporting_lambda.id
  policy = data.aws_iam_policy_document.reporting_lambda.json
}

resource "aws_lambda_function" "reporting" {
  for_each = local.lambda_functions

  function_name    = each.value.name
  role             = aws_iam_role.reporting_lambda.arn
  runtime          = "python3.12"
  handler          = each.value.handler
  filename         = data.archive_file.daily_report_generator_zip.output_path
  source_code_hash = data.archive_file.daily_report_generator_zip.output_base64sha256
  timeout          = each.value.timeout
  memory_size      = each.value.memory

  environment {
    variables = {
      S3_BUCKET_NAME          = data.aws_s3_bucket.data.bucket
      REPORT_TIMEZONE         = var.report_timezone
      REPORT_OUTPUT_PREFIX    = var.report_output_prefix
      REPORT_DATASETS         = var.report_datasets
      REPORT_AUX_DATASETS     = "state_snapshot"
      REPORT_FACTORY_IDS      = var.report_factory_ids
      BEDROCK_MODEL_ID        = var.bedrock_model_id
      BEDROCK_MAX_TOKENS      = tostring(var.bedrock_max_tokens)
      BEDROCK_TEMPERATURE     = tostring(var.bedrock_temperature)
      S3_GET_CONCURRENCY      = "16"
      MAX_OBJECTS_PER_HOUR    = "10000"
      MAX_CONTEXT_BYTES       = "120000"
      MAX_CONTEXT_EVENTS      = "10"
      REPORT_OUTPUT_FORMATS   = "md"
      EVENT_MERGE_GAP_SECONDS = "120"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.reporting_lambda,
    aws_iam_role_policy.reporting_lambda,
  ]

  tags = local.tags
}
