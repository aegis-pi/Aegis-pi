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
    sid    = "WriteFactoryRawObjects"
    effect = "Allow"

    actions = [
      "s3:PutObject",
    ]

    resources = [
      "${aws_s3_bucket.data.arn}/raw/${var.iot_factory_id}/*",
    ]
  }
}

resource "aws_iam_role_policy" "iot_rule_s3" {
  name   = "${local.naming_prefix}-IAMPolicy-IoTRule-S3"
  role   = aws_iam_role.iot_rule_s3.id
  policy = data.aws_iam_policy_document.iot_rule_s3.json
}

resource "aws_iot_topic_rule" "factory_raw_to_s3" {
  name        = local.iot_rule_name
  description = "Route ${var.iot_factory_id} IoT messages to the Aegis raw S3 prefix."
  enabled     = var.iot_rule_enabled
  sql         = "SELECT *, topic(3) AS source_type, timestamp() AS received_at FROM '${local.iot_topic_prefix}/+'"
  sql_version = "2016-03-23"

  s3 {
    bucket_name = aws_s3_bucket.data.bucket
    key         = local.iot_s3_key
    role_arn    = aws_iam_role.iot_rule_s3.arn
  }

  depends_on = [
    aws_iam_role_policy.iot_rule_s3,
  ]
}
