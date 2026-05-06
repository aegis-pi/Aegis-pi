data "aws_iam_policy_document" "prometheus_remote_write_assume_role" {
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
      values   = [local.prometheus_remote_write_subject]
    }
  }
}

resource "aws_iam_role" "prometheus_remote_write_irsa" {
  name               = local.resource_names.prometheus_remote_write_irsa
  assume_role_policy = data.aws_iam_policy_document.prometheus_remote_write_assume_role.json
}

data "aws_iam_policy_document" "prometheus_remote_write_amp" {
  statement {
    sid    = "RemoteWriteToHubAmpWorkspace"
    effect = "Allow"

    actions = [
      "aps:RemoteWrite",
    ]

    resources = [
      data.terraform_remote_state.foundation.outputs.amp_workspace_arn,
    ]
  }
}

resource "aws_iam_role_policy" "prometheus_remote_write_amp" {
  name   = "${local.naming_prefix}-IAMPolicy-IRSA-prometheus-remote-write-AMP"
  role   = aws_iam_role.prometheus_remote_write_irsa.id
  policy = data.aws_iam_policy_document.prometheus_remote_write_amp.json
}
