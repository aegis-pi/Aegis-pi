# DynamoDB table lives in infra/foundation (persistent). Look it up by name.
data "aws_dynamodb_table" "factory_status" {
  name = var.dynamodb_table_name
}
