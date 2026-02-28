# API Reference

Base URL: `http://localhost:8000` (development) · `https://api.scr-platform.com` (production)

All endpoints require `Authorization: Bearer <clerk_jwt>` unless marked as public.

Interactive docs (development only): `http://localhost:8000/docs`

---

## Conventions

### Pagination

List endpoints return:
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

Default: `page=1`, `page_size=20`, max `page_size=100`.

### Error responses

```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request / validation failed |
| `401` | Missing or invalid JWT |
| `403` | Insufficient role or permission |
| `404` | Resource not found (within caller's org) |
| `409` | Conflict (e.g. duplicate) |
| `413` | Request body > 50 MB |
| `422` | Unprocessable entity (Pydantic validation) |
| `429` | Rate limit exceeded |

### Soft delete

Most resources use soft delete (`is_deleted = true`). Deleted items are excluded from list responses and return 404 on detail endpoints.

---

## Auth

### `POST /auth/login`

Verify Clerk JWT and return the current user's platform profile.

**Response:**
```json
{
  "user_id": "uuid",
  "org_id": "uuid",
  "email": "alice@example.com",
  "role": "manager",
  "org_type": "ALLY",
  "org_name": "Sunstone Projects"
}
```

### `POST /auth/webhooks`

Clerk webhook receiver (Svix HMAC verified). Syncs user.created / user.updated / user.deleted events.

---

## Projects

**Prefix:** `/projects` · **Users:** Ally · **Min role:** viewer (read), manager (create), analyst (edit), admin (delete)

### `GET /projects/stats`

Dashboard KPIs for all projects in the org.

**Response:**
```json
{
  "total": 12,
  "by_status": { "draft": 3, "active": 5, "fundraising": 4 },
  "by_type": { "solar": 6, "wind": 4, "hydro": 2 },
  "avg_signal_score": 72.4,
  "total_investment_required": 45000000
}
```

### `GET /projects`

Paginated project list.

**Query params:** `status`, `type`, `stage`, `geography`, `score_min`, `score_max`, `search`, `page`, `page_size`, `sort_by`, `sort_order`

### `POST /projects` → `201`

```json
{
  "name": "Sunstone Solar I",
  "project_type": "solar",
  "description": "...",
  "geography_country": "US",
  "geography_region": "Nevada",
  "capacity_mw": 50.0,
  "total_investment_required": 75000000,
  "currency": "USD",
  "stage": "development"
}
```

### `GET /projects/{id}`

Detail with milestone count, budget item count, document count, and latest signal score breakdown.

### `PUT /projects/{id}`

Partial update (all fields optional).

### `DELETE /projects/{id}` → `204`

Soft delete.

### `PUT /projects/{id}/publish`

Publish to marketplace. Requires `status = active` and `is_published = false`.

### `GET /projects/{id}/milestones`

List milestones ordered by `order_index`.

### `POST /projects/{id}/milestones` → `201`

```json
{ "name": "Permitting complete", "target_date": "2025-06-01", "order_index": 1 }
```

### `PUT /projects/{id}/milestones/{milestone_id}`

Update milestone (name, dates, status, completion_pct).

### `DELETE /projects/{id}/milestones/{milestone_id}` → `204`

### `GET /projects/{id}/budget`

List budget items.

### `POST /projects/{id}/budget` → `201`

```json
{ "category": "construction", "description": "Panels", "estimated_amount": 5000000, "currency": "USD" }
```

### `PUT /projects/{id}/budget/{budget_id}`

### `DELETE /projects/{id}/budget/{budget_id}` → `204`

### `POST /projects/{id}/ai/generate/{action_type}` → `202`

Trigger async AI generation. `action_type`: `executive_summary`, `financial_overview`, `market_analysis`, `risk_narrative`, `esg_statement`, `technical_summary`, `investor_pitch`.

Returns `{ "task_log_id": "uuid", "status": "pending" }`.

### `GET /projects/{id}/ai/tasks/{task_log_id}`

Poll generation result. `status`: `pending → running → completed | failed`.

---

## Portfolio

**Prefix:** `/portfolio` · **Users:** Investor · **Min role:** viewer (read), manager (create/edit)

### `GET /portfolio`

List all portfolios.

### `POST /portfolio` → `201`

```json
{
  "name": "Climate Impact Fund I",
  "strategy": "impact_first",
  "fund_type": "closed_end",
  "vintage_year": 2023,
  "target_aum": 200000000,
  "currency": "USD",
  "sfdr_classification": "article_9"
}
```

### `GET /portfolio/{id}`

Detail with latest metrics and holding count.

### `PUT /portfolio/{id}`

### `GET /portfolio/{id}/metrics`

Computed metrics: IRR (gross/net), MOIC, TVPI, DPI, RVPI, total invested, total distributions, total value, carbon reduction.

### `GET /portfolio/{id}/holdings`

**Query:** `status` (active, exited, written_off)

Returns holdings list + totals (total_invested, total_current_value, weighted_moic).

### `POST /portfolio/{id}/holdings` → `201`

```json
{
  "asset_name": "Sunstone Solar I",
  "asset_type": "equity",
  "investment_date": "2024-03-15",
  "investment_amount": 5000000,
  "current_value": 5800000,
  "ownership_pct": 12.5,
  "currency": "USD",
  "project_id": "uuid"
}
```

### `PUT /portfolio/{id}/holdings/{holding_id}`

### `GET /portfolio/{id}/cash-flows`

Cash flow time series for IRR calculation.

### `GET /portfolio/{id}/allocation`

Breakdown by sector, geography, stage, asset type.

---

## Data Room

**Prefix:** `/dataroom` · **Users:** Both · **Min role:** viewer (read), analyst (upload)

### `GET /dataroom/documents`

**Query:** `project_id`, `document_type`, `page`, `page_size`

### `POST /dataroom/documents/upload-url`

Get a pre-signed S3 PUT URL.

```json
{ "filename": "pitch-deck.pdf", "content_type": "application/pdf", "project_id": "uuid" }
```

Response: `{ "upload_url": "...", "document_id": "uuid" }`

### `POST /dataroom/documents/{id}/confirm`

Confirm upload complete. Triggers SHA-256 verification and text extraction task.

### `GET /dataroom/documents/{id}`

Document detail with access log.

### `GET /dataroom/documents/{id}/download-url`

Pre-signed GET URL (logs a download access event).

### `DELETE /dataroom/documents/{id}` → `204`

Soft delete. Requires manager+.

### `GET /dataroom/documents/{id}/extractions`

AI-extracted content (KPI, clause, deadline, financial, classification, summary types).

---

## Notifications

**Prefix:** `/notifications` · **Users:** Both

### `GET /notifications/stream`

SSE stream of real-time notifications.

```
data: {"id": "uuid", "type": "action_required", "title": "...", "body": "...", "created_at": "..."}
```

### `GET /notifications`

**Query:** `unread_only=true`, `page`, `page_size`

### `GET /notifications/unread-count`

Returns `{ "count": 3 }`.

### `PUT /notifications/{id}/read`

Mark as read.

### `PUT /notifications/read-all`

Mark all as read.

---

## Ralph AI

**Prefix:** `/ralph` · **Users:** Both · **Rate limit:** 60 req/min

### `POST /ralph/conversations` → `201`

```json
{ "title": "Portfolio review", "context_type": "portfolio", "context_entity_id": "uuid" }
```

### `GET /ralph/conversations`

List conversations (most recent first).

### `GET /ralph/conversations/{id}`

Detail with full message history.

### `DELETE /ralph/conversations/{id}` → `204`

### `POST /ralph/conversations/{id}/message`

Send message, wait for full response.

```json
{ "content": "What is my portfolio IRR?" }
```

Returns `{ "user_message": {...}, "assistant_message": {...} }`.

### `POST /ralph/conversations/{id}/stream`

Send message, receive SSE stream of `token`, `tool_call`, `done` events.

See [Ralph AI documentation](ralph-ai.md) for full streaming protocol.

---

## Signal Score

**Prefix:** `/signal-score` · **Users:** Ally

### `GET /signal-score/{project_id}`

Latest signal score for a project.

**Response:** overall_score, tier, 6 dimension scores, gaps, strengths, calculated_at.

### `POST /signal-score/{project_id}/calculate`

Trigger recalculation (async Celery task). Returns `{ "task_id": "...", "status": "pending" }`.

### `GET /signal-score/{project_id}/history`

Score history (chronological list of past scores).

### `GET /signal-score/{project_id}/improvement-plan`

Ranked list of action items to improve the score.

---

## Investor Signal Score

**Prefix:** `/investor-signal-score` · **Users:** Investor · **Rate limit:** 10 req/min for calculate

### `GET /investor-signal-score`

Latest score with dimension breakdown.

Dimensions: Financial Capacity (20%), Risk Management (20%), Investment Strategy (15%), Team Experience (15%), ESG Commitment (15%), Platform Readiness (15%).

### `POST /investor-signal-score/calculate`

Trigger recalculation.

### `GET /investor-signal-score/history`

Score history.

### `GET /investor-signal-score/improvement-plan`

Ranked improvement actions.

### `GET /investor-signal-score/factors`

Positive and negative factors affecting the score.

### `GET /investor-signal-score/benchmark`

Percentile ranking vs. all investors on platform.

### `GET /investor-signal-score/top-matches`

Top matching projects based on investor mandate.

### `GET /investor-signal-score/details/{dimension}`

Per-criterion breakdown for a dimension.

### `POST /investor-signal-score/deal-alignment`

Alignment score with a specific project.

```json
{ "project_id": "uuid" }
```

---

## Matching

**Prefix:** `/matching` · **Users:** Both

### `GET /matching/recommendations`

Recommendations for the current org (investors see projects, allies see investors).

**Query:** `limit`, `min_score`

### `GET /matching/matches`

Existing matches with status.

**Query:** `status` (suggested, viewed, interested, intro_requested, engaged, passed, declined)

### `POST /matching/matches/{id}/status`

Update match status.

```json
{ "status": "interested", "notes": "Good fit for our mandate" }
```

### `POST /matching/intro-request/{match_id}`

Request introduction.

---

## Valuation

**Prefix:** `/valuation` · **Users:** Both

### `GET /valuation/{project_id}`

Latest valuation.

### `POST /valuation` → `201`

```json
{
  "project_id": "uuid",
  "method": "dcf",
  "assumptions": { "discount_rate": 0.12, "terminal_growth": 0.02 },
  "estimated_value": 25000000,
  "currency": "USD"
}
```

### `GET /valuation/{project_id}/history`

Valuation history.

### `PUT /valuation/{valuation_id}/status`

Update status (`draft → reviewed → approved → superseded`).

---

## Equity Calculator

**Prefix:** `/equity-calculator` · **Users:** Both

### `POST /equity-calculator/scenarios`

Run dilution model.

```json
{
  "project_id": "uuid",
  "rounds": [
    { "name": "Series A", "pre_money_valuation": 10000000, "investment": 2000000 }
  ],
  "security_type": "common_equity",
  "anti_dilution": "broad_based"
}
```

### `GET /equity-calculator/scenarios/{id}`

Scenario result with ownership table and return projections.

---

## Capital Efficiency

**Prefix:** `/capital-efficiency` · **Users:** Both

### `GET /capital-efficiency/{project_id}`

Burn rate, runway, deployment efficiency, use-of-proceeds breakdown.

### `POST /capital-efficiency/report` → `202`

Generate detailed capital efficiency report.

---

## Risk

**Prefix:** `/risk` · **Users:** Both

### `GET /risk/assessments`

**Query:** `entity_id`, `entity_type`, `risk_type`, `severity`

### `POST /risk/assessments` → `201`

Create risk assessment.

```json
{
  "entity_id": "uuid",
  "entity_type": "project",
  "risk_type": "regulatory",
  "severity": "high",
  "probability": "possible",
  "description": "...",
  "mitigation_plan": "..."
}
```

### `PUT /risk/assessments/{id}`

### `GET /risk/mitigation/{entity_id}`

Mitigation strategies for all risks on an entity.

### `GET /risk/compliance`

Compliance monitoring status.

---

## Legal

**Prefix:** `/legal` · **Users:** Both

### `GET /legal/documents`

**Query:** `project_id`, `document_type`, `status`

### `POST /legal/documents` → `201`

Create legal document (draft).

```json
{
  "project_id": "uuid",
  "document_type": "term_sheet",
  "counterparty_name": "Investor Corp",
  "key_terms": { ... }
}
```

### `GET /legal/documents/{id}`

### `PUT /legal/documents/{id}`

### `PUT /legal/documents/{id}/status`

Advance status (`draft → review → sent → signed → executed → expired`).

### `POST /legal/documents/{id}/ai-review`

AI-powered document review — extracts key clauses, flags risks.

---

## Reporting

**Prefix:** `/reports` · **Users:** Both

### `GET /reports`

**Query:** `report_type`, `status`, `page`, `page_size`

### `POST /reports` → `202`

Trigger async report generation.

```json
{
  "report_type": "esg",
  "title": "Q1 ESG Report",
  "frequency": "quarterly",
  "entity_id": "uuid",
  "format": "pdf"
}
```

Returns `{ "report_id": "uuid", "status": "pending" }`.

### `GET /reports/{id}`

Poll status and get download URL when complete.

### `DELETE /reports/{id}` → `204`

---

## Marketplace

**Prefix:** `/marketplace` · **Users:** Both

### `GET /marketplace/listings`

**Query:** `listing_type`, `sector`, `geography`, `ticket_min`, `ticket_max`, `visibility`, `page`, `page_size`

### `POST /marketplace/listings` → `201`

```json
{
  "project_id": "uuid",
  "listing_type": "equity_sale",
  "headline": "50MW Solar — Nevada",
  "ticket_size_min": 1000000,
  "ticket_size_max": 10000000,
  "visibility": "qualified_only"
}
```

### `GET /marketplace/listings/{id}`

### `PUT /marketplace/listings/{id}`

### `DELETE /marketplace/listings/{id}` → `204`

---

## Deal Intelligence

**Prefix:** `/deal-intelligence` · **Users:** Both

### `GET /deal-intelligence/pipeline`

Deal flow pipeline overview.

### `POST /deal-intelligence/term-sheet`

Generate term sheet from project and investment parameters.

### `GET /deal-intelligence/due-diligence/{project_id}`

Due diligence checklist with completion status.

---

## Tax Credits

**Prefix:** `/tax-credits` · **Users:** Ally

### `GET /tax-credits/{project_id}`

Tax credit eligibility summary (IRA, ITC, PTC, NMTC, etc.).

### `POST /tax-credits/{project_id}/analyse`

Run eligibility analysis.

### `PUT /tax-credits/{credit_id}/status`

Update qualification status (`potential → qualified → claimed → transferred`).

---

## Carbon Credits

**Prefix:** `/carbon-credits` · **Users:** Ally

### `GET /carbon-credits/{project_id}`

Carbon credit estimates and verification status.

### `POST /carbon-credits/{project_id}/estimate`

Run estimation model.

### `PUT /carbon-credits/{credit_id}/status`

Update verification status (`estimated → submitted → verified → issued → retired`).

---

## Impact

**Prefix:** `/impact` · **Users:** Both

### `GET /impact/metrics`

**Query:** `project_id`, `portfolio_id`

SDG alignment and impact metrics.

### `POST /impact/metrics` → `201`

Record an impact metric.

### `GET /impact/sdg-alignment/{entity_id}`

SDG contribution breakdown.

---

## Investor Personas

**Prefix:** `/investor-personas` · **Users:** Investor

### `GET /investor-personas`

List investor personas (mandate profiles).

### `POST /investor-personas` → `201`

```json
{
  "name": "Growth Impact Fund",
  "strategy": "growth",
  "sectors": ["solar", "wind"],
  "geographies": ["US", "EU"],
  "ticket_min": 1000000,
  "ticket_max": 20000000,
  "stage_preferences": ["development", "construction_ready"]
}
```

### `GET /investor-personas/{id}`

### `PUT /investor-personas/{id}`

### `DELETE /investor-personas/{id}` → `204`

---

## Board Advisor

**Prefix:** `/board-advisor` · **Users:** Both

### `GET /board-advisor/advisors`

**Query:** `expertise`, `sector`, `availability`

### `POST /board-advisor/advisors` → `201`

Create advisor profile.

### `GET /board-advisor/advisors/{id}`

### `POST /board-advisor/engagements` → `201`

Create engagement (application).

```json
{ "advisor_id": "uuid", "project_id": "uuid", "compensation_type": "equity" }
```

### `PUT /board-advisor/engagements/{id}/status`

Advance status (`pending → accepted | rejected → active → completed`).

---

## Settings

**Prefix:** `/settings` · **Users:** Both

### `GET /settings/organisation`

Organisation settings (name, logo, subscription tier, preferences).

### `PUT /settings/organisation`

Update org settings.

### `GET /settings/users`

List org members (requires manager+).

### `POST /settings/users/invite`

Invite a new user.

```json
{ "email": "alice@example.com", "role": "analyst" }
```

### `PUT /settings/users/{id}/role`

Change user role. Requires admin.

### `DELETE /settings/users/{id}` → `204`

Deactivate user. Requires admin.

---

## Onboarding

**Prefix:** `/onboarding` · **Users:** Both

### `GET /onboarding/status`

Onboarding step completion status.

### `PUT /onboarding/steps/{step}`

Mark a step complete.

---

## Collaboration

**Prefix:** `/collaboration` · **Users:** Both

### `GET /collaboration/comments`

**Query:** `entity_id`, `entity_type`

### `POST /collaboration/comments` → `201`

```json
{ "entity_id": "uuid", "entity_type": "project", "content": "Looking good!" }
```

### `PUT /collaboration/comments/{id}`

### `DELETE /collaboration/comments/{id}` → `204`

### `GET /collaboration/tasks`

**Query:** `entity_id`, `assigned_to`, `status`

### `POST /collaboration/tasks` → `201`

### `PUT /collaboration/tasks/{id}`

---

## Ecosystem

**Prefix:** `/ecosystem` · **Users:** Both

### `GET /ecosystem/partners`

Partner network for the org.

### `POST /ecosystem/partners` → `201`

### `GET /ecosystem/map`

Visual ecosystem map data (nodes + edges).

---

## Value Quantifier

**Prefix:** `/value-quantifier` · **Users:** Both

### `POST /value-quantifier/calculate`

Calculate quantitative impact and value creation metrics.

```json
{ "project_id": "uuid", "scenarios": ["base", "upside", "downside"] }
```

### `GET /value-quantifier/results/{id}`

---

## Development OS

**Prefix:** `/development-os` · **Users:** Ally

### `GET /development-os/{project_id}/timeline`

Project development lifecycle with phases and blockers.

### `POST /development-os/{project_id}/milestones`

Add development milestone.

### `GET /development-os/{project_id}/readiness`

Construction readiness assessment.

---

## Tokenization

**Prefix:** `/tokenization` · **Users:** Both

### `GET /tokenization/{project_id}`

Token economics and blockchain integration status.

### `POST /tokenization` → `201`

Create tokenization setup.

```json
{ "project_id": "uuid", "token_name": "SUN", "total_supply": 1000000, "standard": "ERC-20" }
```

### `PUT /tokenization/{id}/status`

---

## Admin

**Prefix:** `/admin` · **Users:** `OrgType.ADMIN` only

> All endpoints require both `OrgType.ADMIN` and `UserRole.ADMIN`. Regular org admins cannot access these.

### `GET /admin/organizations`

All orgs across the platform.

**Query:** `search`, `status`, `org_type`, `tier`, `page`, `page_size`

### `PUT /admin/organizations/{id}/status`

Activate or suspend a subscription.

```json
{ "status": "suspended", "reason": "Payment overdue" }
```

### `PUT /admin/organizations/{id}/tier`

Change subscription tier.

```json
{ "tier": "enterprise" }
```

### `GET /admin/users`

All users across all orgs.

**Query:** `search`, `org_id`, `role`, `page`, `page_size`

### `PUT /admin/users/{id}/status`

Activate or deactivate a user.

### `GET /admin/analytics`

Platform-wide statistics (total orgs by type/status, users by role, content counts).

### `GET /admin/ai-costs`

Token usage breakdown.

**Query:** `days=30`

Returns usage by agent, model, and org.

### `GET /admin/audit-logs`

Searchable immutable audit trail.

**Query:** `org_id`, `user_id`, `action`, `resource`, `date_from`, `date_to`, `page`, `page_size`

### `GET /admin/system-health`

Live health check: DB ping latency, Redis ping latency, AI Gateway `/health` status.
