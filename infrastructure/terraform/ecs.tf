# ── ECS Fargate — Cluster + Services ─────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "scr-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = var.environment == "production" ? "FARGATE" : "FARGATE_SPOT"
  }
}

# ── IAM ───────────────────────────────────────────────────────────────────────

resource "aws_iam_role" "ecs_task_execution" {
  name = "scr-${var.environment}-ecs-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow pulling secrets from Secrets Manager
resource "aws_iam_role_policy" "ecs_secrets" {
  name = "scr-${var.environment}-ecs-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "ssm:GetParameters"]
      Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:scr/${var.environment}/*"
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "scr-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

# Task role: S3 access for document storage
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "scr-${var.environment}-ecs-s3"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.documents.arn,
        "${aws_s3_bucket.documents.arn}/*"
      ]
    }]
  })
}

# ── Security Groups ───────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name        = "scr-${var.environment}-alb"
  description = "ALB — allow HTTPS from internet"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name        = "scr-${var.environment}-ecs"
  description = "ECS tasks — only from ALB"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8001
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow tasks to talk to each other (API → Gateway)
  ingress {
    from_port = 8000
    to_port   = 8001
    protocol  = "tcp"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── CloudWatch Log Groups ─────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/scr-${var.environment}/api"
  retention_in_days = var.environment == "production" ? 90 : 14
}

resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/scr-${var.environment}/web"
  retention_in_days = var.environment == "production" ? 30 : 7
}

resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/ecs/scr-${var.environment}/ai-gateway"
  retention_in_days = var.environment == "production" ? 90 : 14
}

# ── API Service ───────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "api" {
  family                   = "scr-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.services["scr-api"].repository_url}:${var.environment}-latest"
    essential = true

    portMappings = [{ containerPort = 8000, protocol = "tcp" }]

    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "APP_DEBUG", value = "false" },
    ]

    secrets = [
      { name = "DATABASE_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/DATABASE_URL" },
      { name = "REDIS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/REDIS_URL" },
      { name = "SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/SECRET_KEY" },
      { name = "CLERK_SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/CLERK_SECRET_KEY" },
      { name = "CLERK_WEBHOOK_SECRET", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/CLERK_WEBHOOK_SECRET" },
      { name = "CLERK_ISSUER_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/CLERK_ISSUER_URL" },
      { name = "AI_GATEWAY_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AI_GATEWAY_API_KEY" },
      { name = "AWS_ACCESS_KEY_ID", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AWS_ACCESS_KEY_ID" },
      { name = "AWS_SECRET_ACCESS_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AWS_SECRET_ACCESS_KEY" },
    ]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 15
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "scr-api-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.environment == "production" ? 2 : 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.https]

  lifecycle {
    # Prevent Terraform from overriding image tags set by CI/CD
    ignore_changes = [task_definition]
  }
}

# ── AI Gateway Service ────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "gateway" {
  family                   = "scr-ai-gateway-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "ai-gateway"
    image     = "${aws_ecr_repository.services["scr-ai-gateway"].repository_url}:${var.environment}-latest"
    essential = true

    portMappings = [{ containerPort = 8001, protocol = "tcp" }]

    environment = [
      { name = "APP_ENV", value = var.environment },
    ]

    secrets = [
      { name = "ANTHROPIC_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/ANTHROPIC_API_KEY" },
      { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/OPENAI_API_KEY" },
      { name = "AI_GATEWAY_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AI_GATEWAY_API_KEY" },
      { name = "REDIS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/REDIS_URL" },
    ]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 10
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.gateway.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "gateway"
      }
    }
  }])
}

resource "aws_ecs_service" "gateway" {
  name            = "scr-ai-gateway-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.gateway.arn
  desired_count   = 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── Web Service ───────────────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "web" {
  family                   = "scr-web-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "web"
    image     = "${aws_ecr_repository.services["scr-web"].repository_url}:${var.environment}-latest"
    essential = true

    portMappings = [{ containerPort = 3000, protocol = "tcp" }]

    environment = [
      { name = "NODE_ENV", value = "production" },
    ]

    secrets = [
      { name = "CLERK_SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/CLERK_SECRET_KEY" },
    ]

    healthCheck = {
      command     = ["CMD-SHELL", "wget -qO- http://localhost:3000/ || exit 1"]
      interval    = 30
      timeout     = 10
      retries     = 3
      startPeriod = 20
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.web.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "web"
      }
    }
  }])
}

resource "aws_ecs_service" "web" {
  name            = "scr-web-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.environment == "production" ? 2 : 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.https]

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── ALB ───────────────────────────────────────────────────────────────────────

resource "aws_lb" "main" {
  name               = "scr-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnets

  enable_deletion_protection = var.environment == "production"

  access_logs {
    bucket  = aws_s3_bucket.documents.id
    prefix  = "alb-logs"
    enabled = true
  }
}

resource "aws_lb_target_group" "api" {
  name        = "scr-${var.environment}-api"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
}

resource "aws_lb_target_group" "web" {
  name        = "scr-${var.environment}-web"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    matcher             = "200,307"
  }
}

# Redirect HTTP → HTTPS
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.alb.certificate_arn

  # Default: route to web
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# Route /api/* and /auth/* to the FastAPI backend
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/auth/*", "/webhooks/*", "/health", "/docs", "/redoc"]
    }
  }
}

# ── Auto Scaling ──────────────────────────────────────────────────────────────

resource "aws_appautoscaling_target" "api" {
  count              = var.environment == "production" ? 1 : 0
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  count              = var.environment == "production" ? 1 : 0
  name               = "scr-${var.environment}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api[0].resource_id
  scalable_dimension = aws_appautoscaling_target.api[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.api[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# ── Celery Worker CloudWatch Log Groups ───────────────────────────────────────

resource "aws_cloudwatch_log_group" "celery_beat" {
  name              = "/ecs/scr-${var.environment}/celery-beat"
  retention_in_days = var.environment == "production" ? 90 : 14
}

resource "aws_cloudwatch_log_group" "worker_critical" {
  name              = "/ecs/scr-${var.environment}/worker-critical"
  retention_in_days = var.environment == "production" ? 90 : 14
}

resource "aws_cloudwatch_log_group" "worker_default" {
  name              = "/ecs/scr-${var.environment}/worker-default"
  retention_in_days = var.environment == "production" ? 90 : 14
}

resource "aws_cloudwatch_log_group" "worker_bulk" {
  name              = "/ecs/scr-${var.environment}/worker-bulk"
  retention_in_days = var.environment == "production" ? 90 : 14
}

resource "aws_cloudwatch_log_group" "worker_webhooks" {
  name              = "/ecs/scr-${var.environment}/worker-webhooks"
  retention_in_days = var.environment == "production" ? 90 : 14
}

# ── Celery Shared Secrets Local ───────────────────────────────────────────────
# Reusable secrets list for all Celery task definitions

locals {
  celery_secrets = [
    { name = "DATABASE_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/DATABASE_URL" },
    { name = "DATABASE_URL_READ_REPLICA", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/DATABASE_URL_READ_REPLICA" },
    { name = "REDIS_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/REDIS_URL" },
    { name = "SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/SECRET_KEY" },
    { name = "CLERK_SECRET_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/CLERK_SECRET_KEY" },
    { name = "AI_GATEWAY_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AI_GATEWAY_URL" },
    { name = "AI_GATEWAY_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AI_GATEWAY_API_KEY" },
    { name = "AWS_ACCESS_KEY_ID", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AWS_ACCESS_KEY_ID" },
    { name = "AWS_SECRET_ACCESS_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/AWS_SECRET_ACCESS_KEY" },
    { name = "SENTRY_DSN", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/SENTRY_DSN" },
    { name = "ANTHROPIC_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/ANTHROPIC_API_KEY" },
    { name = "OPENAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/OPENAI_API_KEY" },
    { name = "GOOGLE_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/GOOGLE_API_KEY" },
    { name = "XAI_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/XAI_API_KEY" },
    { name = "DEEPSEEK_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/DEEPSEEK_API_KEY" },
    { name = "RESEND_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/RESEND_API_KEY" },
    { name = "HUBSPOT_CLIENT_ID", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/HUBSPOT_CLIENT_ID" },
    { name = "HUBSPOT_CLIENT_SECRET", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/HUBSPOT_CLIENT_SECRET" },
    { name = "SALESFORCE_CONSUMER_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/SALESFORCE_CONSUMER_KEY" },
    { name = "SALESFORCE_CONSUMER_SECRET", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/SALESFORCE_CONSUMER_SECRET" },
    { name = "PINECONE_API_KEY", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/PINECONE_API_KEY" },
    { name = "CELERY_BROKER_URL", valueFrom = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:scr/${var.environment}/CELERY_BROKER_URL" },
  ]
}

# ── Celery Beat Task Definition ───────────────────────────────────────────────

resource "aws_ecs_task_definition" "celery_beat" {
  family                   = "scr-celery-beat-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "celery-beat"
    image     = "${aws_ecr_repository.services["scr-api"].repository_url}:${var.environment}-latest"
    essential = true

    command = ["celery", "-A", "app.worker", "beat", "--loglevel=info", "--scheduler=celery.beat:PersistentScheduler"]

    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "APP_DEBUG", value = "false" },
    ]

    secrets = local.celery_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.celery_beat.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "celery-beat"
      }
    }
  }])
}

resource "aws_ecs_service" "celery_beat" {
  name            = "scr-celery-beat-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.celery_beat.arn
  # Beat must always be a single instance to avoid duplicate scheduled tasks
  desired_count = 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── Worker Critical Task Definition ──────────────────────────────────────────

resource "aws_ecs_task_definition" "worker_critical" {
  family                   = "scr-worker-critical-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker-critical"
    image     = "${aws_ecr_repository.services["scr-api"].repository_url}:${var.environment}-latest"
    essential = true

    command = ["celery", "-A", "app.worker", "worker", "--loglevel=info", "-Q", "critical", "--concurrency=4", "--max-tasks-per-child=100"]

    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "APP_DEBUG", value = "false" },
    ]

    secrets = local.celery_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker_critical.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "worker-critical"
      }
    }
  }])
}

resource "aws_ecs_service" "worker_critical" {
  name            = "scr-worker-critical-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker_critical.arn
  desired_count   = var.environment == "production" ? 2 : 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── Worker Default Task Definition ────────────────────────────────────────────

resource "aws_ecs_task_definition" "worker_default" {
  family                   = "scr-worker-default-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker-default"
    image     = "${aws_ecr_repository.services["scr-api"].repository_url}:${var.environment}-latest"
    essential = true

    command = ["celery", "-A", "app.worker", "worker", "--loglevel=info", "-Q", "default,retention", "--concurrency=8", "--max-tasks-per-child=200"]

    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "APP_DEBUG", value = "false" },
    ]

    secrets = local.celery_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker_default.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "worker-default"
      }
    }
  }])
}

resource "aws_ecs_service" "worker_default" {
  name            = "scr-worker-default-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker_default.arn
  desired_count   = var.environment == "production" ? 2 : 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── Worker Bulk Task Definition ───────────────────────────────────────────────

resource "aws_ecs_task_definition" "worker_bulk" {
  family                   = "scr-worker-bulk-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker-bulk"
    image     = "${aws_ecr_repository.services["scr-api"].repository_url}:${var.environment}-latest"
    essential = true

    command = ["celery", "-A", "app.worker", "worker", "--loglevel=info", "-Q", "bulk", "--concurrency=2", "--max-tasks-per-child=50"]

    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "APP_DEBUG", value = "false" },
    ]

    secrets = local.celery_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker_bulk.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "worker-bulk"
      }
    }
  }])
}

resource "aws_ecs_service" "worker_bulk" {
  name            = "scr-worker-bulk-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker_bulk.arn
  desired_count   = 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── Worker Webhooks Task Definition ───────────────────────────────────────────

resource "aws_ecs_task_definition" "worker_webhooks" {
  family                   = "scr-worker-webhooks-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker-webhooks"
    image     = "${aws_ecr_repository.services["scr-api"].repository_url}:${var.environment}-latest"
    essential = true

    command = ["celery", "-A", "app.worker", "worker", "--loglevel=info", "-Q", "webhooks", "--concurrency=6", "--max-tasks-per-child=500"]

    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "APP_DEBUG", value = "false" },
    ]

    secrets = local.celery_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.worker_webhooks.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "worker-webhooks"
      }
    }
  }])
}

resource "aws_ecs_service" "worker_webhooks" {
  name            = "scr-worker-webhooks-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker_webhooks.arn
  desired_count   = var.environment == "production" ? 2 : 1

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ── Celery Worker Auto Scaling (production only) ───────────────────────────────

# worker-critical: min=2 max=8, CPU target 70%
resource "aws_appautoscaling_target" "worker_critical" {
  count              = var.environment == "production" ? 1 : 0
  max_capacity       = 8
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker_critical.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "worker_critical_cpu" {
  count              = var.environment == "production" ? 1 : 0
  name               = "scr-${var.environment}-worker-critical-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_critical[0].resource_id
  scalable_dimension = aws_appautoscaling_target.worker_critical[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_critical[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# worker-default: min=2 max=12, CPU target 70%
resource "aws_appautoscaling_target" "worker_default" {
  count              = var.environment == "production" ? 1 : 0
  max_capacity       = 12
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker_default.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "worker_default_cpu" {
  count              = var.environment == "production" ? 1 : 0
  name               = "scr-${var.environment}-worker-default-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker_default[0].resource_id
  scalable_dimension = aws_appautoscaling_target.worker_default[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker_default[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
