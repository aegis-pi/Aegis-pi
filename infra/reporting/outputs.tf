output "data_bucket_name" {
  description = "Existing S3 bucket used for processed input and reports output."
  value       = data.aws_s3_bucket.data.bucket
}

output "state_machine_name" {
  description = "Daily factory report Step Functions state machine name."
  value       = aws_sfn_state_machine.daily_factory_report.name
}

output "state_machine_arn" {
  description = "Daily factory report Step Functions state machine ARN."
  value       = aws_sfn_state_machine.daily_factory_report.arn
}

output "scheduler_name" {
  description = "EventBridge Scheduler schedule name."
  value       = aws_scheduler_schedule.daily_factory_report.name
}

output "lambda_function_names" {
  description = "Reporting Lambda function names."
  value = {
    for key, function in aws_lambda_function.reporting :
    key => function.function_name
  }
}

