# ── Infrastructure Outputs ────────────────────────────────────────────────────

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "ALB DNS name — use for api.pampgroup.com A record"
}

output "cloudfront_domain" {
  value       = aws_cloudfront_distribution.web.domain_name
  description = "CloudFront domain — use for app.pampgroup.com alias"
}

output "rds_endpoint" {
  value       = module.rds.db_instance_endpoint
  description = "Primary RDS endpoint for DATABASE_URL"
  sensitive   = true
}

output "rds_read_replica_endpoint" {
  value       = var.environment == "production" ? aws_db_instance.read_replica[0].endpoint : null
  description = "Read replica endpoint for DATABASE_URL_READ_REPLICA"
  sensitive   = true
}

output "redis_endpoint" {
  value       = "${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379"
  description = "Redis primary endpoint for REDIS_URL"
  sensitive   = true
}

output "s3_buckets" {
  value = {
    documents = aws_s3_bucket.documents.bucket
    redacted  = aws_s3_bucket.redacted.bucket
    exports   = aws_s3_bucket.exports.bucket
    backups   = aws_s3_bucket.backups.bucket
  }
  description = "S3 bucket names"
}

output "ecs_cluster_name" {
  value       = aws_ecs_cluster.main.name
  description = "ECS cluster name"
}

output "nameservers" {
  value       = aws_route53_zone.main.name_servers
  description = "Route53 nameservers — set these at your domain registrar"
}
