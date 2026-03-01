# Disaster Recovery Plan — SCR Platform v1.0.0

This document defines recovery procedures for catastrophic failures affecting the SCR Platform production environment. It should be reviewed quarterly and tested via tabletop exercises.

**Last reviewed:** 2026-03-01
**Owner:** Platform Engineering

---

## 1. RPO / RTO Targets

| Data Classification | Recovery Point Objective (RPO) | Recovery Time Objective (RTO) |
|--------------------|-------------------------------|-------------------------------|
| Full platform | 24 hours | 4 hours |
| Critical data (projects, documents, signal scores) | 1 hour (via RDS continuous replication) | 2 hours |
| User sessions and cache | On-demand (no recovery required) | N/A — stateless after restore |
| Audit logs | 24 hours | Recovered as part of database restore |

---

## 2. Backup Inventory

### PostgreSQL Database

| Backup Type | Mechanism | Retention | Location | Frequency |
|-------------|-----------|-----------|----------|-----------|
| Automated pg_dump | Celery `backup_database` task | 30 days in S3 Standard; Glacier after 90 days | `s3://scr-production-backups/pg_dump/` | Daily at 02:00 UTC |
| RDS Automated Backup | AWS managed (snapshots + WAL) | 14 days | RDS-managed storage | Continuous (WAL), daily snapshot |
| RDS Manual Snapshot | Created by CD pipeline pre-deployment | Until manually deleted | RDS-managed storage | Before each production deployment |
| Cross-region backup | pg_dump replicated to `eu-central-1` | 7 days | `s3://scr-dr-backups-frankfurt/pg_dump/` | Daily (replication job) |

**RDS point-in-time recovery (PITR):** Available to any second within the 14-day retention window. This is the preferred recovery method for partial data loss scenarios.

### Redis (ElastiCache)

| Backup Type | Mechanism | Retention | Notes |
|-------------|-----------|-----------|-------|
| AOF persistence | Redis Append-Only File | On-disk (not exported to S3) | Enabled on primary node |
| ElastiCache Snapshots | Automatic daily snapshots | 1 day | Triggered at 03:00 UTC |
| Manual snapshots | Via AWS Console or CLI | Until manually deleted | Create before major changes |

**Note:** Redis stores only ephemeral data (rate limit windows, session tokens, AI result cache, Celery queues). A Redis loss requires no data recovery — the application recovers by re-populating caches on demand. Celery tasks that were in-flight at the time of loss will be re-queued by `task_acks_late=True` behavior, provided the workers also restart.

### S3 Document Storage

| Bucket | Versioning | Cross-Region Replication | Notes |
|--------|-----------|--------------------------|-------|
| `scr-production-documents` | Enabled | Optional (configure in Terraform) | Source of truth for all uploaded files |
| `scr-production-redacted-pdfs` | Enabled | Optional | Generated clean PDFs from redaction workflow |
| `scr-production-backups` | Enabled | Yes — to `scr-dr-backups-frankfurt` | Database dumps |

S3 versioning means all object versions are retained. Accidental deletions can be recovered by removing the delete marker via AWS Console or CLI.

### Application Images

Docker images are stored in ECR with a retention policy of 20 tagged images. The image SHA for any previous production deployment can be retrieved from GitHub Actions run history or from `aws ecr describe-images`.

---

## 3. Recovery Procedures

### 3a. Database — Point-in-Time Recovery (Preferred)

Use when: data has been corrupted or accidentally deleted within the last 14 days.

```bash
# 1. Identify the target restore time (UTC)
# Use CloudWatch Logs or audit_logs to determine the last known good state

# 2. Initiate PITR restore (creates a NEW RDS instance — does not overwrite existing)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier scr-production-postgres \
  --target-db-instance-identifier scr-production-postgres-restored-$(date +%Y%m%d) \
  --restore-time 2026-03-01T06:00:00Z \
  --db-instance-class db.r6g.large \
  --no-multi-az \
  --no-publicly-accessible

# 3. Wait for restore to complete (10-30 minutes typical)
aws rds wait db-instance-available \
  --db-instance-identifier scr-production-postgres-restored-$(date +%Y%m%d)

# 4. Get the new endpoint
aws rds describe-db-instances \
  --db-instance-identifier scr-production-postgres-restored-$(date +%Y%m%d) \
  --query 'DBInstances[0].Endpoint.Address'

# 5. Verify data integrity on restored instance (read-only check)
psql "postgresql://scr:<PASSWORD>@<RESTORED_ENDPOINT>:5432/scr" \
  -c "SELECT COUNT(*) FROM organizations; SELECT COUNT(*) FROM projects; SELECT COUNT(*) FROM documents;"

# 6. If data is confirmed correct, update DATABASE_URL in Secrets Manager to point to restored instance
aws secretsmanager update-secret \
  --secret-id scr-production/database-url \
  --secret-string "postgresql+asyncpg://scr:<PASSWORD>@<RESTORED_ENDPOINT>:5432/scr"

# 7. Force new deployment of API and workers to pick up new connection string
aws ecs update-service --cluster scr-production --service scr-api-production --force-new-deployment
aws ecs update-service --cluster scr-production --service scr-celery-default-production --force-new-deployment
# Repeat for all Celery worker services

# 8. Verify application is healthy
curl https://api.scr-platform.com/health
curl -H "Authorization: Bearer <ADMIN_JWT>" https://api.scr-platform.com/admin/system-health

# 9. After confirming stable, promote restored instance to Multi-AZ and rename (optional)
# Or: use AWS RDS rename/swap to replace the primary instance
```

**Important:** PITR creates a new instance. The old instance is not modified. Keep both running until the restored instance is confirmed stable.

### 3b. Restore from pg_dump Backup

Use when: the RDS instance itself is lost and PITR is not available, or when restoring to a completely new environment.

```bash
# 1. List available backups
aws s3 ls s3://scr-production-backups/pg_dump/ | sort | tail -10

# 2. Download the most recent dump (or a specific date)
aws s3 cp \
  s3://scr-production-backups/pg_dump/scr-backup-2026-03-01-020000.dump.gz \
  /tmp/scr-backup.dump.gz

# 3. Decompress
gunzip /tmp/scr-backup.dump.gz

# 4. Create a new RDS instance (if the original is lost)
# Use Terraform: terraform apply -target=aws_db_instance.primary -var="environment=production"
# Or: create manually via AWS Console

# 5. Restore the dump
pg_restore \
  --host=<NEW_RDS_ENDPOINT> \
  --port=5432 \
  --username=scr \
  --dbname=scr \
  --no-owner \
  --no-privileges \
  --jobs=4 \
  /tmp/scr-backup.dump

# 6. Run Alembic to apply any migrations that occurred after the backup
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","upgrade","head"]}]}'

# 7. Update DATABASE_URL in Secrets Manager and redeploy services (same as step 6-8 in 3a)
```

**Data loss exposure:** pg_dump runs daily at 02:00 UTC. Maximum data loss is 24 hours. For production incidents, always prefer PITR (3a) which limits loss to seconds.

### 3c. Redis Recovery from Snapshot

Redis stores only ephemeral data. Recovery is typically not required. However, if a specific Redis snapshot is needed (e.g., to recover Celery task state from a short window):

```bash
# List available ElastiCache snapshots
aws elasticache describe-snapshots \
  --cache-cluster-id scr-production-redis \
  --query 'Snapshots[*].{Name:SnapshotName,CreateTime:SnapshotCreateTime}'

# Restore snapshot to a new cluster
aws elasticache create-replication-group \
  --replication-group-id scr-production-redis-restored \
  --replication-group-description "Disaster recovery restore" \
  --snapshot-name <SNAPSHOT_NAME> \
  --cache-node-type cache.r6g.large \
  --engine redis \
  --engine-version 7.0
```

In most disaster scenarios, simply creating a fresh Redis cluster is faster than restoring a snapshot. The application will repopulate all caches automatically.

### 3d. Application Re-Deployment from ECR

If ECS services are lost (e.g., cluster deleted or region outage):

```bash
# 1. List available images in ECR
aws ecr describe-images \
  --repository-name scr-api \
  --query 'imageDetails[*].{Tags:imageTags,PushedAt:imagePushedAt}' \
  | sort -k2

# 2. Find the last production image
# Production images are tagged: scr-api:<commit-sha> and scr-api:production-latest

# 3. Re-apply Terraform to recreate ECS infrastructure
cd infrastructure/terraform
terraform init
terraform apply \
  -var="environment=production" \
  -var="acm_certificate_arn=<CERT_ARN>" \
  -var="image_tag=<COMMIT_SHA>"

# 4. Run database migrations if on a clean database
aws ecs run-task \
  --cluster scr-production \
  --task-definition scr-api-migrate-production \
  --overrides '{"containerOverrides":[{"name":"api","command":["poetry","run","alembic","upgrade","head"]}]}'

# 5. Verify health
curl https://api.scr-platform.com/health
```

### 3e. Data Integrity Verification After Recovery

Run this checklist after any database restore to confirm data integrity before re-opening production traffic.

```sql
-- 1. Row counts on critical tables (compare with pre-incident baselines)
SELECT
  'organizations' AS tbl, COUNT(*) FROM organizations
UNION ALL SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'projects', COUNT(*) FROM projects
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'signal_scores', COUNT(*) FROM signal_scores
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'audit_logs', COUNT(*) FROM audit_logs;

-- 2. Verify most recent records are present (no unexpected data cutoff)
SELECT MAX(created_at) AS latest FROM organizations;
SELECT MAX(created_at) AS latest FROM projects;
SELECT MAX(created_at) AS latest FROM documents;
SELECT MAX(created_at) AS latest FROM signal_scores;

-- 3. Check for referential integrity issues
SELECT COUNT(*) FROM projects p
LEFT JOIN organizations o ON o.id = p.org_id
WHERE o.id IS NULL;  -- Should return 0

SELECT COUNT(*) FROM documents d
LEFT JOIN users u ON u.id = d.uploaded_by
WHERE u.id IS NULL;  -- Should return 0

-- 4. Check migration state
-- (run via alembic current)

-- 5. Verify no corrupted JSONB columns (quick sanity)
SELECT COUNT(*) FROM organizations WHERE settings IS NOT NULL;
SELECT COUNT(*) FROM users WHERE preferences IS NOT NULL;
```

Run the API smoke test suite:

```bash
# Health check
curl https://api.scr-platform.com/health

# System health (checks DB, Redis, AI Gateway connectivity)
curl -H "Authorization: Bearer <ADMIN_JWT>" \
  https://api.scr-platform.com/admin/system-health

# Basic data access test
curl -H "Authorization: Bearer <TEST_USER_JWT>" \
  https://api.scr-platform.com/projects?limit=1
```

---

## 4. Regional Failover

### Architecture

| | Primary | Standby |
|--|---------|---------|
| Region | `eu-west-1` (Ireland) | `eu-central-1` (Frankfurt) — manual failover only |
| RDS | Multi-AZ within `eu-west-1` | Cross-region read replica (optional, not currently provisioned) |
| S3 | `eu-west-1` with cross-region replication to `eu-central-1` | `scr-dr-backups-frankfurt` bucket |
| ECR | `eu-west-1` | Must re-push images or replicate (not currently automated) |
| Route53 | Health checks on primary ALB | Failover record pointing to standby ALB |

**Current standby status:** Manual failover only. A standby environment in `eu-central-1` must be provisioned before a regional failover is possible. Provisioning time from scratch: approximately 2–4 hours using Terraform.

### Regional Failover Steps

```bash
# 1. Confirm eu-west-1 is genuinely unavailable (not a transient issue)
# Check: https://health.aws.amazon.com

# 2. Provision standby infrastructure in eu-central-1
cd infrastructure/terraform
terraform workspace new production-frankfurt
terraform apply \
  -var="environment=production" \
  -var="aws_region=eu-central-1" \
  -var="acm_certificate_arn=<FRANKFURT_CERT_ARN>"

# 3. Restore database from cross-region backup
# Use pg_dump from s3://scr-dr-backups-frankfurt/pg_dump/ (see procedure 3b)

# 4. Push ECR images to eu-central-1 registry
aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin <FRANKFURT_ECR>
docker tag scr-api:<SHA> <FRANKFURT_ECR>/scr-api:<SHA>
docker push <FRANKFURT_ECR>/scr-api:<SHA>
# Repeat for scr-web and scr-ai-gateway

# 5. Update Secrets Manager in eu-central-1 with production values

# 6. Deploy services in eu-central-1

# 7. Update Route53 to point to Frankfurt ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id <HOSTED_ZONE_ID> \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"api.scr-platform.com","Type":"A","AliasTarget":{"DNSName":"<FRANKFURT_ALB_DNS>","EvaluateTargetHealth":true,"HostedZoneId":"<FRANKFURT_ALB_HZ_ID>"}}}]}'

# 8. Verify and notify customers
```

**Expected RTO for regional failover:** 2–4 hours.

---

## 5. Communication Plan

### Incident Communication Timeline

| Time | Action |
|------|--------|
| T+0 | Alert fires, on-call engineer acknowledges |
| T+15 min | Initial assessment complete, severity declared |
| T+30 min | Status page updated (for P0/P1): https://status.scr-platform.com |
| T+30 min | Customer notification email sent via Resend (P0/P1 only) |
| T+1 hr | Progress update posted to status page |
| T+2 hr | Engineering manager and CTO briefed (P0) |
| On resolve | Resolution notice posted to status page |
| T+48 hr | Post-mortem published (P0/P1) |

### Status Page Management

Status page is managed via Statuspage.io (or equivalent). To create an incident:

```bash
# Via Statuspage.io API
curl -X POST https://api.statuspage.io/v1/pages/<PAGE_ID>/incidents \
  -H "Authorization: OAuth <STATUSPAGE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "incident": {
      "name": "Service Degradation — API Errors",
      "status": "investigating",
      "impact_override": "critical",
      "body": "We are investigating elevated error rates affecting API requests. We will provide an update in 30 minutes."
    }
  }'
```

### SLA Obligations and Credit Policy

| Tier | Monthly Uptime SLA | Credit for Breach |
|------|--------------------|-------------------|
| Foundation | 99.0% | 10% of monthly fee per 1% below SLA |
| Professional | 99.5% | 25% of monthly fee per 1% below SLA |
| Enterprise | 99.9% | 50% of monthly fee per 1% below SLA |

Uptime is measured as the percentage of minutes in a calendar month during which `GET /health` returns 200 from at least one healthy ECS task. Scheduled maintenance windows (announced 48 hours in advance) are excluded.

Credits are applied to the next billing cycle, not refunded as cash, unless otherwise agreed in an Enterprise MSA.

---

## 6. Disaster Recovery Test Schedule

| Test Type | Frequency | Owner | Last Tested |
|-----------|-----------|-------|-------------|
| Database PITR restore (staging) | Quarterly | Platform Engineering | — |
| pg_dump restore (staging) | Bi-annually | Platform Engineering | — |
| Redis failover (production) | Annually | Platform Engineering | — |
| Full region failover (tabletop exercise) | Annually | Engineering leadership | — |
| Backup integrity verification | Monthly | Automated + manual spot check | — |
| Communication plan walkthrough | Annually | Engineering + CX | — |
