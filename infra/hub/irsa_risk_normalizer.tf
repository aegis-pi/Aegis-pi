data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "risk_normalizer_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }

    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_provider}:sub"
      values   = [local.risk_normalizer_subject]
    }
  }
}

resource "aws_iam_role" "risk_normalizer_irsa" {
  name               = local.resource_names.risk_normalizer_irsa
  assume_role_policy = data.aws_iam_policy_document.risk_normalizer_assume_role.json
}

data "aws_iam_policy_document" "risk_normalizer_s3" {
  statement {
    sid    = "ListScopedDataPrefixes"
    effect = "Allow"

    actions = ["s3:ListBucket"]

    resources = [
      "arn:aws:s3:::${var.data_bucket_name}",
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        "raw/${var.risk_factory_id}",
        "raw/${var.risk_factory_id}/",
        "raw/${var.risk_factory_id}/*",
        "processed",
        "processed/",
        "processed/*",
        "latest/${var.risk_factory_id}",
        "latest/${var.risk_factory_id}/",
        "latest/${var.risk_factory_id}/*",
      ]
    }
  }

  statement {
    sid    = "ReadFactoryRawObjects"
    effect = "Allow"

    actions = ["s3:GetObject"]

    resources = [
      "arn:aws:s3:::${var.data_bucket_name}/raw/${var.risk_factory_id}/*",
    ]
  }

  statement {
    sid    = "WriteProcessedAndLatestObjects"
    effect = "Allow"

    actions = ["s3:PutObject"]

    resources = [
      "arn:aws:s3:::${var.data_bucket_name}/processed/*",
      "arn:aws:s3:::${var.data_bucket_name}/latest/${var.risk_factory_id}/*",
    ]
  }
}

resource "aws_iam_role_policy" "risk_normalizer_s3" {
  name   = "${local.naming_prefix}-IAMPolicy-IRSA-risk-normalizer-S3"
  role   = aws_iam_role.risk_normalizer_irsa.id
  policy = data.aws_iam_policy_document.risk_normalizer_s3.json
}
