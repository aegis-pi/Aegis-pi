data "archive_file" "risk_alert_dispatcher_zip" {
  type             = "zip"
  source_dir       = "${path.module}/../../apps/risk-alert-dispatcher"
  output_path      = "${path.module}/lambda_risk_alert_dispatcher.zip"
  output_file_mode = "0644"
  excludes         = ["**/__pycache__/**", "**/*.pyc", "**/*.pyo", "tests/**", ".pytest_cache/**"]
}

locals {
  risk_alert_slack_webhook_secret_id = var.risk_alert_slack_webhook_secret_arn == "" ? aws_secretsmanager_secret.risk_alert_slack_webhook.arn : var.risk_alert_slack_webhook_secret_arn
  risk_alert_slack_webhook_secret_ids = merge(
    {
      cloud = local.risk_alert_slack_webhook_secret_id
    },
    {
      for scope, secret in aws_secretsmanager_secret.risk_alert_slack_webhook_factory : scope => secret.arn
    }
  )
}

resource "aws_secretsmanager_secret" "risk_alert_slack_webhook" {
  name                    = var.risk_alert_slack_webhook_secret_name
  description             = "Slack webhook URL for AEGIS RiskAlertDispatcher Lambda. Secret value is injected by build-data-pipe.sh."
  recovery_window_in_days = 0
  tags                    = local.tags
}

resource "aws_secretsmanager_secret" "risk_alert_slack_webhook_factory" {
  for_each = var.risk_alert_factory_slack_webhook_secret_names

  name                    = each.value
  description             = "Slack webhook URL for AEGIS RiskAlertDispatcher ${each.key} alerts. Secret value is injected by build-data-pipe.sh."
  recovery_window_in_days = 0
  tags                    = local.tags
}

resource "aws_cloudwatch_log_group" "risk_alert_dispatcher" {
  name              = "/aws/lambda/${var.lambda_risk_alert_dispatcher_name}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_role" "risk_alert_dispatcher" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-RiskAlertDispatcher"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "risk_alert_dispatcher" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.risk_alert_dispatcher.arn}:*"]
  }

  statement {
    sid    = "S3ProcessedRead"
    effect = "Allow"

    actions = ["s3:GetObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/processed/*"]
  }

  statement {
    sid    = "DynamoDBAlertStateUpdate"
    effect = "Allow"

    actions = ["dynamodb:UpdateItem"]

    resources = [data.aws_dynamodb_table.factory_status.arn]
  }

  statement {
    sid    = "SlackWebhookSecretRead"
    effect = "Allow"

    actions = ["secretsmanager:GetSecretValue"]

    resources = values(local.risk_alert_slack_webhook_secret_ids)
  }

  dynamic "statement" {
    for_each = var.risk_alert_slack_webhook_ssm_parameter_name == "" ? [] : [var.risk_alert_slack_webhook_ssm_parameter_name]

    content {
      sid    = "SlackWebhookParameterRead"
      effect = "Allow"

      actions = ["ssm:GetParameter"]

      resources = [
        "arn:${data.aws_partition.current.partition}:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${startswith(statement.value, "/") ? "" : "/"}${statement.value}"
      ]
    }
  }
}

resource "aws_iam_role_policy" "risk_alert_dispatcher" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-RiskAlertDispatcher"
  role   = aws_iam_role.risk_alert_dispatcher.id
  policy = data.aws_iam_policy_document.risk_alert_dispatcher.json
}

resource "aws_lambda_function" "risk_alert_dispatcher" {
  function_name                  = var.lambda_risk_alert_dispatcher_name
  role                           = aws_iam_role.risk_alert_dispatcher.arn
  runtime                        = "python3.12"
  handler                        = "lambda_function.handler"
  filename                       = data.archive_file.risk_alert_dispatcher_zip.output_path
  source_code_hash               = data.archive_file.risk_alert_dispatcher_zip.output_base64sha256
  timeout                        = var.lambda_risk_alert_dispatcher_timeout
  memory_size                    = var.lambda_risk_alert_dispatcher_memory
  reserved_concurrent_executions = var.lambda_risk_alert_dispatcher_reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE_NAME                             = data.aws_dynamodb_table.factory_status.name
      ALERT_STATE_TTL_SECONDS                         = tostring(var.risk_alert_state_ttl_seconds)
      SLACK_HTTP_TIMEOUT_SECONDS                      = tostring(var.risk_alert_slack_http_timeout_seconds)
      SLACK_WEBHOOK_SECRET_ID                         = local.risk_alert_slack_webhook_secret_id
      SLACK_WEBHOOK_SECRET_CLOUD                      = local.risk_alert_slack_webhook_secret_ids["cloud"]
      SLACK_WEBHOOK_SECRET_FACTORY_A                  = local.risk_alert_slack_webhook_secret_ids["factory-a"]
      SLACK_WEBHOOK_SECRET_FACTORY_B                  = local.risk_alert_slack_webhook_secret_ids["factory-b"]
      SLACK_WEBHOOK_SECRET_FACTORY_C                  = local.risk_alert_slack_webhook_secret_ids["factory-c"]
      SLACK_WEBHOOK_SSM_PARAMETER_NAME                = var.risk_alert_slack_webhook_ssm_parameter_name
      COOLDOWN_FACTORY_STATE_SNAPSHOT_WARNING_SECONDS = tostring(var.risk_alert_factory_warning_cooldown_seconds)
      COOLDOWN_FACTORY_STATE_SNAPSHOT_DANGER_SECONDS  = tostring(var.risk_alert_factory_danger_cooldown_seconds)
      COOLDOWN_CLOUD_INFRA_FAST_WARNING_SECONDS       = tostring(var.risk_alert_cloud_warning_cooldown_seconds)
      COOLDOWN_CLOUD_INFRA_FAST_DANGER_SECONDS        = tostring(var.risk_alert_cloud_danger_cooldown_seconds)
      COOLDOWN_CLOUD_INFRA_SLOW_WARNING_SECONDS       = tostring(var.risk_alert_cloud_warning_cooldown_seconds)
      COOLDOWN_CLOUD_INFRA_SLOW_DANGER_SECONDS        = tostring(var.risk_alert_cloud_danger_cooldown_seconds)
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.risk_alert_dispatcher,
    aws_iam_role_policy.risk_alert_dispatcher,
  ]

  tags = local.tags
}

resource "aws_lambda_permission" "risk_alert_dispatcher_s3" {
  statement_id  = "AllowS3InvokeRiskAlertDispatcher"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.risk_alert_dispatcher.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = data.aws_s3_bucket.data.arn
}

resource "aws_s3_bucket_notification" "data_processed_alerts" {
  count  = var.risk_alert_dispatcher_s3_trigger_enabled ? 1 : 0
  bucket = data.aws_s3_bucket.data.id

  dynamic "lambda_function" {
    for_each = toset(var.risk_alert_dispatcher_s3_prefixes)

    content {
      lambda_function_arn = aws_lambda_function.risk_alert_dispatcher.arn
      events              = ["s3:ObjectCreated:*"]
      filter_prefix       = lambda_function.value
      filter_suffix       = ".json"
    }
  }

  depends_on = [aws_lambda_permission.risk_alert_dispatcher_s3]
}
