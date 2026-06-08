data "archive_file" "snapshot_presigner_zip" {
  type             = "zip"
  source_file      = "${path.module}/../../apps/snapshot-presigner/lambda_function.py"
  output_path      = "${path.module}/lambda_snapshot_presigner.zip"
  output_file_mode = "0644"
}

resource "aws_cloudwatch_log_group" "snapshot_presigner" {
  name              = "/aws/lambda/${var.lambda_snapshot_presigner_name}"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_iam_role" "snapshot_presigner" {
  name               = "${local.naming_prefix}-IAMRole-Lambda-SnapshotPresigner"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "snapshot_presigner" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = ["${aws_cloudwatch_log_group.snapshot_presigner.arn}:*"]
  }

  statement {
    sid    = "PresignImageSnapshotPut"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = ["${data.aws_s3_bucket.data.arn}/image_snapshot/*"]
  }
}

resource "aws_iam_role_policy" "snapshot_presigner" {
  name   = "${local.naming_prefix}-IAMPolicy-Lambda-SnapshotPresigner"
  role   = aws_iam_role.snapshot_presigner.id
  policy = data.aws_iam_policy_document.snapshot_presigner.json
}

resource "aws_lambda_function" "snapshot_presigner" {
  function_name    = var.lambda_snapshot_presigner_name
  role             = aws_iam_role.snapshot_presigner.arn
  runtime          = "python3.12"
  handler          = "lambda_function.handler"
  filename         = data.archive_file.snapshot_presigner_zip.output_path
  source_code_hash = data.archive_file.snapshot_presigner_zip.output_base64sha256
  timeout          = var.lambda_snapshot_presigner_timeout
  memory_size      = var.lambda_snapshot_presigner_memory

  environment {
    variables = {
      ALLOWED_FACTORY_IDS        = join(",", var.snapshot_presigner_allowed_factory_ids)
      MAX_FILE_BYTES             = tostring(var.snapshot_presigner_max_file_bytes)
      PRESIGN_EXPIRES_IN_SECONDS = tostring(var.snapshot_presigner_expires_in_seconds)
      PRESIGN_SHARED_TOKEN       = var.snapshot_presigner_shared_token
      S3_BUCKET_NAME             = data.aws_s3_bucket.data.bucket
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.snapshot_presigner,
    aws_iam_role_policy.snapshot_presigner,
  ]

  tags = local.tags
}

resource "aws_apigatewayv2_api" "snapshot_presigner" {
  name          = "${local.naming_prefix}-HTTPAPI-SnapshotPresigner"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["Authorization", "Content-Type"]
    allow_methods = ["OPTIONS", "POST"]
    allow_origins = ["*"]
    max_age       = 300
  }

  tags = local.tags
}

resource "aws_apigatewayv2_integration" "snapshot_presigner" {
  api_id                 = aws_apigatewayv2_api.snapshot_presigner.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.snapshot_presigner.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "snapshot_presigner" {
  api_id    = aws_apigatewayv2_api.snapshot_presigner.id
  route_key = "POST /image-snapshot/presign"
  target    = "integrations/${aws_apigatewayv2_integration.snapshot_presigner.id}"
}

resource "aws_apigatewayv2_stage" "snapshot_presigner" {
  api_id      = aws_apigatewayv2_api.snapshot_presigner.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = var.snapshot_presigner_throttle_burst_limit
    throttling_rate_limit  = var.snapshot_presigner_throttle_rate_limit
  }

  tags = local.tags
}

resource "aws_lambda_permission" "snapshot_presigner_api" {
  statement_id  = "AllowAPIGatewayInvokeSnapshotPresigner"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.snapshot_presigner.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.snapshot_presigner.execution_arn}/*/*/image-snapshot/presign"
}
