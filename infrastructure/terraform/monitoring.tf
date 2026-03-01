# ── CloudWatch Monitoring — Dashboards, Alarms, SNS ──────────────────────────

# ── SNS Topics ────────────────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "scr-production-alerts"
}

resource "aws_sns_topic" "pagerduty" {
  name = "scr-production-pagerduty"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ── CloudWatch Dashboards (production only) ───────────────────────────────────

# 1. Platform Health Dashboard
resource "aws_cloudwatch_dashboard" "platform_health" {
  count          = var.environment == "production" ? 1 : 0
  dashboard_name = "scr-platform-health"

  dashboard_body = jsonencode({
    widgets = [
      # API 5xx error rate
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "API 5xx Error Rate"
          region = var.aws_region
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count",
              "LoadBalancer", aws_lb.main.arn_suffix,
              { stat = "Sum", period = 60, label = "5xx Errors" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # API request rate (2xx)
      {
        type   = "metric"
        x      = 8
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "API Request Rate (2xx)"
          region = var.aws_region
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_2XX_Count",
              "LoadBalancer", aws_lb.main.arn_suffix,
              { stat = "Sum", period = 60, label = "2xx Requests" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # API P99 latency
      {
        type   = "metric"
        x      = 16
        y      = 0
        width  = 8
        height = 6
        properties = {
          title  = "API P99 Latency (ms)"
          region = var.aws_region
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime",
              "LoadBalancer", aws_lb.main.arn_suffix,
              { stat = "p99", period = 60, label = "P99 Latency" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
          yAxis = {
            left = { label = "Seconds", showUnits = false }
          }
        }
      },
      # RDS CPU utilization
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "RDS CPU Utilization"
          region = var.aws_region
          metrics = [
            ["AWS/RDS", "CPUUtilization",
              "DBInstanceIdentifier", module.rds.db_instance_id,
              { stat = "Average", period = 60, label = "RDS CPU %" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # RDS connections
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "RDS Database Connections"
          region = var.aws_region
          metrics = [
            ["AWS/RDS", "DatabaseConnections",
              "DBInstanceIdentifier", module.rds.db_instance_id,
              { stat = "Average", period = 60, label = "Connections" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # Redis CPU and FreeableMemory
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Redis — CPU & Memory"
          region = var.aws_region
          metrics = [
            ["AWS/ElastiCache", "EngineCPUUtilization",
              "CacheClusterId", module.redis.cluster_id,
              { stat = "Average", period = 60, label = "Engine CPU %" }
            ],
            ["AWS/ElastiCache", "FreeableMemory",
              "CacheClusterId", module.redis.cluster_id,
              { stat = "Average", period = 60, label = "Freeable Memory (bytes)" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # ECS CPU per service
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "ECS CPU Utilization per Service"
          region = var.aws_region
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.api.name, { stat = "Average", period = 60, label = "API" }],
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.gateway.name, { stat = "Average", period = 60, label = "AI Gateway" }],
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.web.name, { stat = "Average", period = 60, label = "Web" }],
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_critical.name, { stat = "Average", period = 60, label = "Worker Critical" }],
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_default.name, { stat = "Average", period = 60, label = "Worker Default" }],
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_bulk.name, { stat = "Average", period = 60, label = "Worker Bulk" }],
            ["AWS/ECS", "CPUUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_webhooks.name, { stat = "Average", period = 60, label = "Worker Webhooks" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # ECS Memory per service
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title  = "ECS Memory Utilization per Service"
          region = var.aws_region
          metrics = [
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.api.name, { stat = "Average", period = 60, label = "API" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.gateway.name, { stat = "Average", period = 60, label = "AI Gateway" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.web.name, { stat = "Average", period = 60, label = "Web" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_critical.name, { stat = "Average", period = 60, label = "Worker Critical" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_default.name, { stat = "Average", period = 60, label = "Worker Default" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_bulk.name, { stat = "Average", period = 60, label = "Worker Bulk" }],
            ["AWS/ECS", "MemoryUtilization", "ClusterName", aws_ecs_cluster.main.name, "ServiceName", aws_ecs_service.worker_webhooks.name, { stat = "Average", period = 60, label = "Worker Webhooks" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      }
    ]
  })
}

# 2. AI Operations Dashboard
resource "aws_cloudwatch_dashboard" "ai_ops" {
  count          = var.environment == "production" ? 1 : 0
  dashboard_name = "scr-ai-ops"

  dashboard_body = jsonencode({
    widgets = [
      # AI cost by model (daily sum)
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Daily AI Cost (USD) by Model"
          region = var.aws_region
          metrics = [
            [{ expression = "SEARCH('{scr/ai,model} MetricName=\"cost_usd\"', 'Sum', 86400)", label = "Cost by Model", id = "e1" }]
          ]
          view    = "timeSeries"
          stacked = true
          yAxis = {
            left = { label = "USD", showUnits = false }
          }
        }
      },
      # AI requests by provider
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "AI Requests by Provider"
          region = var.aws_region
          metrics = [
            [{ expression = "SEARCH('{scr/ai,provider} MetricName=\"requests\"', 'Sum', 300)", label = "Requests by Provider", id = "e1" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # AI P95 latency by model
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "AI P95 Latency (ms) by Model"
          region = var.aws_region
          metrics = [
            [{ expression = "SEARCH('{scr/ai,model} MetricName=\"latency_ms\"', 'p95', 300)", label = "P95 Latency by Model", id = "e1" }]
          ]
          view    = "timeSeries"
          stacked = false
          yAxis = {
            left = { label = "Milliseconds", showUnits = false }
          }
        }
      },
      # AI cache hit rate
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 6
        height = 6
        properties = {
          title  = "AI Cache Hit Rate"
          region = var.aws_region
          metrics = [
            ["scr/ai", "cache_hit_rate", { stat = "Average", period = 300, label = "Cache Hit Rate" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # AI fallback rate
      {
        type   = "metric"
        x      = 18
        y      = 6
        width  = 6
        height = 6
        properties = {
          title  = "AI Fallback Rate"
          region = var.aws_region
          metrics = [
            ["scr/ai", "fallback_rate", { stat = "Average", period = 300, label = "Fallback Rate" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # AI budget % used by org
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        properties = {
          title  = "AI Budget % Used by Organisation"
          region = var.aws_region
          metrics = [
            [{ expression = "SEARCH('{scr/ai,org_id} MetricName=\"budget_pct_used\"', 'Maximum', 3600)", label = "Budget % by Org", id = "e1" }]
          ]
          view    = "timeSeries"
          stacked = false
          yAxis = {
            left = { label = "Percent", min = 0, max = 100, showUnits = false }
          }
        }
      }
    ]
  })
}

# 3. Business Metrics Dashboard
resource "aws_cloudwatch_dashboard" "business" {
  count          = var.environment == "production" ? 1 : 0
  dashboard_name = "scr-business"

  dashboard_body = jsonencode({
    widgets = [
      # DAU / MAU
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Active Users (DAU / MAU)"
          region = var.aws_region
          metrics = [
            ["scr/business", "active_users", "period_type", "DAU", { stat = "Maximum", period = 86400, label = "Daily Active Users" }],
            ["scr/business", "active_users", "period_type", "MAU", { stat = "Maximum", period = 86400, label = "Monthly Active Users" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # Projects created
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Projects Created"
          region = var.aws_region
          metrics = [
            ["scr/business", "projects_created", { stat = "Sum", period = 86400, label = "Projects Created (daily)" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # Signal scores computed
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Signal Scores Computed"
          region = var.aws_region
          metrics = [
            ["scr/business", "signal_scores_computed", { stat = "Sum", period = 3600, label = "Signal Scores/hr" }]
          ]
          view    = "timeSeries"
          stacked = false
        }
      },
      # Webhook delivery success rate
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "Webhook Delivery Success Rate"
          region = var.aws_region
          metrics = [
            ["scr/business", "webhook_delivery_success_rate", { stat = "Average", period = 300, label = "Success Rate %" }]
          ]
          view    = "timeSeries"
          stacked = false
          yAxis = {
            left = { label = "Percent", min = 0, max = 100, showUnits = false }
          }
        }
      },
      # QA SLA compliance rate
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6
        properties = {
          title  = "QA SLA Compliance Rate"
          region = var.aws_region
          metrics = [
            ["scr/business", "qa_sla_compliance_rate", { stat = "Average", period = 3600, label = "SLA Compliance %" }]
          ]
          view    = "timeSeries"
          stacked = false
          yAxis = {
            left = { label = "Percent", min = 0, max = 100, showUnits = false }
          }
        }
      }
    ]
  })
}

# ── CloudWatch Alarms (production only) ───────────────────────────────────────

# ── Infrastructure Alarms ─────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "api_5xx_rate" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-api-5xx-rate"
  alarm_description   = "API 5xx error rate exceeds 1% of total requests"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 1

  # Use a math expression to compute the 5xx rate as a percentage
  metric_query {
    id          = "e1"
    expression  = "m2 / m1 * 100"
    label       = "5xx Error Rate %"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "RequestCount"
      dimensions = {
        LoadBalancer = aws_lb.main.arn_suffix
      }
      period = 60
      stat   = "Sum"
    }
  }

  metric_query {
    id = "m2"
    metric {
      namespace   = "AWS/ApplicationELB"
      metric_name = "HTTPCode_Target_5XX_Count"
      dimensions = {
        LoadBalancer = aws_lb.main.arn_suffix
      }
      period = 60
      stat   = "Sum"
    }
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_p99_latency" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-api-p99-latency"
  alarm_description   = "API P99 latency exceeds 2000ms"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 2
  namespace           = "AWS/ApplicationELB"
  metric_name         = "TargetResponseTime"
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  period             = 60
  statistic          = "p99"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-rds-cpu"
  alarm_description   = "RDS CPU utilization exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 80
  namespace           = "AWS/RDS"
  metric_name         = "CPUUtilization"
  dimensions = {
    DBInstanceIdentifier = module.rds.db_instance_id
  }
  period             = 60
  statistic          = "Average"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_replica_lag" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-rds-replica-lag"
  alarm_description   = "RDS read replica lag exceeds 60 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 60
  namespace           = "AWS/RDS"
  metric_name         = "ReplicaLag"
  dimensions = {
    DBInstanceIdentifier = module.rds.db_instance_read_replica_id
  }
  period             = 60
  statistic          = "Average"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-redis-memory"
  alarm_description   = "Redis FreeableMemory is low (less than 15% estimated free)"
  # Alarm when FreeableMemory drops below a low threshold (bytes)
  # Adjust threshold based on node type; for cache.t4g.micro (~512MB) alarm at ~77MB (15%)
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  threshold           = 80000000
  namespace           = "AWS/ElastiCache"
  metric_name         = "FreeableMemory"
  dimensions = {
    CacheClusterId = module.redis.cluster_id
  }
  period             = 60
  statistic          = "Average"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_ecs_cpu" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-api-ecs-cpu"
  alarm_description   = "API ECS service CPU utilization exceeds 85%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 85
  namespace           = "AWS/ECS"
  metric_name         = "CPUUtilization"
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.api.name
  }
  period             = 60
  statistic          = "Average"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ── Celery Queue Depth Alarms ─────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "celery_queue_critical" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-celery-queue-critical-depth"
  alarm_description   = "Celery critical queue depth exceeds 50 — signal scores/doc processing may be backlogged"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 50
  namespace           = "scr/celery"
  metric_name         = "queue_depth"
  dimensions = {
    queue = "critical"
  }
  period             = 60
  statistic          = "Maximum"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.pagerduty.arn]
  ok_actions    = [aws_sns_topic.pagerduty.arn]
}

resource "aws_cloudwatch_metric_alarm" "celery_queue_default" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-celery-queue-default-depth"
  alarm_description   = "Celery default queue depth exceeds 100"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 100
  namespace           = "scr/celery"
  metric_name         = "queue_depth"
  dimensions = {
    queue = "default"
  }
  period             = 60
  statistic          = "Maximum"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "celery_queue_bulk" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-celery-queue-bulk-depth"
  alarm_description   = "Celery bulk queue depth exceeds 200"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 200
  namespace           = "scr/celery"
  metric_name         = "queue_depth"
  dimensions = {
    queue = "bulk"
  }
  period             = 60
  statistic          = "Maximum"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "celery_queue_webhooks" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-celery-queue-webhooks-depth"
  alarm_description   = "Celery webhooks queue depth exceeds 100"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 100
  namespace           = "scr/celery"
  metric_name         = "queue_depth"
  dimensions = {
    queue = "webhooks"
  }
  period             = 60
  statistic          = "Maximum"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "celery_beat_heartbeat" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-celery-beat-heartbeat-missing"
  alarm_description   = "Celery Beat heartbeat missing for more than 10 minutes — scheduler may be down"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  threshold           = 1
  namespace           = "scr/celery"
  metric_name         = "beat_heartbeat"
  period              = 300
  statistic           = "Sum"
  # Missing data treated as breaching — if beat stops publishing we want to alarm
  treat_missing_data = "breaching"

  alarm_actions = [aws_sns_topic.pagerduty.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ── AI Cost Alarms ────────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "ai_daily_cost_total" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-ai-daily-cost-total"
  alarm_description   = "Total daily AI cost exceeds $80"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 80
  namespace           = "scr/ai"
  metric_name         = "cost_usd"
  period              = 86400
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ai_daily_cost_anthropic" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-ai-daily-cost-anthropic"
  alarm_description   = "Daily Anthropic AI cost exceeds $50"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 50
  namespace           = "scr/ai"
  metric_name         = "cost_usd"
  dimensions = {
    provider = "anthropic"
  }
  period             = 86400
  statistic          = "Sum"
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ai_provider_error_rate" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-ai-provider-error-rate"
  alarm_description   = "AI provider error rate exceeds 5%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 5
  namespace           = "scr/ai"
  metric_name         = "error_rate"
  period              = 300
  statistic           = "Average"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ai_fallback_rate" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-ai-fallback-rate"
  alarm_description   = "AI fallback rate exceeds 20% — primary provider may be degraded"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 20
  namespace           = "scr/ai"
  metric_name         = "fallback_rate"
  period              = 300
  statistic           = "Average"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ── Data Integrity Alarms ─────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "backup_task_failure" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-backup-task-failure"
  alarm_description   = "Backup task has failed — data protection at risk"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  namespace           = "scr/tasks"
  metric_name         = "backup_failed"
  period              = 3600
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.pagerduty.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "data_retention_failure" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-data-retention-failure"
  alarm_description   = "Data retention task has failed — compliance risk"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  namespace           = "scr/tasks"
  metric_name         = "retention_failed"
  period              = 3600
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ── Application Alarms ────────────────────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "webhook_delivery_failure" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-webhook-delivery-failure-rate"
  alarm_description   = "Webhook delivery failure rate exceeds 10%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 10
  namespace           = "scr/business"
  metric_name         = "webhook_delivery_failure_rate"
  period              = 300
  statistic           = "Average"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "crm_sync_errors" {
  count               = var.environment == "production" ? 1 : 0
  alarm_name          = "scr-production-crm-sync-errors"
  alarm_description   = "CRM sync errors exceed 5 per hour"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 5
  namespace           = "scr/business"
  metric_name         = "crm_sync_errors"
  period              = 3600
  statistic           = "Sum"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "alerts_sns_topic_arn" {
  description = "ARN of the SNS topic used for production CloudWatch alarm notifications"
  value       = aws_sns_topic.alerts.arn
}
