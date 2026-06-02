resource "aws_cloudwatch_log_group" "state_machine" {
  name              = "/aws/vendedlogs/states/${local.state_machine_name}"
  retention_in_days = 30
  tags              = local.tags
}

data "aws_iam_policy_document" "sfn_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${local.naming_prefix}-IAMRole-SFN-DailyFactoryReport"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "sfn" {
  statement {
    sid    = "InvokeReportingLambdas"
    effect = "Allow"

    actions = ["lambda:InvokeFunction"]

    resources = [
      for function in aws_lambda_function.reporting :
      function.arn
    ]
  }

  statement {
    sid    = "StateMachineLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  name   = "${local.naming_prefix}-IAMPolicy-SFN-DailyFactoryReport"
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn.json
}

resource "aws_sfn_state_machine" "daily_factory_report" {
  name     = local.state_machine_name
  role_arn = aws_iam_role.sfn.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment = "Daily factory report pipeline"
    StartAt = "PrepareReportWindow"
    States = {
      PrepareReportWindow = {
        Type     = "Task"
        Resource = aws_lambda_function.reporting["prepare_report_window"].arn
        Next     = "ReportTargetMap"
      }
      ReportTargetMap = {
        Type           = "Map"
        ItemsPath      = "$.report_targets"
        MaxConcurrency = 4
        Iterator = {
          StartAt = "SelectReportTarget"
          States = {
            SelectReportTarget = {
              Type = "Choice"
              Choices = [
                {
                  Variable     = "$.target_type"
                  StringEquals = "factory"
                  Next         = "FactoryHourMap"
                },
                {
                  Variable     = "$.target_type"
                  StringEquals = "cloud_infra"
                  Next         = "CloudInfraHourMap"
                }
              ]
              Default = "UnsupportedReportTarget"
            }
            FactoryHourMap = {
              Type           = "Map"
              ItemsPath      = "$.hour_items"
              MaxConcurrency = 6
              ItemSelector = {
                "factory_id.$"    = "$.factory_id"
                "report_date.$"   = "$.report_date"
                "timezone.$"      = "$.timezone"
                "datasets.$"      = "$.datasets"
                "output_prefix.$" = "$.output_prefix"
                "hour.$"          = "$$.Map.Item.Value.hour"
                "hour_window.$"   = "$$.Map.Item.Value.hour_window"
              }
              Iterator = {
                StartAt = "AggregateFactoryHour"
                States = {
                  AggregateFactoryHour = {
                    Type     = "Task"
                    Resource = aws_lambda_function.reporting["aggregate_factory_hour"].arn
                    End      = true
                  }
                }
              }
              ResultPath = "$.hour_results"
              Next       = "MergeFactoryDaily"
            }
            MergeFactoryDaily = {
              Type     = "Task"
              Resource = aws_lambda_function.reporting["merge_factory_daily"].arn
              Next     = "GenerateFactoryReport"
            }
            GenerateFactoryReport = {
              Type     = "Task"
              Resource = aws_lambda_function.reporting["generate_factory_report"].arn
              End      = true
            }
            CloudInfraHourMap = {
              Type           = "Map"
              ItemsPath      = "$.hour_items"
              MaxConcurrency = 6
              ItemSelector = {
                "target_id.$"     = "$.target_id"
                "report_date.$"   = "$.report_date"
                "timezone.$"      = "$.timezone"
                "output_prefix.$" = "$.output_prefix"
                "hour.$"          = "$$.Map.Item.Value.hour"
                "hour_window.$"   = "$$.Map.Item.Value.hour_window"
              }
              Iterator = {
                StartAt = "AggregateCloudInfraHour"
                States = {
                  AggregateCloudInfraHour = {
                    Type     = "Task"
                    Resource = aws_lambda_function.reporting["aggregate_cloud_infra_hour"].arn
                    End      = true
                  }
                }
              }
              ResultPath = "$.hour_results"
              Next       = "MergeCloudInfraDaily"
            }
            MergeCloudInfraDaily = {
              Type     = "Task"
              Resource = aws_lambda_function.reporting["merge_cloud_infra_daily"].arn
              Next     = "GenerateCloudInfraReport"
            }
            GenerateCloudInfraReport = {
              Type     = "Task"
              Resource = aws_lambda_function.reporting["generate_cloud_infra_report"].arn
              End      = true
            }
            UnsupportedReportTarget = {
              Type  = "Fail"
              Error = "UnsupportedReportTarget"
            }
          }
        }
        End = true
      }
    }
  })

  logging_configuration {
    include_execution_data = false
    level                  = "ERROR"
    log_destination        = "${aws_cloudwatch_log_group.state_machine.arn}:*"
  }

  depends_on = [aws_iam_role_policy.sfn]
  tags       = local.tags
}
