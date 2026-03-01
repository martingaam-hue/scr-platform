# ── CloudFront, WAF, ACM, and Route53 ────────────────────────────────────────

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# ── ACM Certificate (us-east-1 — required for CloudFront) ────────────────────

resource "aws_acm_certificate" "wildcard" {
  provider          = aws.us_east_1
  domain_name       = "*.pampgroup.com"
  validation_method = "DNS"

  subject_alternative_names = [
    "pampgroup.com",
    "app.pampgroup.com",
    "api.pampgroup.com",
    "custom.pampgroup.com", # White-label CNAME target
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# ── Route53 Hosted Zone and DNS Records ──────────────────────────────────────

resource "aws_route53_zone" "main" {
  name = "pampgroup.com"

  tags = {
    Name = "pampgroup.com"
  }
}

# ACM DNS validation records
resource "aws_route53_record" "acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.wildcard.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "wildcard" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.wildcard.arn
  validation_record_fqdns = [for record in aws_route53_record.acm_validation : record.fqdn]
}

# ── ACM Certificate (eu-west-1 — required for ALB) ───────────────────────────

resource "aws_acm_certificate" "alb" {
  domain_name       = "*.${var.domain_name}"
  validation_method = "DNS"

  subject_alternative_names = [
    var.domain_name,
    "app.${var.domain_name}",
    "api.${var.domain_name}",
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "alb" {
  certificate_arn         = aws_acm_certificate.alb.arn
  validation_record_fqdns = [for record in aws_route53_record.acm_validation : record.fqdn]
}

# app.pampgroup.com → CloudFront
resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "app.pampgroup.com"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.web.domain_name
    zone_id                = aws_cloudfront_distribution.web.hosted_zone_id
    evaluate_target_health = false
  }
}

# api.pampgroup.com → ALB
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.pampgroup.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# custom.pampgroup.com → CloudFront (CNAME target for white-label domains)
resource "aws_route53_record" "custom_cname_target" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "custom.pampgroup.com"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.web.domain_name
    zone_id                = aws_cloudfront_distribution.web.hosted_zone_id
    evaluate_target_health = false
  }
}

# ── WAF Web ACL ───────────────────────────────────────────────────────────────

resource "aws_wafv2_web_acl" "main" {
  provider = aws.us_east_1 # WAF for CloudFront must be in us-east-1
  name     = "scr-${var.environment}"
  scope    = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # SQL injection protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 10
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Common threat protection
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 20
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
        # Exclude rules that block large document uploads
        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
            count {}
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Bot detection
  rule {
    name     = "AWSManagedRulesBotControlRuleSet"
    priority = 30
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"
        managed_rule_group_configs {
          aws_managed_rules_bot_control_rule_set {
            inspection_level = "COMMON"
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "BotControlRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Known bad inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 40
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "KnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "scr-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Name = "scr-${var.environment}-waf"
  }
}

# ── CloudFront Distribution ───────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "web" {
  comment             = "SCR Platform ${var.environment}"
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "/"
  price_class         = "PriceClass_100" # US, EU, Canada only
  web_acl_id          = aws_wafv2_web_acl.main.arn

  aliases = var.environment == "production" ? [
    "app.pampgroup.com",
    "custom.pampgroup.com",
  ] : []

  # Origin: ALB (web + API)
  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "alb-origin"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default cache behavior: web frontend (no caching for app shell)
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "alb-origin"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    # Don't cache app shell — SPA routes must always reach origin
    default_ttl = 0
    min_ttl     = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["Host", "Authorization", "CloudFront-Viewer-Country"]
      cookies { forward = "all" }
    }
  }

  # Cache behavior: static assets (_next/static/*)
  ordered_cache_behavior {
    path_pattern           = "/_next/static/*"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "alb-origin"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    default_ttl = 31536000 # 1 year
    min_ttl     = 31536000
    max_ttl     = 31536000

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  # Pass-through: API routes (no caching)
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "alb-origin"
    viewer_protocol_policy = "redirect-to-https"

    default_ttl = 0
    min_ttl     = 0
    max_ttl     = 0

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies { forward = "all" }
    }
  }

  viewer_certificate {
    acm_certificate_arn            = var.environment == "production" ? aws_acm_certificate_validation.wildcard.certificate_arn : null
    ssl_support_method             = var.environment == "production" ? "sni-only" : null
    minimum_protocol_version       = var.environment == "production" ? "TLSv1.2_2021" : null
    cloudfront_default_certificate = var.environment != "production"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  logging_config {
    bucket          = aws_s3_bucket.exports.bucket_domain_name
    prefix          = "cloudfront-logs/"
    include_cookies = false
  }

  depends_on = [aws_acm_certificate_validation.wildcard]
}
