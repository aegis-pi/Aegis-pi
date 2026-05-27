data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.naming_prefix}-IAMRole-Scheduler-DailyFactoryReport"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid    = "StartDailyFactoryReportStateMachine"
    effect = "Allow"

    actions = ["states:StartExecution"]

    resources = [aws_sfn_state_machine.daily_factory_report.arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${local.naming_prefix}-IAMPolicy-Scheduler-DailyFactoryReport"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

resource "aws_scheduler_schedule" "daily_factory_report" {
  name                         = local.scheduler_name
  description                  = "Run daily factory reports at 00:30 KST."
  schedule_expression          = var.schedule_expression
  schedule_expression_timezone = "UTC"
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.daily_factory_report.arn
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      timezone    = var.report_timezone
      factories   = split(",", var.report_factory_ids)
      report_type = "daily_factory_operations_draft"
    })
  }

  depends_on = [aws_iam_role_policy.scheduler]
}

