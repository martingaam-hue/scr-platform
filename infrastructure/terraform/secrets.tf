# ── Secrets Manager — All application secrets ─────────────────────────────────
# Secret values must be populated manually (AWS Console) or via CI/CD pipeline
# after initial Terraform apply creates the secret ARNs.
#
# Pattern: aws secretsmanager put-secret-value \
#   --secret-id "scr/${var.environment}/SECRET_NAME" \
#   --secret-string "actual-value-here"

locals {
  secret_names = [
    # Core
    "DATABASE_URL",
    "DATABASE_URL_READ_REPLICA",
    "DATABASE_URL_SYNC",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "SECRET_KEY",
    # Auth
    "CLERK_SECRET_KEY",
    "CLERK_WEBHOOK_SECRET",
    "CLERK_ISSUER_URL",
    # Storage
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    # LLM Providers (5)
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "XAI_API_KEY",
    "DEEPSEEK_API_KEY",
    # AI Gateway
    "AI_GATEWAY_API_KEY",
    "AI_GATEWAY_API_KEY_PREVIOUS",
    # CRM
    "HUBSPOT_CLIENT_ID",
    "HUBSPOT_CLIENT_SECRET",
    "SALESFORCE_CONSUMER_KEY",
    "SALESFORCE_CONSUMER_SECRET",
    # Vector DB
    "PINECONE_API_KEY",
    # Email
    "RESEND_API_KEY",
    # Monitoring
    "SENTRY_DSN",
    # Market Data
    "FRED_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    # Flower
    "FLOWER_USER",
    "FLOWER_PASSWORD",
  ]
}

resource "aws_secretsmanager_secret" "app_secrets" {
  for_each = toset(local.secret_names)

  name                    = "scr/${var.environment}/${each.key}"
  description             = "SCR Platform ${var.environment} — ${each.key}"
  recovery_window_in_days = var.environment == "production" ? 30 : 7

  tags = {
    SecretType = "application"
  }
}

# IAM policy document for reading all app secrets
data "aws_iam_policy_document" "secrets_access" {
  statement {
    effect  = "Allow"
    actions = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = [for s in aws_secretsmanager_secret.app_secrets : s.arn]
  }
}

resource "aws_iam_policy" "secrets_access" {
  name        = "scr-${var.environment}-secrets-access"
  description = "Read SCR Platform ${var.environment} secrets from Secrets Manager"
  policy      = data.aws_iam_policy_document.secrets_access.json
}

# Attach to ECS task execution role (so containers can pull secrets)
resource "aws_iam_role_policy_attachment" "ecs_secrets_policy" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = aws_iam_policy.secrets_access.arn
}

output "secret_arns" {
  value       = { for k, v in aws_secretsmanager_secret.app_secrets : k => v.arn }
  description = "ARNs of all Secrets Manager secrets. Populate values after first apply."
  sensitive   = true
}
