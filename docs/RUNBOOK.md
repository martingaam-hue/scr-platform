# On-Call Operations Runbook — SCR Platform v1.0.0

This runbook is for engineers responding to incidents in the SCR Platform production environment. It covers common failure modes, step-by-step diagnosis procedures, and remediation actions.

---

## 1. Quick Reference

| Resource | URL / Command |
|----------|---------------|
| API Health | `GET https://api.scr-platform.com/health` |
| System Health (admin) | `GET https://api.scr-platform.com/admin/system-health` |
| AI Cost Overview (admin) | `GET https://api.scr-platform.com/v1/admin/ai-budget-overview` |
| Sentry | https://scr-platform.sentry.io |
| CloudWatch Dashboards | https://eu-west-1.console.aws.amazon.com/cloudwatch/home (see below) |
| Celery Flower | Internal VPN only — port 5555 on the Celery worker ECS task private IP |
| AWS Console | https://console.aws.amazon.com |
| Status Page | https://status.scr-platform.com |

### CloudWatch Dashboard URLs

| Dashboard | Purpose |
|-----------|---------|
| `scr-production-overview` | ECS CPU/memory, ALB request rate, 5xx rate |
| `scr-production-database` | RDS connections, replication lag, IOPS, disk |
| `scr-production-ai` | AI Gateway token usage, latency, cost by model |
| `scr-production-celery` | Queue depths, task success/failure rates |
| `scr-production-errors` | Structured error counts by module and endpoint |

### Key AWS Resources (Production)

| Resource | Identifier |
|----------|-----------|
| ECS Cluster | `scr-production` |
| API Service | `scr-api-production` |
| Web Service | `scr-web-production` |
| AI Gateway Service | `scr-ai-gateway-production` |
| Celery Worker Services | `scr-celery-default-production`, `scr-celery-bulk-production`, etc. |
| RDS Instance | `scr-production-postgres` |
| ElastiCache Cluster | `scr-production-redis` |
| S3 Documents Bucket | `scr-production-documents` |
| S3 Backups Bucket | `scr-production-backups` |
| ALB | `scr-production-alb` |

---

## 2. Incident Severity Levels

| Severity | Definition | Response Time | Notification |
|----------|-----------|--------------|--------------|
| **P0** | Platform down, data loss, security breach | 15 minutes | Page on-call + manager + CTO |
| **P1** | Major feature unavailable, >10% users affected, payment processing failure | 30 minutes | Page on-call + manager |
| **P2** | Degraded performance, non-critical feature down, elevated error rates | 2 hours | Slack alert to on-call |
| **P3** | Minor bugs, cosmetic issues, single-user impact | Next business day | Ticket only |

### Incident Declaration Process

1. Acknowledge the alert in PagerDuty (or Slack).
2. Post in `#incidents` Slack channel: severity, brief description, who is investigating.
3. Create an incident thread for all updates.
4. If P0/P1: update status page at https://status.scr-platform.com within 30 minutes.
5. Resolve and write a post-mortem within 48 hours for P0/P1 incidents.

---

## 3. Common Incidents and Runbooks

---

### 3a. API Down / High 5xx Rate

**Symptoms:** ALB health checks failing, `GET /health` returns non-200, Sentry spike in 5xx errors, users reporting "Service Unavailable".

**Diagnosis steps:**

```bash
# 1. Check ECS service health
aws ecs describe-services \
  --cluster scr-production \
  --services scr-api-production \
  --query 'services[0].{running:runningCount,desired:desiredCount,pending:pendingCount}'

# 2. Check recent ECS events (look for task launch failures)
aws ecs describe-services \
  --cluster scr-production \
  --services scr-api-production \
  --query 'services[0].events[:10]'

# 3. Check CloudWatch API error logs
aws logs filter-log-events \
  --log-group-name /ecs/scr-api-production \
  --start-time $(date -d '30 minutes ago' +%s000) \
  --filter-pattern "ERROR"

# 4. Check ALB target group health
aws elbv2 describe-target-health \
  --target-group-arn <API_TARGET_GROUP_ARN>

# 5. Check RDS connectivity (from within VPC — use bastion or ECS exec)
aws ecs execute-command \
  --cluster scr-production \
  --task <TASK_ARN> \
  --container api \
  --interactive \
  --command "python -c \"from app.core.database import engine; print('DB OK')\""
```

**Common causes and fixes:**

| Cause | Fix |
|-------|-----|
| Task crash loop (OOM, startup error) | Check CloudWatch Logs for the specific error; may need image rollback |
| RDS unreachable | Check RDS status and security group rules |
| Secrets Manager unreachable | Check VPC endpoint or NAT gateway |
| Bad deployment (new code crashing) | Roll back to previous task definition |
| Alembic migration left DB in bad state | Run `alembic downgrade -1` via one-off task |

**Force new deployment (rolling restart):**

```bash
aws ecs update-service \
  --cluster scr-production \
  --service scr-api-production \
  --force-new-deployment
```

**Rollback to previous task definition:**

```bash
# List recent task definition revisions
aws ecs list-task-definitions \
  --family-prefix scr-api-production \
  --sort DESC \
  --query 'taskDefinitionArns[:5]'

# Update service to use previous revision
aws ecs update-service \
  --cluster scr-production \
  --service scr-api-production \
  --task-definition scr-api-production:<PREVIOUS_REVISION>
```

---

### 3b. Database Issues

#### High Connection Count

**Symptoms:** `FATAL: remaining connection slots are reserved`, slow queries, connection timeout errors.

```sql
-- Check current connections
SELECT count(*), state, wait_event_type, wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event
ORDER BY count DESC;

-- Kill idle connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < now() - interval '10 minutes'
  AND pid <> pg_backend_pid();
```

The API uses SQLAlchemy async connection pool. Default pool size is configured via `DATABASE_POOL_SIZE` env var (default: 10 per process). With 4 uvicorn workers: 40 connections per ECS task.

If connection count is legitimately exhausted: reduce `--workers` count or add `pgbouncer` sidecar (not currently deployed).

#### Replication Lag > 60 Seconds

**Symptoms:** CloudWatch `ReplicaLag` alarm firing. Read-heavy analytics queries returning stale data.

```bash
# Check replica lag via AWS CLI
aws rds describe-db-instances \
  --db-instance-identifier scr-production-postgres-replica \
  --query 'DBInstances[0].{ReplicaLag:StatusInfos}'

# Check from psql on replica
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

**Fix:** Usually resolves on its own. If sustained > 5 minutes:
- Check if a large write transaction is in progress on primary
- Check replica instance CPU/IO (may need to scale up)
- If replica is permanently behind: failover analytics traffic to primary temporarily

#### Slow Queries

```sql
-- Find queries running > 5 seconds
SELECT pid, now() - query_start AS duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
  AND query_start < now() - interval '5 seconds'
ORDER BY duration DESC;

-- Top queries by total time (requires pg_stat_statements)
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Kill a specific query
SELECT pg_cancel_backend(<pid>);     -- graceful
SELECT pg_terminate_backend(<pid>);  -- force
```

#### Disk Full

RDS has storage auto-scaling enabled (threshold: 10% free). If auto-scaling is not keeping up:

```bash
# Check free storage via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=scr-production-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average

# Manually increase storage (no downtime for Multi-AZ)
aws rds modify-db-instance \
  --db-instance-identifier scr-production-postgres \
  --allocated-storage <NEW_SIZE_GB> \
  --apply-immediately
```

Emergency: run data retention cleanup ahead of schedule (see section 3f).

#### Migration Failure

If `alembic upgrade head` exits non-zero during deployment:

```bash
# 1. Check current migration state
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","current"]}]}'

# 2. Roll back one step
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","downgrade","-1"]}]}'

# 3. If schema is corrupted: restore from pre-migration RDS snapshot (see DISASTER_RECOVERY.md)
```

Always take an RDS snapshot before running migrations against production (this is automated in the CD pipeline, but verify it completed).

---

### 3c. AI Provider Outage

**Symptoms:** AI features returning 503 or empty responses, Sentry errors from AI Gateway, `ai_task_logs` table showing `FAILED` status.

**Check provider status pages:**
- Anthropic: https://status.anthropic.com
- OpenAI: https://status.openai.com

**Diagnosis:**

```bash
# Check AI Gateway logs for provider errors
aws logs filter-log-events \
  --log-group-name /ecs/scr-ai-gateway-production \
  --start-time $(date -d '15 minutes ago' +%s000) \
  --filter-pattern "provider_error OR litellm OR fallback"

# Test AI Gateway health directly
curl https://ai-gateway.internal.scr-platform.com/health
```

**Behavior during outage:**

The AI Gateway uses `litellm` with configured fallback models. If the primary model (Claude Sonnet 4) is unavailable, it auto-routes to the configured fallback. Check `services/ai-gateway/app/services/llm_router.py` for the current fallback configuration.

If all providers are unavailable:
- Signal Score calculations will queue in Celery and retry
- Ralph AI responses will return a graceful error message to users
- Document analysis will fail and surface an error in the UI
- Cached AI results (`analysis_extractions` table) will still be served

**Monitor for cost spikes:** If fallback routes to GPT-4o instead of Claude Haiku, token costs may increase 10-50x for the same task. Monitor `GET /admin/ai-costs` endpoint and set a CloudWatch alarm on the `ai_cost_usd` metric if cost per hour exceeds threshold.

**Recovery:** Once the provider is back, no manual action needed. Queued Celery tasks will process automatically.

---

### 3d. Celery Queue Backlog

**Symptoms:** Long delays on async operations (score calculation, report generation, document processing), Flower UI shows large queue depths, users reporting "still processing" after extended periods.

**Check queue depths:**

```bash
# Via Celery inspect (from inside a worker container)
aws ecs execute-command \
  --cluster scr-production \
  --task <WORKER_TASK_ARN> \
  --container celery-worker \
  --interactive \
  --command "celery -A app.worker inspect active_queues"

# Via Redis CLI (queue names are Celery queue keys)
redis-cli -h <REDIS_HOST> llen celery          # default queue
redis-cli -h <REDIS_HOST> llen critical        # critical queue
redis-cli -h <REDIS_HOST> llen bulk            # bulk queue
redis-cli -h <REDIS_HOST> llen webhooks        # webhook queue
redis-cli -h <REDIS_HOST> llen retention       # retention queue
```

**Queue priority (highest to lowest):**

| Queue | Workers | Purpose |
|-------|---------|---------|
| `critical` | Dedicated | Score calculation for active user sessions |
| `webhooks` | Dedicated | Webhook delivery (SLA-sensitive) |
| `default` | General | Most background tasks |
| `bulk` | Dedicated | Report generation, ZIP downloads |
| `retention` | Celery Beat | Data retention, archival |

**Scale up workers:**

```bash
# Scale up the default worker service
aws ecs update-service \
  --cluster scr-production \
  --service scr-celery-default-production \
  --desired-count 4  # up from 2

# Scale up bulk worker for report backlog
aws ecs update-service \
  --cluster scr-production \
  --service scr-celery-bulk-production \
  --desired-count 3
```

**Important:** `task_acks_late=True` is set globally. Tasks are only acknowledged after successful completion, so crashed workers will automatically re-queue their in-progress tasks. Do not manually re-enqueue tasks unless a task has been stuck in `STARTED` state for more than its expected max runtime.

**Monitor via Flower UI:** Access via SSH tunnel through bastion host on port 5555.

---

### 3e. AI Budget Exceeded

**Symptoms:** Users receiving "AI budget exceeded" errors, certain AI features disabled for an organisation.

**Check budget status:**

```bash
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  https://api.scr-platform.com/v1/admin/ai-budget-overview
```

**Per-org budget check:**

```sql
-- Find orgs near or at budget limit
SELECT
  o.id,
  o.name,
  o.subscription_tier,
  o.ai_monthly_budget,
  SUM(atl.cost_usd) AS month_spend_usd,
  (SUM(atl.cost_usd) / NULLIF(o.ai_monthly_budget, 0)) * 100 AS pct_used
FROM organizations o
LEFT JOIN ai_task_logs atl ON atl.org_id = o.id
  AND atl.created_at >= date_trunc('month', now())
GROUP BY o.id, o.name, o.subscription_tier, o.ai_monthly_budget
HAVING SUM(atl.cost_usd) > (o.ai_monthly_budget * 0.9)
ORDER BY pct_used DESC;
```

**Emergency budget increase (approved by account manager):**

```sql
-- Increase monthly budget for a specific org
UPDATE organizations
SET ai_monthly_budget = <NEW_BUDGET_USD>
WHERE id = '<ORG_UUID>';
```

**Review expensive model usage:** Check `apps/api/app/services/ai_costs.py` for the `MODEL_COSTS` dict. Verify that LiteLLM fallback routing is not accidentally routing cheap tasks to expensive models. Monitor the `model_used` column in `ai_task_logs`.

**Tier default budgets** are defined in the AI Gateway configuration. Contact a platform engineer if tier defaults need adjustment — this requires a code change and deployment.

---

### 3f. Data Retention Issues

**Symptoms:** Tables growing unboundedly, disk usage increasing unexpectedly, `data_retention_cleanup` task not appearing as recently succeeded in Flower.

**Check last run:**

```sql
-- Check the last retention run (logged to ai_task_logs)
SELECT created_at, status, output_data
FROM ai_task_logs
WHERE agent_type = 'DATA_RETENTION'
ORDER BY created_at DESC
LIMIT 5;
```

**Retention policies** (defined in `apps/api/app/tasks/data_retention.py`):

| Table | Retention | Behaviour |
|-------|-----------|-----------|
| `audit_logs` | 365 days | Archive (log candidates, do not delete) |
| `document_access_logs` | 365 days | Archive |
| `ai_task_logs` | 90 days | Archive |
| `digest_logs` | 90 days | Delete in 10,000-row batches |
| `usage_events` | 180 days | Delete in 10,000-row batches |
| `webhook_deliveries` | 30 days (delivered) | Delete in 10,000-row batches |

**Runs daily at 04:00 UTC** via Celery Beat.

**If stuck:** Check for long-running transactions blocking the DELETE:

```sql
SELECT pid, now() - xact_start AS duration, state, query
FROM pg_stat_activity
WHERE xact_start < now() - interval '5 minutes'
  AND state != 'idle'
ORDER BY duration DESC;
```

**Manual trigger:**

```bash
aws ecs execute-command \
  --cluster scr-production \
  --task <WORKER_TASK_ARN> \
  --container celery-worker \
  --interactive \
  --command "celery -A app.worker call data_retention_cleanup"
```

---

### 3g. Webhook Delivery Failures

**Symptoms:** Customers reporting they are not receiving webhook events, `webhook_deliveries` table showing `failed` status, Flower showing `deliver_webhook` tasks failing.

**Diagnosis:**

```sql
-- Check recent webhook failures for a specific org
SELECT
  wd.id,
  wd.event_type,
  wd.status,
  wd.attempts,
  wd.response_status_code,
  wd.error_message,
  wd.created_at
FROM webhook_deliveries wd
WHERE wd.org_id = '<ORG_UUID>'
  AND wd.created_at > now() - interval '24 hours'
ORDER BY wd.created_at DESC
LIMIT 50;

-- Check if subscription is auto-disabled (10 consecutive failures)
SELECT id, url, is_active, failure_count, disabled_reason
FROM webhook_subscriptions
WHERE org_id = '<ORG_UUID>';
```

**Re-enable a disabled subscription:**

```bash
curl -X PUT \
  -H "Authorization: Bearer <ADMIN_OR_USER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}' \
  https://api.scr-platform.com/v1/webhooks/<WEBHOOK_ID>
```

**Common failure reasons:**

| Cause | Diagnosis | Fix |
|-------|-----------|-----|
| Target URL unreachable from VPC | `error_message` contains connection refused/timeout | Customer must update their firewall to allow NAT gateway IPs |
| SSL certificate error on target | `error_message` contains SSL | Customer's certificate is invalid/expired |
| HTTP 4xx from target | `response_status_code` in 400–499 | Customer must fix their endpoint logic; review payload format |
| HTTP 5xx from target | `response_status_code` in 500–599 | Customer's server is down; will auto-retry |
| HMAC signature rejected | Customer says signature doesn't match | Verify customer is using the correct secret from `webhook_subscriptions.secret` |

**Retry policy:** Deliveries retry with exponential backoff (1m, 5m, 30m, 2h, 8h). After 10 consecutive failures, the subscription is auto-disabled with reason stored in `disabled_reason`.

---

### 3h. CRM Sync Errors

**Symptoms:** Users reporting HubSpot or Salesforce data not syncing, `crm_sync_logs` showing errors.

**Diagnosis:**

```sql
-- Check recent CRM sync failures
SELECT
  csl.id,
  csl.provider,
  csl.direction,
  csl.status,
  csl.error_message,
  csl.created_at
FROM crm_sync_logs csl
WHERE csl.org_id = '<ORG_UUID>'
  AND csl.created_at > now() - interval '24 hours'
ORDER BY csl.created_at DESC
LIMIT 20;
```

**Common causes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `OAuth token expired` or `401 Unauthorized` | Refresh token has expired or been revoked | User must re-authenticate via Settings → Integrations → HubSpot/Salesforce |
| `429 Too Many Requests` (HubSpot) | HubSpot rate limit: 100 req/10s | Celery task backs off automatically; check if org is using excessive sync frequency |
| `INVALID_FIELD` (Salesforce) | Custom field mapping references a field that doesn't exist in the org's Salesforce instance | User must verify custom field names in CRM module settings |
| `INSUFFICIENT_ACCESS_RIGHTS` (Salesforce) | Connected app OAuth user lacks permission on the object | Salesforce admin must grant permission |

**Check CRM connector keys:**

```sql
-- Verify connector credentials exist (encrypted)
SELECT id, provider, is_active, last_synced_at, created_at
FROM crm_connections
WHERE org_id = '<ORG_UUID>';
```

Connector OAuth tokens are encrypted at rest using Fernet (`apps/api/app/services/encryption.py`). Decryption failures mean the `ENCRYPTION_KEY` env var has changed — escalate to a platform engineer.

---

### 3i. White-Label Domain Issues

**Symptoms:** A partner's custom domain returning errors or certificate warnings.

**Diagnosis checklist:**

```bash
# 1. Verify DNS CNAME record points to custom.scr-platform.com
dig CNAME <CUSTOMER_DOMAIN>

# 2. Test routing with Host header
curl -v -H "Host: <CUSTOMER_DOMAIN>" https://custom.scr-platform.com/health

# 3. Check ACM certificate status
aws acm describe-certificate \
  --certificate-arn <CERT_ARN> \
  --query 'Certificate.{Status:Status,DomainName:DomainName,ValidationRecords:DomainValidationOptions}'

# 4. Check CloudFront alternate domains
aws cloudfront get-distribution \
  --id <CLOUDFRONT_DIST_ID> \
  --query 'Distribution.DistributionConfig.Aliases'
```

**Required setup for a custom domain:**

1. Customer adds CNAME: `<their-domain>` → `custom.scr-platform.com`
2. Platform admin requests ACM certificate for `<their-domain>` in `us-east-1` (required for CloudFront)
3. Customer adds ACM DNS validation CNAME to their DNS (Route53 or external)
4. ACM certificate issues (5–30 minutes)
5. Platform admin adds alternate domain to CloudFront distribution
6. Platform admin updates `custom_domains` table with org mapping

```sql
-- Check custom domain record
SELECT org_id, domain, is_active, ssl_status, created_at
FROM custom_domains
WHERE domain = '<CUSTOMER_DOMAIN>';
```

**CAA records:** If ACM renewal fails, check that the customer's DNS does not have CAA records that exclude Amazon. Required: `0 issue "amazon.com"` or no CAA records at all.

---

### 3j. Backup Failure

**Symptoms:** `backup_database` Celery task showing `FAILED` in Flower, no new objects in `scr-production-backups` S3 bucket with today's timestamp.

**Check last successful backup:**

```bash
aws s3 ls s3://scr-production-backups/pg_dump/ --recursive \
  | sort | tail -5
```

**Check backup task logs:**

```bash
aws logs filter-log-events \
  --log-group-name /ecs/scr-celery-default-production \
  --start-time $(date -d '25 hours ago' +%s000) \
  --filter-pattern "backup"
```

**Trigger manual backup:**

```bash
aws ecs execute-command \
  --cluster scr-production \
  --task <WORKER_TASK_ARN> \
  --container celery-worker \
  --interactive \
  --command "python -c \"from app.tasks.backup import backup_database_task; backup_database_task.apply()\""
```

**Common failures:**

| Cause | Fix |
|-------|-----|
| S3 bucket permissions | Verify ECS task role has `s3:PutObject` on `scr-production-backups/*` |
| `pg_dump` not in PATH | Verify Docker image includes `postgresql-client` |
| RDS `DATABASE_URL_SYNC` not reachable | Check VPC routing from worker to RDS |
| Disk space on worker insufficient | `pg_dump` streams directly to S3 via pipe — should not require local disk |

For restore procedures, see [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).

---

### 3k. Certificate Expiry Warning

**Symptoms:** CloudWatch or ACM alert about certificate expiring within 30 days.

**Background:** ACM certificates managed with Route53 DNS validation auto-renew automatically approximately 60 days before expiry. Manual action is only required if renewal fails.

**Check renewal status:**

```bash
aws acm describe-certificate \
  --certificate-arn <CERT_ARN> \
  --query 'Certificate.{Status:Status,RenewalStatus:RenewalSummary.RenewalStatus,FailureReason:RenewalSummary.RenewalStatusReason}'
```

**If renewal is stuck at `PENDING_VALIDATION`:**

```bash
# Get the required CNAME records
aws acm describe-certificate \
  --certificate-arn <CERT_ARN> \
  --query 'Certificate.DomainValidationOptions[*].{Domain:DomainName,Name:ResourceRecord.Name,Value:ResourceRecord.Value}'

# Verify the CNAME exists in Route53
aws route53 list-resource-record-sets \
  --hosted-zone-id <HOSTED_ZONE_ID> \
  --query "ResourceRecordSets[?Type=='CNAME']"
```

If the validation CNAME is missing from Route53, re-add it. ACM will then pick it up within 30 minutes.

**CAA record check:** If a customer's domain has a CAA record blocking Amazon's CA, ACM cannot renew. Verify:

```bash
dig CAA <DOMAIN>
# Should include: 0 issue "amazon.com"
# Or have no CAA records at all
```

---

### 3l. Redis Down

**Symptoms:** Rate limiting errors or passes (fail-open), Celery workers cannot fetch tasks, users logged out unexpectedly, session errors.

**Impact by component:**

| Component | Behaviour when Redis is down |
|-----------|------------------------------|
| Rate limiting | Fails open — requests pass through without rate limiting |
| Celery broker | Workers cannot fetch new tasks; existing tasks continue until complete |
| Session store | Users may need to re-login (session tokens invalidated) |
| AI result cache | Cache misses; all AI requests go to providers (higher cost) |
| Clerk JWKS cache | Falls back to per-request Clerk verification (higher latency) |

**Check ElastiCache status:**

```bash
aws elasticache describe-replication-groups \
  --replication-group-id scr-production-redis \
  --query 'ReplicationGroups[0].{Status:Status,NodeGroups:NodeGroups}'
```

**Initiate failover to replica:**

```bash
aws elasticache test-failover \
  --replication-group-id scr-production-redis \
  --node-group-id 0001
```

Failover typically completes in 30–60 seconds. The API and Celery workers will automatically reconnect.

**If Redis data is lost:** Celery tasks that were in-flight will be requeued. Rate limit windows will reset. AI caches will be empty (cold start). No business data is stored in Redis — all persistent data is in PostgreSQL.

---

## 4. Deployment Procedures

### Standard Deployment (Blue/Green via ECS Rolling Update)

Production deployments use ECS rolling updates. The CD pipeline handles this automatically, but manual deployment is documented here.

**Pre-deployment checklist:**
- [ ] Staging deployment succeeded and smoke tests passed
- [ ] RDS snapshot completed (verify in AWS Console)
- [ ] No active incidents in production
- [ ] Change communicated in `#deployments` Slack channel

**Manual production deployment:**

```bash
# Deploy a specific image SHA (from staging)
gh workflow run cd-production.yml \
  -f image_tag=<COMMIT_SHA> \
  -f confirm=DEPLOY

# Monitor progress
gh run watch
```

**Force new deployment (same image, rolling restart):**

```bash
aws ecs update-service \
  --cluster scr-production \
  --service scr-api-production \
  --force-new-deployment

# Wait for stability
aws ecs wait services-stable \
  --cluster scr-production \
  --services scr-api-production
```

### Rollback

```bash
# List recent task definition versions
aws ecs list-task-definitions \
  --family-prefix scr-api-production \
  --sort DESC \
  --query 'taskDefinitionArns[:10]'

# Roll back to a specific revision
aws ecs update-service \
  --cluster scr-production \
  --service scr-api-production \
  --task-definition scr-api-production:<REVISION_NUMBER>
```

Repeat for `scr-web-production` and `scr-ai-gateway-production` if applicable.

---

## 5. Database Migration Runbook

**Never run migrations directly against production without following this procedure.**

### Pre-migration

```bash
# 1. Take a manual RDS snapshot (before the CD pipeline does it automatically)
aws rds create-db-snapshot \
  --db-instance-identifier scr-production-postgres \
  --db-snapshot-identifier scr-pre-migration-$(date +%Y%m%d-%H%M%S)

# 2. Wait for snapshot to complete
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier <SNAPSHOT_ID>

# 3. Check current migration state
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --network-configuration '{"awsvpcConfiguration":{"subnets":["<SUBNET_IDS>"],"securityGroups":["<SG_ID>"]}}' \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","current"]}]}'
```

### Apply Migration

```bash
# Run via ECS one-off task (same as CD pipeline)
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --network-configuration '{"awsvpcConfiguration":{"subnets":["<SUBNET_IDS>"],"securityGroups":["<SG_ID>"]}}' \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","upgrade","head"]}]}'
```

### Verify

```bash
# Confirm migrations applied correctly
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","current","--verbose"]}]}'

# Quick table existence check
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["python","-c","from sqlalchemy import inspect; from app.core.database import sync_engine; print(inspect(sync_engine).get_table_names())"]}]}'
```

### Rollback

```bash
# Roll back one migration step
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","downgrade","-1"]}]}'

# If multiple steps need rolling back, use specific revision:
# alembic downgrade <target_revision>
```

If the migration has caused data corruption and rollback is insufficient: restore from the pre-migration RDS snapshot per [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).

---

## 6. Escalation Contacts

| Role | Contact | When to escalate |
|------|---------|-----------------|
| On-call engineer | PagerDuty rotation | All P0/P1 |
| Engineering manager | PagerDuty escalation | P0, or P1 > 60 min unresolved |
| Database lead | Slack DM | RDS corruption, migration failures |
| Security officer | Slack DM / phone | Data breach, unauthorized access |
| AWS Support | Console → Support Center | Infrastructure outages beyond our control |
| Anthropic support | https://support.anthropic.com | Claude API outages requiring manual override |
