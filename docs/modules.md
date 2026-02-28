# Modules Reference

SCR Platform has 29 feature modules split across two user types. Each module follows the same structure: `router.py`, `service.py`, `schemas.py`, optional `tasks.py`.

---

## User Types

| Type | Description | Org Type |
|------|-------------|----------|
| **Ally** | Impact project developers who create and fundraise for projects | `ALLY` |
| **Investor** | Investment funds that discover, evaluate, and invest in projects | `INVESTOR` |
| **Admin** | SCR platform administrators with cross-org visibility | `ADMIN` |

---

## Core Platform

### Projects

**Route prefix:** `/projects`
**Users:** Ally
**Purpose:** Central entity for impact projects — lifecycle management from concept to operational.

Key features:
- Full CRUD with soft delete
- Milestones and budget items
- Status workflow: `draft → active → fundraising → funded → construction → operational → archived`
- Project stage: `concept → pre_development → development → construction_ready → under_construction → operational`
- Publish/unpublish control
- Project statistics aggregation

Key endpoints:
- `GET /projects` — paginated list with filters (type, status, stage)
- `POST /projects` — create project
- `GET /projects/{id}` — detail with milestones and budget
- `PATCH /projects/{id}` — update
- `POST /projects/{id}/publish` — publish to marketplace
- `GET /projects/{id}/stats` — KPI summary

---

### Portfolio

**Route prefix:** `/portfolio`
**Users:** Investor
**Purpose:** Fund and holding management for investor portfolios.

Key features:
- Multiple portfolios per organisation
- Fund metadata (SFDR classification, strategy, AUM)
- Holdings linked to projects
- Portfolio-level metrics and aggregation
- Risk assessment per holding

Key endpoints:
- `GET /portfolio` — list portfolios
- `GET /portfolio/{id}` — detail with holdings
- `POST /portfolio/{id}/holdings` — add holding
- `GET /portfolio/metrics` — aggregate performance

---

### Data Room

**Route prefix:** `/dataroom`
**Users:** Both
**Purpose:** Secure document storage with access control, AI extraction, and audit trail.

Key features:
- Document upload → S3 pre-signed URLs
- File type whitelist: `pdf, docx, xlsx, pptx, csv, jpg, png`
- 100 MB size limit per document
- SHA-256 integrity verification
- AI text extraction (Claude Sonnet 4 via gateway)
- NLP extraction types: KPI, clause, deadline, financial, classification, summary
- Per-document access log (view/download/share/print)
- Role-based document visibility

---

### Notifications

**Route prefix:** `/notifications`
**Users:** Both
**Purpose:** In-app notification delivery with SSE real-time push.

Types: `info`, `warning`, `action_required`, `mention`, `system`

Delivered via:
- SSE stream (`GET /notifications/stream`)
- REST read/dismiss endpoints

---

### Settings

**Route prefix:** `/settings`
**Users:** Both
**Purpose:** Organisation and user preference management.

---

### Onboarding

**Route prefix:** `/onboarding`
**Users:** Both
**Purpose:** Guided first-run experience for new organisations.

---

## AI Modules

### Ralph AI (Conversational Agent)

**Route prefix:** `/ralph`
**Users:** Both
**Purpose:** Persistent conversational AI analyst with 19 domain-specific tools.

See [Ralph AI documentation](ralph-ai.md) for full architecture and tool reference.

Key endpoints:
- `POST /ralph/conversations` — start conversation
- `GET /ralph/conversations` — list conversations
- `GET /ralph/conversations/{id}` — conversation with messages
- `DELETE /ralph/conversations/{id}` — delete
- `POST /ralph/conversations/{id}/message` — send message (sync)
- `POST /ralph/conversations/{id}/stream` — send message (SSE streaming)

---

### Signal Score (Project)

**Route prefix:** `/signal-score`
**Users:** Ally
**Purpose:** AI-powered project readiness score across six dimensions.

Dimensions: Financial Readiness, Legal & Compliance, Technical Feasibility, ESG Impact, Market Fit, Team Capability

Score range: 0–100
Calculation: Weighted average of dimension scores, stored in `signal_scores` table
Calculation is triggered by user action and runs as a Celery task.

---

### Investor Signal Score

**Route prefix:** `/investor-signal-score`
**Users:** Investor
**Purpose:** Investor readiness and quality score across six dimensions.

Dimensions: Financial Capacity (20%), Risk Management (20%), Investment Strategy (15%), Team Experience (15%), ESG Commitment (15%), Platform Readiness (15%)

Key endpoints:
- `GET /investor-signal-score` — latest score
- `POST /investor-signal-score/calculate` — trigger recalculation
- `GET /investor-signal-score/history` — score history
- `GET /investor-signal-score/improvement-plan` — ranked action items
- `GET /investor-signal-score/factors` — positive/negative factors
- `GET /investor-signal-score/benchmark` — percentile vs. platform
- `GET /investor-signal-score/top-matches` — best matching projects
- `GET /investor-signal-score/details/{dimension}` — per-criterion breakdown
- `POST /investor-signal-score/deal-alignment` — alignment with specific project

---

### Matching

**Route prefix:** `/matching`
**Users:** Both
**Purpose:** AI-powered investor ↔ project compatibility matching.

Algorithm considers: investment mandate alignment, sector, geography, ticket size, ESG requirements, stage preference.

Match statuses: `suggested → viewed → interested → intro_requested → engaged → passed | declined`

---

### Deal Intelligence

**Route prefix:** `/deal-intelligence`
**Users:** Both
**Purpose:** Deal flow analysis, term sheet generation, and due diligence checklists.

---

### Reporting

**Route prefix:** `/reports`
**Users:** Both
**Purpose:** Automated report generation (performance, ESG, compliance, portfolio, project).

Report types: `performance`, `esg`, `compliance`, `portfolio`, `project`, `custom`
Frequencies: `daily`, `weekly`, `biweekly`, `monthly`, `quarterly`, `annually`
Generation: async Celery task, status polling via `GET /reports/{id}`

---

## Financial Modules

> All financial calculations use deterministic Python arithmetic — never LLM generation.

### Valuation

**Route prefix:** `/valuations`
**Users:** Both
**Purpose:** Project valuation using multiple methods.

Methods: DCF, Comparables, Replacement Cost, Book Value, Market Value, Blended

Statuses: `draft → reviewed → approved → superseded`

Key response fields: `enterprise_value`, `equity_value`, `method`, `status`, `version`, `valued_at` — all at top level (not nested under a `result` key).

The `POST /valuations/{id}/report` endpoint sets `generated_by` from `current_user.user_id`; the field is non-nullable so the user must be authenticated.

---

### Equity Calculator

**Route prefix:** `/equity-calculator`
**Users:** Both
**Purpose:** Equity dilution modelling and return scenario analysis.

Security types: `common_equity`, `preferred_equity`, `convertible_note`, `SAFE`, `revenue_share`
Anti-dilution: `none`, `broad_based`, `narrow_based`, `full_ratchet`

---

### Capital Efficiency

**Route prefix:** `/capital-efficiency`
**Users:** Both
**Purpose:** Burn rate, runway, and capital deployment efficiency metrics.

Key response fields: `platform_efficiency_score`, `total_savings`, `due_diligence_savings`, `moic`, `irr`, `dpi`, `tvpi`

---

### Tax Credits

**Route prefix:** `/tax-credits`
**Users:** Ally
**Purpose:** US tax credit eligibility analysis (IRA, ITC, PTC, NMTC, etc.).

Qualification statuses: `potential → qualified → claimed → transferred`

---

### Carbon Credits

**Route prefix:** `/carbon-credits`
**Users:** Ally
**Purpose:** Carbon credit estimation, verification tracking, and retirement registry.

Verification statuses: `estimated → submitted → verified → issued → retired`

---

## Risk & Compliance

### Risk

**Route prefix:** `/risk`
**Users:** Both
**Purpose:** Risk assessment, mitigation tracking, and compliance monitoring.

Risk types: `market`, `credit`, `operational`, `regulatory`, `climate`, `concentration`, `counterparty`, `liquidity`
Severity: `low`, `medium`, `high`, `critical`
Probability: `unlikely`, `possible`, `likely`, `very_likely`

---

### Legal

**Route prefix:** `/legal`
**Users:** Both
**Purpose:** Legal document drafting, review, and lifecycle management.

Document types: `term_sheet`, `subscription_agreement`, `SPV_incorporation`, `NDA`, `side_letter`, `amendment`
Statuses: `draft → review → sent → signed → executed → expired`

---

## Market Modules

### Marketplace

**Route prefix:** `/marketplace`
**Users:** Both
**Purpose:** Secondary market for deal listing, discovery, and transaction processing.

Listing types: `equity_sale`, `debt_sale`, `co_investment`, `carbon_credit`
Visibility: `public`, `qualified_only`, `invite_only`

---

### Investor Personas

**Route prefix:** `/investor-personas`
**Users:** Investor
**Purpose:** Structured investor profile creation for mandate definition.

Strategies: `conservative`, `moderate`, `growth`, `aggressive`, `impact_first`

> **Note:** Fields like `preferred_asset_types`, `target_geographies`, `preferred_stages` expect plain `list[str]` — not `{"types": [...]}` dict wrappers.

---

### Board Advisor

**Route prefix:** `/board-advisors`
**Users:** Both
**Purpose:** Board advisor discovery, matching, and engagement management.

Compensation: `equity`, `cash`, `pro_bono`, `negotiable`
Application flow: `pending → accepted | rejected → active → completed`

Key endpoints:
- `GET /board-advisors/search` — search advisors by expertise, sector, availability
- `POST /board-advisors/profiles` — create advisor profile
- `POST /board-advisors/applications` — apply to connect with an advisor

---

## Analytics & Intelligence

### Impact

**Route prefix:** `/impact`
**Users:** Both
**Purpose:** SDG alignment, impact metric tracking, and ESG reporting.

---

### Value Quantifier

**Route prefix:** `/value-quantifier`
**Users:** Both
**Purpose:** Quantitative impact and value creation assessment.

---

### Development OS

**Route prefix:** `/development-os`
**Users:** Ally
**Purpose:** Project development lifecycle tooling and milestone tracking.

---

### Ecosystem

**Route prefix:** `/ecosystem`
**Users:** Both
**Purpose:** Ecosystem mapping, partner network, and relationship management.

---

### Tokenization

**Route prefix:** `/tokenization`
**Users:** Both
**Purpose:** Asset tokenization setup, token economics, and blockchain integration.

---

### Collaboration

**Route prefix:** `/collaboration`
**Users:** Both
**Purpose:** Team messaging, commenting, and task management within projects.

---

## Platform Administration

### Admin

**Route prefix:** `/admin`
**Users:** ADMIN org type only
**Purpose:** Platform-level administration — cross-org visibility and management.

> All admin endpoints require `OrgType.ADMIN` + `UserRole.ADMIN`. Regular org admins cannot access these.

Key endpoints:
- `GET /admin/organizations` — all orgs with user counts, searchable + filterable
- `PUT /admin/organizations/{id}/status` — suspend / activate subscription
- `PUT /admin/organizations/{id}/tier` — change tier (foundation/professional/enterprise)
- `GET /admin/users` — all users across all orgs
- `PUT /admin/users/{id}/status` — activate / deactivate user
- `GET /admin/analytics` — platform-wide stats (orgs, users, content counts)
- `GET /admin/ai-costs?days=30` — token usage breakdown by agent, model, org
- `GET /admin/audit-logs` — searchable immutable audit trail
- `GET /admin/system-health` — live service health (DB, Redis, AI Gateway latency)
