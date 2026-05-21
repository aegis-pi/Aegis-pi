data "aws_iam_policy_document" "iot_rule_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["iot.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "iot_rule_s3" {
  name               = "${local.naming_prefix}-IAMRole-IoTRule-S3"
  assume_role_policy = data.aws_iam_policy_document.iot_rule_assume_role.json
}

data "aws_iam_policy_document" "iot_rule_s3" {
  statement {
    sid    = "WriteAllFactoriesRawObjects"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      "${data.aws_s3_bucket.data.arn}/raw/factory-a/*",
      "${data.aws_s3_bucket.data.arn}/raw/factory-b/*",
      "${data.aws_s3_bucket.data.arn}/raw/factory-c/*",
    ]
  }
}

resource "aws_iam_role_policy" "iot_rule_s3" {
  name   = "${local.naming_prefix}-IAMPolicy-IoTRule-S3"
  role   = aws_iam_role.iot_rule_s3.id
  policy = data.aws_iam_policy_document.iot_rule_s3.json
}

# factory-a: S3 raw + Lambda
resource "aws_iot_topic_rule" "factory_raw_to_s3" {
  name        = local.iot_rule_name
  description = "Route ${var.iot_factory_id} IoT messages to S3 raw and Lambda data processor."
  enabled     = var.iot_rule_enabled
  sql         = "SELECT * FROM '${local.iot_topic_prefix}/+'"
  sql_version = "2016-03-23"

  s3 {
    bucket_name = data.aws_s3_bucket.data.bucket
    key         = local.iot_s3_key
    role_arn    = aws_iam_role.iot_rule_s3.arn
  }

  lambda {
    function_arn = aws_lambda_function.data_processor.arn
  }

  depends_on = [aws_iam_role_policy.iot_rule_s3]
}

# factory-b: S3 raw + Lambda
resource "aws_iot_topic_rule" "factory_b_raw_s3" {
  name        = "AEGIS_IoTRule_factory_b_raw_s3"
  description = "Route factory-b IoT messages to S3 raw and Lambda data processor."
  enabled     = true
  sql         = "SELECT * FROM 'aegis/factory-b/+'"
  sql_version = "2016-03-23"

  s3 {
    bucket_name = data.aws_s3_bucket.data.bucket
    key         = local.iot_s3_key_factory_b
    role_arn    = aws_iam_role.iot_rule_s3.arn
  }

  lambda {
    function_arn = aws_lambda_function.data_processor.arn
  }

  depends_on = [aws_iam_role_policy.iot_rule_s3]
}

# factory-c: S3 raw + Lambda
resource "aws_iot_topic_rule" "factory_c_raw_s3" {
  name        = "AEGIS_IoTRule_factory_c_raw_s3"
  description = "Route factory-c IoT messages to S3 raw and Lambda data processor."
  enabled     = true
  sql         = "SELECT * FROM 'aegis/factory-c/+'"
  sql_version = "2016-03-23"

  s3 {
    bucket_name = data.aws_s3_bucket.data.bucket
    key         = local.iot_s3_key_factory_c
    role_arn    = aws_iam_role.iot_rule_s3.arn
  }

  lambda {
    function_arn = aws_lambda_function.data_processor.arn
  }

  depends_on = [aws_iam_role_policy.iot_rule_s3]
}
