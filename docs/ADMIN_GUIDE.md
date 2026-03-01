# Administrator Guide — SCR Platform v1.0.0

This guide is for SCR Platform administrators (users with `role = ADMIN` and `org_type = ADMIN`) who manage the platform, organisations, and operational configuration.

---

## 1. Administrator Access

Platform administrators have an organisation with `type = ADMIN` in the database. This grants cross-org visibility and access to admin-only API endpoints under `/admin/*`.

Standard organisation admins (role `ADMIN` within their own org) can manage their org's settings but cannot see other organisations' data.

### Admin API Authentication

All admin endpoints require:

```
Authorization: Bearer <CLERK_JWT>
```

The JWT must belong to a user with `role = ADMIN` and `org_type = ADMIN`. Regular org admins are blocked from platform-level admin endpoints.

### Platform Admin Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /admin/system-health` | DB, Redis, AI Gateway connectivity and latency |
| `GET /admin/ai-costs` | AI spend by org, model, and task type |
| `GET /v1/admin/ai-budget-overview` | Per-org budget vs spend summary |
| `GET /admin/prompts` | List all prompt templates |
| `POST /admin/prompts` | Create a new prompt template |
| `PUT /admin/prompts/{id}` | Update a prompt template |
| `GET /admin/feature-flags` | List all feature flags |
| `PUT /admin/feature-flags/{org_id}/{key}` | Set a feature flag |

---

## 2. Organisation Management

### Creating an Organisation

New organisations are created when a customer signs up via the onboarding flow. Clerk handles user creation and fires a `user.created` webhook. The SCR onboarding module creates the corresponding `Organization` and `User` records.

To manually create an organisation (e.g., for an enterprise pilot):

```sql
INSERT INTO organizations (id, name, slug, type, subscription_tier, subscription_status, settings)
VALUES (
  gen_random_uuid(),
  'Acme Capital',
  'acme-capital',
  'INVESTOR',
  'PROFESSIONAL',
  'ACTIVE',
  '{}'::jsonb
);
```

Then create the first admin user via Clerk dashboard and ensure the `User` record has `org_id` set to the new org and `role = ADMIN`.

### Organisation Settings

Organisation settings are stored in the `organizations.settings` JSONB column. The standard schema includes:

```json
{
  "branding": {
    "logo_url": "https://...",
    "primary_color": "#1a56db",
    "font": "Inter"
  },
  "notifications": {
    "weekly_digest": true,
    "deal_alerts": true
  },
  "matching": {
    "min_deal_size_usd": 1000000,
    "max_deal_size_usd": 50000000,
    "preferred_geographies": ["EU", "UK"],
    "preferred_sectors": ["solar", "wind", "storage"]
  }
}
```

Update via the settings API:

```bash
curl -X PUT \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"branding": {"primary_color": "#2563eb"}}' \
  https://api.scr-platform.com/settings/branding
```

### Subscription Tier Management

Subscription tiers control AI rate limits, feature access, and monthly SLA commitments.

| Tier | AI Rate Limit | Token Limit | Default AI Budget |
|------|--------------|-------------|-------------------|
| `foundation` | 100 req/hr, 500K tokens/day | 500K tokens/day | $50/month |
| `professional` | 500 req/hr, 2M tokens/day | 2M tokens/day | $200/month |
| `enterprise` | 2000 req/hr, 10M tokens/day | 10M tokens/day | $1,000/month |

Change a subscription tier:

```sql
UPDATE organizations
SET subscription_tier = 'ENTERPRISE',
    subscription_status = 'ACTIVE'
WHERE id = '<ORG_UUID>';
```

### Subscription Status Values

| Status | Meaning |
|--------|---------|
| `TRIAL` | Free trial, full feature access for limited period |
| `ACTIVE` | Paid subscription, all features available |
| `PAST_DUE` | Payment failed, grace period active |
| `CANCELLED` | Subscription cancelled, read-only access |
| `SUSPENDED` | Admin-suspended, no access |

---

## 3. Custom Domain and Branding (White-Label)

White-label setup requires both DNS configuration by the customer and infrastructure changes by the platform admin.

### Setup Steps

**Step 1 — Customer DNS:** Customer adds a CNAME record:
```
<their-domain>  CNAME  custom.scr-platform.com
```

**Step 2 — Request ACM certificate** (must be in `us-east-1` for CloudFront):
```bash
aws acm request-certificate \
  --region us-east-1 \
  --domain-name <CUSTOMER_DOMAIN> \
  --validation-method DNS
```

**Step 3 — Customer adds ACM DNS validation CNAME** (provided by ACM in the console or via CLI):
```bash
aws acm describe-certificate \
  --region us-east-1 \
  --certificate-arn <CERT_ARN> \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'
```

**Step 4 — Wait for ACM to issue** (5–30 minutes after customer adds the CNAME).

**Step 5 — Add alternate domain to CloudFront distribution:**
```bash
aws cloudfront get-distribution-config --id <DIST_ID> > dist-config.json
# Edit dist-config.json: add domain to Aliases.Items, update ViewerCertificate
aws cloudfront update-distribution --id <DIST_ID> --distribution-config file://dist-config.json
```

**Step 6 — Create database record:**
```sql
INSERT INTO custom_domains (org_id, domain, ssl_status, is_active)
VALUES ('<ORG_UUID>', '<CUSTOMER_DOMAIN>', 'ACTIVE', true);
```

**Step 7 — Configure org branding:**
```bash
curl -X PUT \
  -H "Authorization: Bearer <ORG_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "logo_url": "https://cdn.customer.com/logo.png",
    "primary_color": "#1a56db",
    "custom_email_from": "noreply@customer.com"
  }' \
  https://api.scr-platform.com/settings/branding
```

---

## 4. AI Budget Configuration

### Per-Org Budget Override

The `organizations.ai_monthly_budget` column overrides the tier default. When `NULL`, the tier default applies.

```sql
-- Set a custom monthly budget of $500 for a specific org
UPDATE organizations
SET ai_monthly_budget = 500.00
WHERE id = '<ORG_UUID>';

-- Reset to tier default
UPDATE organizations
SET ai_monthly_budget = NULL
WHERE id = '<ORG_UUID>';
```

### Budget Enforcement Behaviour

- At 80% of monthly budget: a `warning` notification is sent to org admins.
- At 100% of monthly budget: AI features are blocked for the org. Users see a "budget exceeded" message.
- AI calls that are already in-flight (Celery queue) are allowed to complete.
- Read endpoints and non-AI features are never blocked.

### Monitoring AI Spend

```bash
# Platform-wide AI cost overview
curl -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  https://api.scr-platform.com/v1/admin/ai-budget-overview

# Per-model costs (code reference)
# apps/api/app/services/ai_costs.py — MODEL_COSTS dict
```

```sql
-- Per-org spend this month
SELECT
  o.name,
  o.subscription_tier,
  o.ai_monthly_budget,
  ROUND(SUM(atl.cost_usd)::numeric, 4) AS month_spend_usd,
  ROUND((SUM(atl.cost_usd) / NULLIF(o.ai_monthly_budget, 0) * 100)::numeric, 1) AS pct_used
FROM ai_task_logs atl
JOIN organizations o ON o.id = atl.org_id
WHERE atl.created_at >= date_trunc('month', now())
GROUP BY o.id, o.name, o.subscription_tier, o.ai_monthly_budget
ORDER BY month_spend_usd DESC;
```

---

## 5. Feature Flag Management

Feature flags control per-org access to specific platform features without requiring a deployment.

### Database Schema

```sql
-- feature_flags table
-- (org_id, feature_key, is_enabled, config JSONB, created_at, updated_at)
```

### Via Admin API

```bash
# List all feature flags for an org
curl -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  https://api.scr-platform.com/admin/feature-flags?org_id=<ORG_UUID>

# Enable a feature flag
curl -X PUT \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": true, "config": {}}' \
  https://api.scr-platform.com/admin/feature-flags/<ORG_UUID>/blockchain_audit

# Disable a feature flag
curl -X PUT \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": false}' \
  https://api.scr-platform.com/admin/feature-flags/<ORG_UUID>/blockchain_audit
```

### Via SQL (emergency)

```sql
-- Enable a feature flag
INSERT INTO feature_flags (org_id, feature_key, is_enabled)
VALUES ('<ORG_UUID>', 'blockchain_audit', true)
ON CONFLICT (org_id, feature_key)
DO UPDATE SET is_enabled = true, updated_at = now();

-- Disable globally (all orgs)
UPDATE feature_flags
SET is_enabled = false
WHERE feature_key = 'experimental_feature';
```

### Available Feature Keys

| Key | Description | Default |
|-----|-------------|---------|
| `blockchain_audit` | SHA-256 + Polygon anchoring for documents | false |
| `voice_input` | Voice-to-text deal notes | false |
| `excel_addin` | Excel add-in API access | false |
| `white_label` | Custom domain and branding | false |
| `salesforce_sync` | Salesforce CRM integration | false |
| `hubspot_sync` | HubSpot CRM integration | true (Professional+) |
| `ai_redaction` | AI-assisted PDF redaction | false |
| `backtesting` | Signal score backtesting | false |
| `external_data_feeds` | IRENA/World Bank/EU ETS data | false |

---

## 6. API Key Management

API keys allow programmatic access to the SCR Platform API (used by the Excel add-in and external integrations).

### Key Structure

API keys are prefixed `scr_` followed by 32 random bytes (hex-encoded). Only the SHA-256 hash is stored in the database — the plaintext key is shown only once at creation time.

### Managing Keys

```bash
# List API keys for an org
curl -H "Authorization: Bearer <ORG_ADMIN_JWT>" \
  https://api.scr-platform.com/api-keys

# Create a new API key
curl -X POST \
  -H "Authorization: Bearer <ORG_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Excel Add-in", "scopes": ["read:projects", "read:signals"], "expires_at": "2027-01-01T00:00:00Z"}' \
  https://api.scr-platform.com/api-keys

# Revoke an API key
curl -X DELETE \
  -H "Authorization: Bearer <ORG_ADMIN_JWT>" \
  https://api.scr-platform.com/api-keys/<KEY_ID>
```

### Available Scopes

| Scope | Description |
|-------|-------------|
| `read:projects` | Read project data |
| `write:projects` | Create and update projects |
| `read:signals` | Read signal scores |
| `read:documents` | Read document metadata and download |
| `write:documents` | Upload documents |
| `read:portfolio` | Read portfolio data |
| `read:reports` | Download generated reports |
| `admin` | Full access (platform admin only) |

### Rate Limits for API Keys

API key requests are subject to the same per-org rate limits as JWT-authenticated requests. Additionally, the `api_keys` table supports a per-key `rate_limit_override` that can restrict a key below the org tier limit.

---

## 7. User Management and RBAC

### User Roles

| Role | Permissions |
|------|-------------|
| `viewer` | Read-only access to org data |
| `analyst` | Read + create/edit projects and documents |
| `manager` | All analyst permissions + user management + settings |
| `admin` | Full access including billing and API key management |

### Changing a User's Role

Via the settings API (requires `manager` or `admin` role):

```bash
curl -X PUT \
  -H "Authorization: Bearer <MANAGER_OR_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"role": "analyst"}' \
  https://api.scr-platform.com/settings/users/<USER_ID>/role
```

Via SQL (emergency):

```sql
UPDATE users
SET role = 'MANAGER'
WHERE id = '<USER_UUID>'
  AND org_id = '<ORG_UUID>';  -- Always scope to org
```

### Deactivating a User

When a user leaves an organisation, deactivate their account (do not delete — preserve audit log references):

```bash
curl -X DELETE \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  https://api.scr-platform.com/settings/users/<USER_ID>
```

This sets `users.is_active = false`. The user's Clerk account should also be suspended via the Clerk dashboard.

### User Preferences

User preferences are stored in `users.preferences` as JSONB:

```json
{
  "digest": {
    "enabled": true,
    "frequency": "weekly",
    "categories": ["deals", "signals", "portfolio"]
  },
  "notifications": {
    "email": true,
    "in_app": true
  },
  "theme": "light"
}
```

---

## 8. Prompt Template Management

The prompt registry allows updating AI prompts without a code deployment.

### Viewing Active Prompts

```bash
curl -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  https://api.scr-platform.com/admin/prompts?is_active=true
```

### Creating a New Prompt Version

```bash
curl -X POST \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "signal_score",
    "version": 3,
    "content": "You are an expert investment analyst...",
    "system_prompt": "You evaluate renewable energy projects...",
    "is_active": true
  }' \
  https://api.scr-platform.com/admin/prompts
```

Setting `is_active: true` on the new version automatically deactivates the previous active version for that `task_type`. The system always uses the single active version per task type, with a fallback to the hardcoded default if no active template exists.

### Task Types

| Task Type | Used By |
|-----------|---------|
| `signal_score` | Signal Score module |
| `risk_assessment` | Risk module |
| `legal_analysis` | Legal module |
| `deal_screening` | Deal Intelligence module |
| `meeting_prep` | Meeting Prep module |
| `esg_analysis` | ESG module |
| `carbon_analysis` | Carbon Credits module |
| `valuation_narrative` | Valuation module |
| `document_summary` | Data Room module |
| `expert_enrichment` | Expert Insights module |
| `redaction_detection` | Redaction module |
| `chat_with_tools` | Ralph AI |

---

## 9. Webhook Configuration (Admin)

### Viewing All Webhooks

Platform admins can view webhook subscriptions across all orgs:

```sql
SELECT
  ws.id,
  o.name AS org_name,
  ws.url,
  ws.events,
  ws.is_active,
  ws.failure_count,
  ws.created_at
FROM webhook_subscriptions ws
JOIN organizations o ON o.id = ws.org_id
ORDER BY ws.created_at DESC;
```

### Re-enabling a Disabled Webhook

```bash
# Via API (as platform admin)
curl -X PUT \
  -H "Authorization: Bearer <PLATFORM_ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true, "failure_count": 0}' \
  https://api.scr-platform.com/v1/webhooks/<WEBHOOK_ID>
```

```sql
-- Via SQL
UPDATE webhook_subscriptions
SET is_active = true, failure_count = 0, disabled_reason = NULL
WHERE id = '<WEBHOOK_UUID>';
```

---

## 10. CRM Integration Management

### Viewing Connected CRM Integrations

```sql
SELECT
  o.name AS org_name,
  cc.provider,
  cc.is_active,
  cc.last_synced_at,
  cc.created_at
FROM crm_connections cc
JOIN organizations o ON o.id = cc.org_id
ORDER BY cc.created_at DESC;
```

### Resetting a CRM Connection (Force Re-authentication)

If an OAuth token is corrupted or expired:

```sql
-- Mark connection as inactive to force re-authentication
UPDATE crm_connections
SET is_active = false
WHERE org_id = '<ORG_UUID>'
  AND provider = 'hubspot';
```

The user will be prompted to re-authenticate when they next access the CRM settings page.

### Manual CRM Sync Trigger

```bash
# Trigger a sync via Celery (from worker container)
celery -A app.worker call crm_sync.sync_org --args='["<ORG_UUID>", "hubspot"]'
```

---

## 11. Data Retention Policy Management

Retention policies are defined in code (`apps/api/app/tasks/data_retention.py`). Changes require a deployment. The policies cannot currently be changed per-org.

### Current Policies

| Table | Retention | Action |
|-------|-----------|--------|
| `audit_logs` | 365 days | Archive candidate (logged, not deleted) |
| `document_access_logs` | 365 days | Archive candidate |
| `ai_task_logs` | 90 days | Archive candidate |
| `digest_logs` | 90 days | Hard delete |
| `usage_events` | 180 days | Hard delete |
| `webhook_deliveries` | 30 days | Hard delete |

### Manual Retention Run

```bash
# Trigger via Celery
celery -A app.worker call data_retention_cleanup
```

### Checking Table Sizes

```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total_size,
  pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS table_size,
  pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 20;
```

---

## 12. Celery Flower Monitoring

Celery Flower provides a web UI for monitoring queue depths, task history, and worker status.

**Access:** Flower runs on port 5555 on the Celery Beat ECS task. Access via SSH tunnel through the VPN/bastion:

```bash
# Port-forward via bastion (or use AWS Systems Manager Session Manager)
ssh -L 5555:<CELERY_TASK_PRIVATE_IP>:5555 bastion.scr-platform.com
# Then open http://localhost:5555 in browser
```

### Key Flower Views

| View | URL | Purpose |
|------|-----|---------|
| Dashboard | `/` | Active tasks, workers, processed count |
| Workers | `/workers` | Worker status, heartbeat, task rates |
| Tasks | `/tasks` | Task history, filter by state |
| Queues | `/queues` | Per-queue message counts |
| Monitor | `/monitor` | Success/failure rate charts |

### Common Celery Admin Commands

```bash
# List active tasks across all workers
celery -A app.worker inspect active

# List registered tasks
celery -A app.worker inspect registered

# Purge a specific queue (DANGEROUS — tasks lost permanently)
celery -A app.worker purge -Q bulk

# Revoke a specific task
celery -A app.worker control revoke <TASK_ID> --terminate
```

---

## 13. Database Maintenance

### Regular Maintenance Tasks

These run automatically but can be triggered manually if needed:

```sql
-- VACUUM ANALYZE on large tables (run during low-traffic periods)
VACUUM ANALYZE audit_logs;
VACUUM ANALYZE ai_task_logs;
VACUUM ANALYZE document_access_logs;
VACUUM ANALYZE webhook_deliveries;

-- Check for table bloat
SELECT schemaname, tablename, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / nullif(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE 'pg_%'
ORDER BY indexrelname;
```

### Connection Pool Tuning

The API uses SQLAlchemy asyncpg connection pool. Key parameters are set via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_POOL_SIZE` | 10 | Connections per uvicorn worker |
| `DATABASE_MAX_OVERFLOW` | 20 | Extra connections above pool size |
| `DATABASE_POOL_TIMEOUT` | 30 | Seconds to wait for a connection |
| `DATABASE_POOL_RECYCLE` | 3600 | Recycle connections after N seconds |

With 4 uvicorn workers: `(10 + 20) × 4 = 120` max connections from the API alone. RDS max connections for `db.r6g.large` is approximately 2,000. Current configuration has significant headroom.
