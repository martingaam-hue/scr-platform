# ── GitHub Actions OIDC Federation ───────────────────────────────────────────
#
# Replaces long-lived AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY secrets with
# short-lived OIDC tokens.  Workflows assume this role using:
#
#   uses: aws-actions/configure-aws-credentials@v4
#   with:
#     role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
#     aws-region: eu-north-1
#
# IMPORTANT: Apply this Terraform change BEFORE switching the workflow files.
# After apply, set AWS_ROLE_ARN in both the "staging" and "production"
# GitHub environment secrets to the role ARN output by `terraform output`.

resource "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # GitHub's OIDC thumbprint — stable; update only when GitHub rotates their cert.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = {
    Name = "github-actions-oidc"
  }
}

resource "aws_iam_role" "github_actions" {
  name        = "scr-github-actions"
  description = "Assumed by GitHub Actions via OIDC for CI/CD to ${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubActionsOIDC"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_actions.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Scope to this repo only — adjust if the repo is ever renamed
            "token.actions.githubusercontent.com:sub" = "repo:martingaam-hue/scr-platform:*"
          }
        }
      }
    ]
  })
}

# ── Permissions needed by the CI/CD workflows ─────────────────────────────────

resource "aws_iam_role_policy" "github_actions_ecr" {
  name = "scr-github-actions-ecr"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRAuth"
        Effect = "Allow"
        Action = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:ListImages",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/scr-*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_actions_ecs" {
  name = "scr-github-actions-ecs"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECSDeployAndRun"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTasks",
          "ecs:DescribeTaskDefinition",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition",
          "ecs:RunTask",
          "ecs:UpdateService",
        ]
        Resource = "*"
      },
      {
        Sid      = "PassRoleToECS"
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/scr-staging-ecs-task",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/scr-staging-ecs-exec",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/scr-production-ecs-task",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/scr-production-ecs-exec",
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_actions_logs" {
  name = "scr-github-actions-logs"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogsRead"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/scr-*"
      }
    ]
  })
}

# ── Output for operators ───────────────────────────────────────────────────────

output "github_actions_role_arn" {
  description = "Set this as AWS_ROLE_ARN in GitHub environment secrets (staging + production)"
  value       = aws_iam_role.github_actions.arn
}
