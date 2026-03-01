# Integration Guide — SCR Platform v1.0.0

This guide covers all external integration points available to SCR Platform customers: API access, webhooks, CRM sync, the Excel add-in, and white-label setup.

---

## 1. API Access

### Base URLs

| Environment | API Base URL | OpenAPI Docs |
|-------------|-------------|-------------|
| Production | `https://api.scr-platform.com` | `https://api.scr-platform.com/docs` |
| Staging | `https://api.staging.scr-platform.com` | `https://api.staging.scr-platform.com/docs` |

### Authentication Methods

The SCR Platform API supports two authentication methods:

#### Method 1: Clerk JWT (Interactive Users)

For browser-based applications and user-facing integrations.

```http
Authorization: Bearer <clerk_jwt>
```

Tokens are issued by Clerk and expire after the configured session duration (default: 7 days). Refresh tokens handle automatic renewal.

#### Method 2: API Keys (Programmatic Access)

For server-to-server integrations, the Excel add-in, and automation scripts.

```http
X-API-Key: scr_<your_key>
```

Or as a Bearer token:

```http
Authorization: Bearer scr_<your_key>
```

API keys are created via Settings → API Keys in the platform UI, or via the API:

```bash
curl -X POST \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Integration",
    "scopes": ["read:projects", "read:signals"],
    "expires_at": "2027-01-01T00:00:00Z"
  }' \
  https://api.scr-platform.com/api-keys
```

**The key is shown only once at creation.** Store it securely (e.g., in your secret manager). If lost, revoke the key and create a new one.

---

## 2. Rate Limits and Quotas

All requests are rate-limited per organisation. Limits differ by subscription tier.

### Request Rate Limits

| Tier | Standard API | AI Endpoints | Burst |
|------|-------------|-------------|-------|
| Foundation | 300 req/min | 100 req/hr | 50 req/sec for 10s |
| Professional | 1,000 req/min | 500 req/hr | 100 req/sec for 10s |
| Enterprise | 5,000 req/min | 2,000 req/hr | 500 req/sec for 10s |

### AI Token Limits

| Tier | Tokens/Day | Tokens/Month |
|------|-----------|-------------|
| Foundation | 500,000 | 15,000,000 |
| Professional | 2,000,000 | 60,000,000 |
| Enterprise | 10,000,000 | 300,000,000 |

### Rate Limit Headers

Every response includes:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1740844800
X-RateLimit-Window: 60
```

When the rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 15

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Retry after 15 seconds.",
  "retry_after": 15
}
```

### AI Budget Limits

In addition to token rate limits, each organisation has a monthly USD budget. When the budget is reached, AI-powered endpoints return:

```http
HTTP/1.1 402 Payment Required

{
  "error": "ai_budget_exceeded",
  "message": "Your organisation's monthly AI budget has been reached. Contact support to increase your limit."
}
```

---

## 3. API Endpoints Overview

Full interactive documentation is available at `https://api.scr-platform.com/docs`.

### Core Resources

| Resource | Base Path | Key Operations |
|----------|-----------|---------------|
| Projects | `/projects` | CRUD, publish, list by status/type |
| Documents | `/dataroom/documents` | Upload, download, list, version history |
| Signal Scores | `/signal-score` | Request score, get history, get explainability |
| Portfolio | `/portfolio` | CRUD portfolios, holdings, metrics |
| Deal Intelligence | `/deals` | Screen deal, get report, pipeline |
| Risk Assessment | `/risk` | Get risk report, dimensions |
| Legal Analysis | `/legal` | Analyse document, get gaps |
| Valuation | `/valuation` | Get valuation, update assumptions |
| ESG | `/esg` | Get ESG score, portfolio summary |

### AI Features

| Feature | Path | Notes |
|---------|------|-------|
| Ralph AI | `/ralph/conversations` | Conversational AI assistant |
| Ralph Streaming | `/ralph/stream` | SSE streaming for Ralph responses |
| Meeting Prep | `/meeting-prep` | AI-generated meeting brief |
| Expert Insights | `/expert-insights` | Expert notes with AI enrichment |
| Redaction | `/redaction/sessions` | AI-assisted PDF redaction workflow |

### Data and Analytics

| Feature | Path | Notes |
|---------|------|-------|
| Matching | `/matching` | Project-investor compatibility scores |
| Backtesting | `/backtesting` | Signal score accuracy metrics |
| Market Data | `/market-data` | External data feed access |
| Carbon Credits | `/carbon-credits` | Carbon project and credit data |
| Certifications | `/certification` | Certification workflow status |

### Infrastructure

| Feature | Path | Notes |
|---------|------|-------|
| Webhooks | `/v1/webhooks` | Manage webhook subscriptions |
| API Keys | `/api-keys` | Generate and revoke API keys |
| CRM Sync | `/crm` | CRM connection management |
| Notifications | `/notifications` | Notification preferences and history |
| Settings | `/settings` | Org settings, branding, users |

---

## 4. Webhooks

### Overview

Webhooks deliver real-time event notifications to your server via HTTP POST. Each delivery is signed with HMAC-SHA256 using a per-subscription secret.

### Creating a Webhook Subscription

```bash
curl -X POST \
  -H "Authorization: Bearer <ADMIN_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/scr-webhook",
    "events": ["signal_score.completed", "document.uploaded", "deal.screened"],
    "description": "Main event handler"
  }' \
  https://api.scr-platform.com/v1/webhooks
```

Response:

```json
{
  "id": "wh_01h...",
  "url": "https://your-server.com/scr-webhook",
  "events": ["signal_score.completed", "document.uploaded", "deal.screened"],
  "secret": "whsec_a8f3b2...",
  "is_active": true,
  "created_at": "2026-03-01T12:00:00Z"
}
```

**Store the `secret` securely.** It is shown only once.

### Available Event Types

| Event | Description | Payload Contains |
|-------|-------------|----------------|
| `signal_score.completed` | Signal score calculation finished | `project_id`, `score_id`, `overall_score`, dimensions |
| `signal_score.failed` | Signal score calculation failed | `project_id`, `error` |
| `document.uploaded` | Document uploaded to data room | `document_id`, `project_id`, `file_name`, `uploaded_by` |
| `document.accessed` | Document downloaded or viewed | `document_id`, `user_id`, `action` |
| `deal.screened` | AI deal screen completed | `project_id`, `screen_id`, `recommendation` |
| `deal.memo_generated` | Investment memo generated | `project_id`, `memo_id` |
| `risk.assessed` | Risk assessment completed | `project_id`, `risk_id`, `overall_risk` |
| `legal.analysed` | Legal document analysis completed | `document_id`, `analysis_id` |
| `matching.new_match` | New project-investor match | `project_id`, `investor_org_id`, `score` |
| `covenant.breach` | Portfolio covenant breach detected | `portfolio_id`, `covenant_id`, `metric`, `value` |
| `covenant.warning` | Portfolio covenant warning threshold hit | `portfolio_id`, `covenant_id`, `metric`, `value` |
| `qa.question_received` | Q&A question submitted | `question_id`, `project_id`, `from_org_id` |
| `qa.answer_received` | Q&A answer submitted | `question_id`, `answer_id` |
| `qa.sla_breach` | Q&A response SLA breached | `question_id`, `overdue_by_hours` |
| `report.generated` | LP report generated | `report_id`, `portfolio_id`, `format` |
| `user.created` | New user added to org | `user_id`, `email`, `role` |
| `user.deactivated` | User deactivated | `user_id`, `email` |
| `project.published` | Project published to marketplace | `project_id`, `project_name` |
| `certification.status_changed` | Certification status updated | `certification_id`, `project_id`, `status` |

### Webhook Payload Format

```json
{
  "id": "evt_01h...",
  "type": "signal_score.completed",
  "org_id": "org_01h...",
  "created_at": "2026-03-01T12:34:56Z",
  "data": {
    "project_id": "proj_01h...",
    "score_id": "ss_01h...",
    "overall_score": 78.4,
    "dimensions": {
      "project_viability_score": 82.0,
      "financial_planning_score": 75.0,
      "risk_assessment_score": 71.0,
      "team_strength_score": 83.0,
      "esg_score": 80.0
    }
  }
}
```

### Verifying Webhook Signatures

Every webhook delivery includes a signature header:

```http
X-SCR-Signature: sha256=<hex_digest>
X-SCR-Timestamp: 1740844800
```

**Verify in Python:**

```python
import hashlib
import hmac
import time

def verify_webhook(payload_body: bytes, signature_header: str, timestamp_header: str, secret: str) -> bool:
    # Reject requests older than 5 minutes
    timestamp = int(timestamp_header)
    if abs(time.time() - timestamp) > 300:
        return False

    # Compute expected signature
    signed_content = f"{timestamp_header}.{payload_body.decode('utf-8')}"
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        signed_content.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(f"sha256={expected_sig}", signature_header)
```

**Verify in Node.js:**

```javascript
const crypto = require('crypto');

function verifyWebhook(rawBody, signatureHeader, timestampHeader, secret) {
  const timestamp = parseInt(timestampHeader, 10);
  if (Math.abs(Date.now() / 1000 - timestamp) > 300) {
    return false; // Reject stale requests
  }

  const signedContent = `${timestampHeader}.${rawBody}`;
  const expectedSig = crypto
    .createHmac('sha256', secret)
    .update(signedContent)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(`sha256=${expectedSig}`),
    Buffer.from(signatureHeader)
  );
}
```

### Retry Policy

| Attempt | Delay |
|---------|-------|
| 1st retry | 1 minute |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |
| 4th retry | 2 hours |
| 5th retry | 8 hours |

After 10 consecutive failures across all events, the subscription is automatically disabled. Re-enable via the API or platform UI.

Your endpoint must return HTTP 2xx within 30 seconds to be considered successful. Timeouts and non-2xx responses are treated as failures.

### Webhook Best Practices

- **Respond immediately, process asynchronously.** Acknowledge the webhook with 200 and process the event in a background job to avoid timeouts.
- **Idempotency.** Use `evt.id` as an idempotency key — the same event may be delivered more than once (e.g., after a network timeout where your server received the request but our delivery timed out).
- **Filter by `org_id`.** Validate that incoming events belong to your expected organisation.
- **Use HTTPS.** HTTP endpoints are rejected.

---

## 5. HubSpot CRM Integration

### Prerequisites

- HubSpot account with API access (Professional or Enterprise tier)
- SCR Platform Professional subscription or higher
- `hubspot_sync` feature flag enabled for your org

### OAuth Setup Flow

1. Navigate to **Settings → Integrations → HubSpot** in the SCR Platform.
2. Click **Connect HubSpot**.
3. You are redirected to HubSpot's OAuth consent screen.
4. Approve the requested scopes: `contacts`, `companies`, `deals`, `crm.objects.contacts.read`, `crm.objects.contacts.write`.
5. HubSpot redirects back to SCR Platform with an authorization code.
6. SCR Platform exchanges the code for access and refresh tokens (stored encrypted with Fernet).

### What Syncs

| HubSpot Object | SCR Object | Direction |
|---------------|-----------|-----------|
| Company | Organization / Project | Bidirectional |
| Contact | User | HubSpot → SCR (read only) |
| Deal | Project / Deal Screen | Bidirectional |

### Sync Schedule

- **Automatic:** Every 6 hours via Celery Beat
- **Manual trigger:** Settings → Integrations → HubSpot → Sync Now

### Rate Limits

HubSpot enforces 100 requests per 10 seconds per token. The SCR sync worker respects this limit with built-in backoff.

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Sync stopped working | OAuth token expired | Re-authenticate via Settings → Integrations |
| Missing field mapping | Custom HubSpot property doesn't exist | Create the property in HubSpot or update the field mapping in SCR settings |
| Duplicate records | HubSpot duplicate detection | Enable HubSpot deduplication rules; SCR uses `hs_object_id` as external key |

---

## 6. Salesforce CRM Integration

### Prerequisites

- Salesforce account (Professional, Enterprise, or Unlimited edition)
- SCR Platform Enterprise subscription
- `salesforce_sync` feature flag enabled
- A connected app created in Salesforce (see below)

### Salesforce Connected App Setup

In Salesforce Setup:

1. Go to **App Manager → New Connected App**.
2. Enable **OAuth Settings**.
3. Set **Callback URL** to: `https://api.scr-platform.com/crm/salesforce/callback`
4. Select scopes: `api`, `refresh_token`, `offline_access`
5. Note the **Consumer Key** and **Consumer Secret**.

### OAuth Setup Flow in SCR Platform

1. Navigate to **Settings → Integrations → Salesforce**.
2. Enter your Salesforce **Consumer Key** and **Consumer Secret**.
3. Click **Connect Salesforce**.
4. Complete the OAuth flow in the Salesforce popup.

### What Syncs

| Salesforce Object | SCR Object | Direction |
|------------------|-----------|-----------|
| Account | Organization / Portfolio | Bidirectional |
| Lead | Project (early stage) | Salesforce → SCR |
| Opportunity | Project / Deal Screen | Bidirectional |
| Contact | User | Salesforce → SCR (read only) |

### Custom Field Mappings

Salesforce custom fields can be mapped to SCR project fields via **Settings → Integrations → Salesforce → Field Mappings**. Fields must exist in Salesforce before they can be mapped.

### Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `INVALID_FIELD` | Mapped field doesn't exist in Salesforce | Update field mapping or create the field in Salesforce |
| `INSUFFICIENT_ACCESS_RIGHTS` | Connected app user lacks permission | Grant the user Object-level access in Salesforce profiles |
| `REQUEST_LIMIT_EXCEEDED` | Salesforce API daily limit hit | Reduce sync frequency; upgrade Salesforce edition |

---

## 7. Excel Add-in

### Installation

The SCR Platform Excel add-in requires Microsoft 365 (Excel 2016 or later) or Excel on the web.

**Option A — Microsoft AppSource (recommended):**
1. In Excel, go to **Insert → Add-ins → Get Add-ins**.
2. Search for "SCR Platform".
3. Click **Add**.

**Option B — Manual sideload (IT-managed environments):**
1. Download the manifest XML from `https://api.scr-platform.com/excel-addin/manifest.xml`.
2. In Excel, go to **Insert → Add-ins → My Add-ins → Manage My Add-ins → Upload My Add-in**.
3. Select the downloaded manifest XML.

### Authentication

1. Open the SCR Platform task pane in Excel (via the **SCR** button in the ribbon).
2. Click **Sign In** and enter your SCR API key (generate one at Settings → API Keys with scope `read:projects read:signals read:portfolio`).
3. The API key is stored in Excel's secure storage.

### Available Excel Functions

| Function | Syntax | Description |
|----------|--------|-------------|
| `SCR.PROJECT` | `=SCR.PROJECT(project_id, field)` | Get a project field value |
| `SCR.SIGNAL_SCORE` | `=SCR.SIGNAL_SCORE(project_id, [dimension])` | Get overall or dimension score |
| `SCR.PORTFOLIO_NAV` | `=SCR.PORTFOLIO_NAV(portfolio_id)` | Get current portfolio NAV |
| `SCR.HOLDING_METRIC` | `=SCR.HOLDING_METRIC(holding_id, metric, date)` | Get a specific metric for a holding |
| `SCR.FX_RATE` | `=SCR.FX_RATE(from_currency, to_currency, [date])` | Get FX rate from ECB data |
| `SCR.VALUATION` | `=SCR.VALUATION(project_id, method)` | Get project valuation by method |
| `SCR.COVENANT_STATUS` | `=SCR.COVENANT_STATUS(portfolio_id, covenant_name)` | Get covenant compliance status |

### Function Examples

```excel
=SCR.PROJECT("proj_01h...", "name")
=SCR.SIGNAL_SCORE("proj_01h...", "esg_score")
=SCR.PORTFOLIO_NAV("port_01h...")
=SCR.FX_RATE("EUR", "USD")
=SCR.VALUATION("proj_01h...", "dcf")
```

### Data Refresh

By default, Excel functions cache results for 5 minutes. To force a refresh:
- Press **Ctrl+Alt+F9** to recalculate all cells.
- Or configure auto-refresh interval in the SCR task pane settings (minimum: 60 seconds).

### Rate Limits for Excel Add-in

Excel add-in requests use API key authentication and count against your org's standard rate limit. Each function call is one API request. For large spreadsheets with many SCR functions, use batch ranges or consider increasing your rate limit tier.

---

## 8. White-Label Setup

White-label allows partners to present SCR Platform under their own brand and domain.

### Requirements

- Enterprise subscription
- `white_label` feature flag enabled
- DNS access to the partner's domain

### Setup Process

Contact your SCR Platform account manager to initiate white-label setup. The following is configured per partner:

| Setting | Description |
|---------|-------------|
| Custom domain | `app.yourcompany.com` → SCR Platform |
| Logo | Replaces SCR logo in navigation and emails |
| Primary color | Brand color for buttons and accents |
| Email sender | `noreply@yourcompany.com` for all platform emails |
| Favicon | Browser tab icon |
| Page title | Browser tab title prefix |

### Technical Requirements

**DNS (partner configures):**
```
app.yourcompany.com  CNAME  custom.scr-platform.com
```

**Email sending (partner configures):**
- SPF record: `v=spf1 include:spf.resend.com ~all`
- DKIM record: provided by SCR Platform team
- DMARC: `v=DMARC1; p=quarantine; pct=100`

### Testing Your White-Label Setup

```bash
# Test routing
curl -I -H "Host: app.yourcompany.com" https://custom.scr-platform.com/

# Test health endpoint
curl https://app.yourcompany.com/api/health
```

---

## 9. Pagination

All list endpoints use cursor-based pagination.

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 20 | Items per page (max 100) |
| `cursor` | string | null | Cursor from previous response |
| `order_by` | string | `created_at` | Sort field |
| `order_dir` | string | `desc` | `asc` or `desc` |

### Response Format

```json
{
  "items": [...],
  "total": 243,
  "limit": 20,
  "cursor": "eyJpZCI6Ii4uLiJ9",
  "has_more": true
}
```

### Example

```bash
# First page
curl "https://api.scr-platform.com/projects?limit=20" \
  -H "Authorization: Bearer <TOKEN>"

# Next page
curl "https://api.scr-platform.com/projects?limit=20&cursor=eyJpZCI6Ii4uLiJ9" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 10. Error Handling

### Error Response Format

All API errors follow a consistent JSON format:

```json
{
  "error": "not_found",
  "message": "Project not found or you do not have access.",
  "details": {
    "resource": "Project",
    "id": "proj_01h..."
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No content (DELETE success) |
| `400` | Bad request — invalid parameters |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — insufficient permissions |
| `404` | Not found |
| `409` | Conflict — resource already exists |
| `413` | Payload too large (max 50 MB) |
| `422` | Unprocessable entity — validation error |
| `429` | Rate limit exceeded |
| `402` | AI budget exceeded |
| `500` | Internal server error |
| `503` | Service unavailable |

### Common Error Codes

| Error Code | Description |
|-----------|-------------|
| `authentication_failed` | JWT or API key is invalid or expired |
| `permission_denied` | Your role does not have access to this operation |
| `rate_limit_exceeded` | Too many requests — check `Retry-After` header |
| `ai_budget_exceeded` | Monthly AI budget reached — contact support |
| `validation_error` | Request body failed schema validation |
| `not_found` | Resource does not exist or is not accessible |
| `conflict` | Resource already exists (e.g., duplicate slug) |
| `file_too_large` | Upload exceeds 50 MB limit |
| `unsupported_file_type` | File MIME type not allowed |

---

## 11. SDK and Code Examples

Official SDKs are not yet published. Use any HTTP client. Examples below use curl and Python requests.

### Python Example

```python
import requests

API_BASE = "https://api.scr-platform.com"
API_KEY = "scr_your_key_here"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

# List projects
response = requests.get(f"{API_BASE}/projects", headers=headers, params={"limit": 10})
response.raise_for_status()
projects = response.json()["items"]

# Get signal score for a project
project_id = projects[0]["id"]
score_response = requests.get(f"{API_BASE}/signal-score/{project_id}/latest", headers=headers)
score = score_response.json()

print(f"Project: {projects[0]['name']}")
print(f"Overall score: {score['overall_score']}")
print(f"ESG score: {score['dimensions']['esg_score']}")
```

### TypeScript / Node.js Example

```typescript
const API_BASE = 'https://api.scr-platform.com';
const API_KEY = process.env.SCR_API_KEY!;

async function getProjects() {
  const response = await fetch(`${API_BASE}/projects?limit=10`, {
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`API error: ${error.message}`);
  }

  return response.json();
}

async function getLatestSignalScore(projectId: string) {
  const response = await fetch(`${API_BASE}/signal-score/${projectId}/latest`, {
    headers: { 'X-API-Key': API_KEY },
  });
  return response.json();
}
```
