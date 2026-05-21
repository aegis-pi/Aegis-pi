locals {
  naming_prefix = "AEGIS"

  iot_topic_prefix = "${var.iot_topic_root}/${var.iot_factory_id}"
  iot_rule_name    = "${local.naming_prefix}_IoTRule_${replace(var.iot_factory_id, "-", "_")}_raw_s3"
  iot_s3_key       = "raw/${var.iot_factory_id}/$${topic(3)}/yyyy=$${parse_time(\"yyyy\", timestamp(), \"UTC\")}/mm=$${parse_time(\"MM\", timestamp(), \"UTC\")}/dd=$${parse_time(\"dd\", timestamp(), \"UTC\")}/$${get_or_default(message_id, newuuid())}.json"

  iot_s3_key_factory_b = "raw/factory-b/$${topic(3)}/yyyy=$${parse_time(\"yyyy\", timestamp(), \"UTC\")}/mm=$${parse_time(\"MM\", timestamp(), \"UTC\")}/dd=$${parse_time(\"dd\", timestamp(), \"UTC\")}/$${get_or_default(message_id, newuuid())}.json"
  iot_s3_key_factory_c = "raw/factory-c/$${topic(3)}/yyyy=$${parse_time(\"yyyy\", timestamp(), \"UTC\")}/mm=$${parse_time(\"MM\", timestamp(), \"UTC\")}/dd=$${parse_time(\"dd\", timestamp(), \"UTC\")}/$${get_or_default(message_id, newuuid())}.json"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Component   = "data-pipeline"
  }
}
