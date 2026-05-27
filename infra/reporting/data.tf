data "aws_s3_bucket" "data" {
  bucket = var.data_bucket_name
}

data "aws_caller_identity" "current" {}

