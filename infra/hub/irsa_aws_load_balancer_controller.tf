data "aws_iam_policy_document" "aws_lb_controller_assume_role" {
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
      values   = [local.aws_lb_controller_subject]
    }
  }
}

resource "aws_iam_role" "aws_lb_controller_irsa" {
  name               = local.resource_names.aws_lb_controller_irsa
  assume_role_policy = data.aws_iam_policy_document.aws_lb_controller_assume_role.json
}

resource "aws_iam_policy" "aws_lb_controller" {
  name        = local.resource_names.aws_lb_controller_policy
  description = "AWS Load Balancer Controller policy for AEGIS Hub EKS"
  policy      = file("${path.module}/aws_load_balancer_controller_iam_policy.json")
}

resource "aws_iam_role_policy_attachment" "aws_lb_controller" {
  role       = aws_iam_role.aws_lb_controller_irsa.name
  policy_arn = aws_iam_policy.aws_lb_controller.arn
}
