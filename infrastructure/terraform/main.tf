terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "scr-platform-terraform-state"
    key     = "infrastructure/terraform.tfstate"
    region  = "eu-west-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "scr-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# --- VPC ---
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "scr-${var.environment}"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = var.environment != "production"
}

# --- RDS (PostgreSQL 16) ---
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "scr-${var.environment}"

  engine               = "postgres"
  engine_version       = "16"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100

  db_name  = "scr_platform"
  username = "scr_admin"
  port     = 5432

  vpc_security_group_ids = [module.vpc.default_security_group_id]
  subnet_ids             = module.vpc.private_subnets

  backup_retention_period = var.environment == "production" ? 14 : 7
  deletion_protection     = var.environment == "production"

  db_parameter_group_name      = aws_db_parameter_group.postgres16.name
  multi_az                     = var.environment == "production"
  performance_insights_enabled = var.environment == "production"
  monitoring_interval          = var.environment == "production" ? 60 : 0
  monitoring_role_arn          = var.environment == "production" ? aws_iam_role.rds_monitoring[0].arn : null
}

# --- ElastiCache (Redis 7 — Replication Group) ---
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "scr-${var.environment}"
  description          = "SCR Platform Redis cluster"

  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_clusters   = var.environment == "production" ? 2 : 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [module.vpc.default_security_group_id]

  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  maintenance_window       = "sun:05:00-sun:06:00"
  snapshot_window          = "04:00-05:00"
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "scr-${var.environment}-redis"
  subnet_ids = module.vpc.private_subnets
}

# --- S3 (Document Storage) ---
resource "aws_s3_bucket" "documents" {
  bucket = "scr-${var.environment}-documents"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

# --- RDS Parameter Group ---
resource "aws_db_parameter_group" "postgres16" {
  name   = "scr-${var.environment}-postgres16"
  family = "postgres16"

  parameter {
    name  = "max_connections"
    value = "200"
  }
  parameter {
    name         = "shared_buffers"
    value        = "4294967296" # 4GB in bytes
    apply_method = "pending-reboot"
  }
  parameter {
    name  = "statement_timeout"
    value = "30000" # 30 seconds in ms
  }
  parameter {
    name  = "idle_in_transaction_session_timeout"
    value = "60000" # 60 seconds in ms
  }
  parameter {
    name  = "lock_timeout"
    value = "10000" # 10 seconds in ms
  }
  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log slow queries > 1s
  }
  parameter {
    name         = "log_connections"
    value        = "1"
    apply_method = "pending-reboot"
  }
}

# --- RDS IAM Role for Enhanced Monitoring (production only) ---
resource "aws_iam_role" "rds_monitoring" {
  count = var.environment == "production" ? 1 : 0
  name  = "scr-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.environment == "production" ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# --- RDS Read Replica (production only) ---
resource "aws_db_instance" "read_replica" {
  count = var.environment == "production" ? 1 : 0

  identifier          = "scr-${var.environment}-read"
  replicate_source_db = module.rds.db_instance_id

  instance_class      = var.db_instance_class
  publicly_accessible = false
  skip_final_snapshot = true
  deletion_protection = true

  vpc_security_group_ids  = [module.vpc.default_security_group_id]
  db_parameter_group_name = aws_db_parameter_group.postgres16.name

  performance_insights_enabled = true
  monitoring_interval          = 60
  monitoring_role_arn          = aws_iam_role.rds_monitoring[0].arn

  tags = {
    Name = "scr-${var.environment}-read-replica"
    Role = "read-replica"
  }
}

# --- Additional S3 Buckets ---

# scr-redacted: redacted PDFs (D03)
resource "aws_s3_bucket" "redacted" {
  bucket = "scr-${var.environment}-redacted"
}
resource "aws_s3_bucket_versioning" "redacted" {
  bucket = aws_s3_bucket.redacted.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "redacted" {
  bucket = aws_s3_bucket.redacted.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" } }
}

# scr-exports: generated reports (30-day lifecycle)
resource "aws_s3_bucket" "exports" {
  bucket = "scr-${var.environment}-exports"
}
resource "aws_s3_bucket_lifecycle_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id
  rule {
    id     = "expire-exports"
    status = "Enabled"
    expiration { days = 30 }
    filter { prefix = "" }
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}

# scr-backups: pg_dump backups
resource "aws_s3_bucket" "backups" {
  bucket = "scr-${var.environment}-backups"
}
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    id     = "glacier-after-90d"
    status = "Enabled"
    filter { prefix = "" }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration { days = 365 }
  }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" } }
}

# Documents bucket: Glacier after 1 year
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    id     = "glacier-after-1yr"
    status = "Enabled"
    filter { prefix = "" }
    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }
}

# Block all public access for all buckets
resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_public_access_block" "redacted" {
  bucket                  = aws_s3_bucket.redacted.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_public_access_block" "exports" {
  bucket                  = aws_s3_bucket.exports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_public_access_block" "backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- ECS Task S3 Extended Policy (redacted, exports, backups) ---
resource "aws_iam_role_policy" "ecs_task_s3_extended" {
  name = "scr-${var.environment}-ecs-s3-extended"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.redacted.arn, "${aws_s3_bucket.redacted.arn}/*",
          aws_s3_bucket.exports.arn, "${aws_s3_bucket.exports.arn}/*",
          aws_s3_bucket.backups.arn, "${aws_s3_bucket.backups.arn}/*",
        ]
      }
    ]
  })
}
