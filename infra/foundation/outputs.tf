output "data_bucket_name" {
  description = "S3 bucket name for Aegis data."
  value       = aws_s3_bucket.data.bucket
}

output "data_bucket_arn" {
  description = "S3 bucket ARN for Aegis data."
  value       = aws_s3_bucket.data.arn
}

output "data_bucket_prefixes" {
  description = "Standard data prefixes used by the Aegis data bucket."
  value       = local.data_prefixes
}

output "raw_object_key_template" {
  description = "Recommended raw object key template for IoT Core Rule S3 actions."
  value       = "raw/{factory_id}/{source_type}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json"
}

output "processed_object_key_template" {
  description = "Recommended processed object key template for normalized datasets."
  value       = "processed/{dataset}/{factory_id}/yyyy={YYYY}/mm={MM}/dd={DD}/{message_id}.json"
}
