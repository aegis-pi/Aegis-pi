data "aws_iam_policy_document" "grafana_amp_query_assume_role" {
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
      values   = [local.grafana_amp_query_subject]
    }
  }
}

resource "aws_iam_role" "grafana_amp_query_irsa" {
  name               = local.resource_names.grafana_amp_query_irsa
  assume_role_policy = data.aws_iam_policy_document.grafana_amp_query_assume_role.json
}

data "aws_iam_policy_document" "grafana_amp_query" {
  statement {
    sid    = "QueryHubAmpWorkspace"
    effect = "Allow"

    actions = [
      "aps:GetLabels",
      "aps:GetMetricMetadata",
      "aps:GetSeries",
      "aps:QueryMetrics",
    ]

    resources = [
      data.terraform_remote_state.foundation.outputs.amp_workspace_arn,
    ]
  }
}

resource "aws_iam_role_policy" "grafana_amp_query" {
  name   = "${local.naming_prefix}-IAMPolicy-IRSA-grafana-amp-query"
  role   = aws_iam_role.grafana_amp_query_irsa.id
  policy = data.aws_iam_policy_document.grafana_amp_query.json
}
