resource "aws_route53_zone" "admin_ui" {
  name = var.admin_ui_domain_name

  tags = {
    Name = "${local.naming_prefix}-Route53Zone-admin-ui"
  }
}

resource "aws_acm_certificate" "admin_ui" {
  domain_name = var.admin_ui_domain_name

  subject_alternative_names = [
    local.admin_ui_argocd_host,
    local.admin_ui_grafana_host,
  ]

  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.naming_prefix}-ACM-admin-ui"
  }
}

resource "aws_route53_record" "admin_ui_certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.admin_ui.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.admin_ui.zone_id
}
