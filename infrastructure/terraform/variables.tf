variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-west-1"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.medium"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.micro"
}

# ── ECS ───────────────────────────────────────────────────────────────────────

variable "api_cpu" {
  description = "ECS task CPU units for the API service (256 = 0.25 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "ECS task memory (MiB) for the API service"
  type        = number
  default     = 1024
}

# ── TLS ───────────────────────────────────────────────────────────────────────

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for the ALB HTTPS listener"
  type        = string
  # No default — must be supplied per environment
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
  default     = "ops@scr-platform.com"
}

variable "domain_name" {
  description = "Primary domain name for the platform"
  type        = string
  default     = "scr-platform.com"
}

variable "db_read_replica_instance_class" {
  description = "RDS read replica instance class (production)"
  type        = string
  default     = "db.t4g.medium"
}

variable "celery_critical_cpu" {
  description = "CPU units for critical Celery worker"
  type        = number
  default     = 1024
}

variable "celery_critical_memory" {
  description = "Memory (MiB) for critical Celery worker"
  type        = number
  default     = 2048
}
