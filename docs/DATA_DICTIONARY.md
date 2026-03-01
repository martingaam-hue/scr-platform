# Data Dictionary — SCR Platform v1.0.0

This document describes the key database tables in the SCR Platform, organized by domain. The platform has approximately 113 tables across 50+ Alembic migration revisions, backed by PostgreSQL 16.

**Conventions:**
- All tables have `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` unless noted otherwise.
- Tables that extend `BaseModel` have `id`, `created_at`, `updated_at`, and soft-delete `is_deleted` (where applicable).
- Tables that extend `TimestampedModel` are append-only (no `updated_at`, no soft-delete).
- All `org_id` columns are foreign keys to `organizations.id` and enforce multi-tenant isolation.
- `JSONB` columns store schemaless extension data; documented schemas are the expected format but are not enforced by the database.

---

## Domain: Core

### `organizations`

The top-level tenant entity. Every other table is scoped to an organization.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `name` | VARCHAR(255) | No | Display name |
| `slug` | VARCHAR(255) | No | URL-safe unique identifier |
| `type` | ENUM(`ALLY`, `INVESTOR`, `ADMIN`) | No | Organization type determines available features |
| `logo_url` | VARCHAR(512) | Yes | URL to the org logo (S3 or CDN) |
| `settings` | JSONB | No | Org-level settings (branding, preferences, matching criteria) |
| `subscription_tier` | ENUM(`foundation`, `professional`, `enterprise`) | No | Controls rate limits and feature access |
| `subscription_status` | ENUM(`trial`, `active`, `past_due`, `cancelled`, `suspended`) | No | Billing status |
| `ai_monthly_budget` | NUMERIC | Yes | USD monthly AI spend cap; NULL uses tier default |
| `created_at` | TIMESTAMP | No | Record creation time |
| `updated_at` | TIMESTAMP | No | Last modification time |

**Indexes:** `slug` (unique), `type`

**Relationships:** Parent of `users`, `projects`, `portfolios`, `ai_conversations`, `audit_logs`, and all module tables.

---

### `users`

A human user, always belonging to exactly one organization.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `org_id` | UUID → `organizations` | No | Parent organization |
| `email` | VARCHAR(320) | No | Unique email address |
| `full_name` | VARCHAR(255) | No | Display name |
| `role` | ENUM(`viewer`, `analyst`, `manager`, `admin`) | No | RBAC role within the org |
| `avatar_url` | VARCHAR(512) | Yes | Profile picture URL |
| `preferences` | JSONB | No | User preferences (digest settings, notification opt-outs, theme) |
| `mfa_enabled` | BOOLEAN | No | Whether MFA is configured in Clerk |
| `external_auth_id` | VARCHAR(255) | No | Clerk `user_id` (unique); used for JWT verification |
| `last_login_at` | TIMESTAMP | Yes | Last successful authentication |
| `is_active` | BOOLEAN | No | False = deactivated (soft delete) |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `email` (unique), `external_auth_id` (unique), `(org_id, role)`

---

### `projects`

An impact project created and owned by an `ALLY` organization.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `org_id` | UUID → `organizations` | No | Owning org (must be type ALLY) |
| `name` | VARCHAR(500) | No | Project name |
| `slug` | VARCHAR(500) | No | URL-safe identifier within the org |
| `description` | TEXT | No | Full project description |
| `project_type` | ENUM(`SOLAR`, `WIND`, `STORAGE`, `HYDRO`, `BIOMASS`, ...) | No | Technology type |
| `status` | ENUM(`DRAFT`, `ACTIVE`, `ARCHIVED`, `SUSPENDED`) | No | Lifecycle status |
| `stage` | ENUM(`CONCEPT`, `DEVELOPMENT`, `CONSTRUCTION`, `OPERATIONAL`) | No | Development stage |
| `geography_country` | VARCHAR(100) | No | ISO country code or name |
| `geography_region` | VARCHAR(255) | No | Region or state |
| `geography_coordinates` | JSONB | Yes | `{lat, lng}` for map display |
| `technology_details` | JSONB | Yes | Technology-specific metadata |
| `capacity_mw` | NUMERIC(19,4) | Yes | Nameplate capacity in megawatts |
| `total_investment_required` | NUMERIC(19,4) | No | Target fundraise amount |
| `currency` | CHAR(3) | No | ISO 4217 currency code |
| `target_close_date` | DATE | Yes | Target financial close |
| `cover_image_url` | VARCHAR(512) | Yes | |
| `is_published` | BOOLEAN | No | True = visible on marketplace |
| `published_at` | TIMESTAMP | Yes | When project was first published |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `(org_id, status)`, `status`, `project_type`, `slug`, `geography_country`

**Relationships:** Has `project_milestones`, `project_budget_items`, `signal_scores`, `documents`, `deal_screens`, `qa_questions`, `match_results`.

---

### `project_milestones`

Timeline milestones for a project's development.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `project_id` | UUID → `projects` | No | |
| `name` | VARCHAR(500) | No | Milestone name |
| `description` | TEXT | No | |
| `target_date` | DATE | No | Planned completion date |
| `completed_date` | DATE | Yes | Actual completion date |
| `status` | ENUM(`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`, `DELAYED`) | No | |
| `completion_pct` | INTEGER | No | 0–100 |
| `order_index` | INTEGER | No | Display order |

---

### `project_budget_items`

Line items of a project's capital budget.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `project_id` | UUID → `projects` | No | |
| `category` | VARCHAR(255) | No | e.g. "EPC", "Grid Connection", "Legal" |
| `description` | VARCHAR(1000) | No | |
| `estimated_amount` | NUMERIC(19,4) | No | |
| `actual_amount` | NUMERIC(19,4) | Yes | Populated as expenditure occurs |
| `currency` | CHAR(3) | No | |
| `status` | ENUM(`PLANNED`, `COMMITTED`, `SPENT`) | No | |

---

### `audit_logs`

Immutable, append-only record of all write operations. Never soft-deleted.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `user_id` | UUID → `users` | Yes | NULL for system actions |
| `action` | VARCHAR(100) | No | e.g. `project.created`, `document.deleted` |
| `entity_type` | VARCHAR(100) | No | e.g. `Project`, `Document` |
| `entity_id` | UUID | Yes | ID of the affected entity |
| `changes` | JSONB | Yes | Before/after values for updates |
| `ip_address` | VARCHAR(45) | Yes | Client IP (IPv4 or IPv6) |
| `user_agent` | TEXT | Yes | |
| `timestamp` | TIMESTAMP | No | Write time (indexed) |

**Indexes:** `org_id`, `user_id`, `(entity_type, entity_id)`, `action`, `timestamp`
**Retention:** 365 days (archive candidate — not deleted)

---

## Domain: Signal Score

### `signal_scores`

Each row is one version of a project's AI signal score.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `project_id` | UUID → `projects` | No | |
| `version` | INTEGER | No | Increments with each recalculation |
| `overall_score` | NUMERIC(5,2) | No | Weighted average of dimensions (0–100) |
| `project_viability_score` | NUMERIC(5,2) | Yes | Technical and site feasibility dimension |
| `financial_planning_score` | NUMERIC(5,2) | Yes | Financial model quality dimension |
| `risk_assessment_score` | NUMERIC(5,2) | Yes | Risk identification dimension |
| `team_strength_score` | NUMERIC(5,2) | Yes | Team capability dimension |
| `esg_score` | NUMERIC(5,2) | Yes | Environmental and social impact dimension |
| `status` | ENUM(`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) | No | Calculation status |
| `narrative` | TEXT | Yes | AI-generated score explanation |
| `model_version` | VARCHAR(50) | Yes | AI model used for this score version |
| `triggered_by` | UUID → `users` | Yes | User who requested the recalculation |
| `created_at` | TIMESTAMP | No | Calculation timestamp |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `(org_id, project_id)`, `project_id`, `status`, `(project_id, version)`

---

### `ai_task_logs`

Append-only log of every AI task execution across all modules.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `agent_type` | ENUM(16 values) | No | Which AI feature generated this log |
| `entity_type` | VARCHAR(100) | Yes | e.g. `Project`, `Document` |
| `entity_id` | UUID | Yes | ID of the entity being analyzed |
| `status` | ENUM(`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) | No | |
| `input_data` | JSONB | Yes | Truncated input context (for debugging) |
| `output_data` | JSONB | Yes | Structured AI output |
| `error_message` | TEXT | Yes | Error detail if status = FAILED |
| `model_used` | VARCHAR(100) | Yes | Exact model ID (e.g. `claude-sonnet-4-20250514`) |
| `tokens_input` | INTEGER | Yes | Prompt tokens |
| `tokens_output` | INTEGER | Yes | Completion tokens |
| `cost_usd` | NUMERIC(12,6) | Yes | Calculated cost based on model pricing |
| `triggered_by` | UUID → `users` | Yes | |
| `created_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `agent_type`, `status`, `(entity_type, entity_id)`
**Retention:** 90 days (archive candidate)

---

### `prompt_templates`

Versioned library of prompts for all AI task types, editable by platform admins without deployment.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `task_type` | VARCHAR(100) | No | e.g. `signal_score`, `legal_analysis`, `chat_with_tools` |
| `version` | INTEGER | No | Monotonically increasing per task_type |
| `content` | TEXT | No | The user/human-turn prompt template |
| `system_prompt` | TEXT | Yes | The system prompt |
| `is_active` | BOOLEAN | No | Only one active version per task_type |
| `notes` | TEXT | Yes | Change notes for this version |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Unique constraint:** `(task_type, version)`
**Indexes:** `task_type`, `is_active`

---

### `analysis_extractions`

Cache of AI extraction results for documents. Avoids re-running identical AI tasks on unchanged documents.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `document_id` | UUID → `documents` | No | Source document |
| `extraction_type` | ENUM(`QUALITY_ASSESSMENT`, `RISK_FLAGS`, `DEAL_RELEVANCE`, `COMPLETENESS_CHECK`, `KEY_FIGURES`, `ENTITY_EXTRACTION`, ...) | No | What was extracted |
| `content_hash` | VARCHAR(64) | No | SHA-256 of document text at extraction time |
| `result` | JSONB | No | Structured extraction output |
| `model_used` | VARCHAR(100) | Yes | Model that produced this extraction |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Unique constraint:** `(document_id, extraction_type, content_hash)` — cache key

---

### `ai_feedback`

User thumbs up/down feedback on AI-generated outputs.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `user_id` | UUID → `users` | No | Who gave the feedback |
| `entity_type` | VARCHAR(100) | No | e.g. `SignalScore`, `RiskReport` |
| `entity_id` | UUID | No | The AI output being rated |
| `rating` | SMALLINT | No | 1 = thumbs up, -1 = thumbs down |
| `comment` | TEXT | Yes | Optional free-text feedback |
| `created_at` | TIMESTAMP | No | |

---

## Domain: AI Conversations (Ralph AI)

### `ai_conversations`

A conversation session with Ralph AI.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `user_id` | UUID → `users` | No | Owning user |
| `context_type` | ENUM(`GENERAL`, `PROJECT`, `PORTFOLIO`, `DOCUMENT`, ...) | No | What the conversation is about |
| `context_entity_id` | UUID | Yes | The project/portfolio/document being discussed |
| `title` | VARCHAR(500) | No | Auto-generated conversation title |
| `summary` | TEXT | Yes | AI-generated summary of the conversation |
| `metadata_` | JSONB | Yes | Additional context metadata |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `user_id`, `context_type`, `(user_id, context_type)`

---

### `ai_messages`

Individual messages within a Ralph AI conversation.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `conversation_id` | UUID → `ai_conversations` | No | |
| `role` | ENUM(`user`, `assistant`, `tool`) | No | Message author |
| `content` | TEXT | No | Message text or tool result |
| `model_used` | VARCHAR(100) | Yes | Model for assistant messages |
| `tokens_input` | INTEGER | Yes | |
| `tokens_output` | INTEGER | Yes | |
| `tool_calls` | JSONB | Yes | Tool invocations made in this message |
| `tool_results` | JSONB | Yes | Results returned by tools |
| `created_at` | TIMESTAMP | No | |

**Indexes:** `conversation_id`, `role`

---

## Domain: Data Room

### `documents`

A document uploaded to the data room. Metadata only — file content is in S3.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `project_id` | UUID → `projects` | Yes | Owning project (or portfolio) |
| `portfolio_id` | UUID → `portfolios` | Yes | Owning portfolio |
| `folder_id` | UUID → `document_folders` | Yes | Parent folder |
| `name` | VARCHAR(500) | No | Display name |
| `file_type` | VARCHAR(20) | No | Extension: `pdf`, `xlsx`, etc. |
| `mime_type` | VARCHAR(255) | No | IANA MIME type |
| `s3_key` | VARCHAR(1000) | No | S3 object key |
| `s3_bucket` | VARCHAR(255) | No | S3 bucket name |
| `file_size_bytes` | INTEGER | No | |
| `version` | INTEGER | No | Starts at 1, increments on new version upload |
| `parent_version_id` | UUID → `documents` | Yes | Self-reference for version chain |
| `status` | ENUM(`UPLOADING`, `PROCESSING`, `READY`, `ERROR`) | No | |
| `metadata_` | JSONB | Yes | Additional metadata from extraction |
| `uploaded_by` | UUID → `users` | No | |
| `checksum_sha256` | CHAR(64) | No | File integrity hash |
| `classification` | ENUM(`PUBLIC`, `CONFIDENTIAL`, `RESTRICTED`, `TOP_SECRET`) | Yes | Access control classification |
| `watermark_enabled` | BOOLEAN | No | If true, apply viewer watermark on download |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `project_id`, `portfolio_id`, `folder_id`, `(org_id, status)`, `uploaded_by`

---

### `document_folders`

Hierarchical folder structure for organizing documents.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `project_id` | UUID → `projects` | Yes | |
| `parent_folder_id` | UUID → `document_folders` | Yes | Self-reference for folder hierarchy |
| `name` | VARCHAR(255) | No | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `project_id`, `parent_folder_id`

---

### `document_extractions` (a.k.a. `DocumentExtraction`)

Raw text and AI extractions from a document. One row per extraction pass.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `document_id` | UUID → `documents` | No | |
| `extraction_type` | ENUM | No | Type of extraction (text, summary, entities, etc.) |
| `content` | TEXT | Yes | Raw extracted text for `text` type |
| `result` | JSONB | Yes | Structured result for AI extraction types |
| `page_count` | INTEGER | Yes | Number of pages processed |
| `status` | ENUM(`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) | No | |
| `error_message` | TEXT | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `document_access_logs`

Append-only log of every interaction with a document (view, download, share).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `document_id` | UUID → `documents` | No | |
| `org_id` | UUID → `organizations` | No | The accessing org |
| `user_id` | UUID → `users` | Yes | NULL for anonymous/system access |
| `action` | ENUM(`VIEWED`, `DOWNLOADED`, `SHARED`, `ANNOTATED`, `PRINTED`) | No | |
| `ip_address` | VARCHAR(45) | Yes | |
| `user_agent` | TEXT | Yes | |
| `metadata_` | JSONB | Yes | e.g. page numbers viewed, download format |
| `created_at` | TIMESTAMP | No | Access timestamp |

**Retention:** 365 days (archive candidate)
**Indexes:** `document_id`, `org_id`, `user_id`, `action`

---

### `redaction_jobs`

Tracks a PII-detection and redaction workflow for a single document.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID | No | |
| `document_id` | UUID | No | Source document |
| `created_by` | UUID | Yes | |
| `status` | VARCHAR(20) | No | `pending` → `analyzing` → `review` → `applying` → `done` / `failed` |
| `detected_entities` | JSONB | Yes | List of detected PII entities with type, text, page, confidence, position |
| `approved_redactions` | JSONB | Yes | Subset approved by user for actual redaction |
| `redacted_document_id` | UUID | Yes | New document created after redaction applied |
| `redacted_s3_key` | VARCHAR(1024) | Yes | S3 key for the clean PDF |
| `error_message` | TEXT | Yes | |
| `entity_count` | INTEGER | No | Total entities detected |
| `approved_count` | INTEGER | No | Entities approved for redaction |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `document_annotations`

User annotations on documents (highlights, comments, bookmarks).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `document_id` | UUID → `documents` | No | |
| `user_id` | UUID → `users` | No | Annotation author |
| `type` | ENUM(`HIGHLIGHT`, `COMMENT`, `BOOKMARK`) | No | |
| `page_number` | INTEGER | No | |
| `position` | JSONB | No | `{x, y, width, height}` in PDF coordinates |
| `text` | TEXT | Yes | Comment text or highlighted text |
| `color` | VARCHAR(7) | Yes | Hex color for highlight |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: Portfolio

### `portfolios`

An investment portfolio managed by an `INVESTOR` organization.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | Must be type INVESTOR |
| `name` | VARCHAR(255) | No | |
| `description` | TEXT | Yes | |
| `currency` | CHAR(3) | No | Base currency for NAV reporting |
| `target_size` | NUMERIC(19,4) | Yes | Target fund size |
| `vintage_year` | INTEGER | Yes | Fund vintage year |
| `strategy` | VARCHAR(100) | Yes | e.g. "Infrastructure Debt", "Impact Equity" |
| `status` | ENUM(`ACTIVE`, `CLOSED`, `LIQUIDATING`) | No | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `portfolio_holdings`

A single project investment within a portfolio.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `portfolio_id` | UUID → `portfolios` | No | |
| `org_id` | UUID → `organizations` | No | |
| `project_id` | UUID → `projects` | No | |
| `investment_date` | DATE | No | Date of initial investment |
| `committed_amount` | NUMERIC(19,4) | No | Total commitment |
| `invested_amount` | NUMERIC(19,4) | No | Amount drawn to date |
| `current_value` | NUMERIC(19,4) | Yes | Latest NAV for this holding |
| `currency` | CHAR(3) | No | |
| `ownership_pct` | NUMERIC(7,4) | Yes | Equity ownership percentage |
| `status` | ENUM(`ACTIVE`, `EXITED`, `WRITTEN_OFF`) | No | |
| `exit_date` | DATE | Yes | |
| `exit_proceeds` | NUMERIC(19,4) | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `metric_snapshots`

Daily automated snapshots of all key performance metrics for trending.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `entity_type` | VARCHAR(50) | No | e.g. `Portfolio`, `Holding`, `Project` |
| `entity_id` | UUID | No | |
| `metric_type` | VARCHAR(100) | No | e.g. `nav`, `irr`, `moic`, `signal_score` |
| `value` | NUMERIC(19,6) | No | |
| `currency` | CHAR(3) | Yes | For monetary metrics |
| `snapshot_date` | DATE | No | Date of the snapshot |
| `metadata_` | JSONB | Yes | Additional context |
| `created_at` | TIMESTAMP | No | |

**Unique constraint:** `(entity_id, metric_type, snapshot_date)`

---

### `covenants`

Financial or operational covenants monitored for portfolio holdings.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `holding_id` | UUID → `portfolio_holdings` | No | |
| `name` | VARCHAR(255) | No | e.g. "DSCR >= 1.25x" |
| `metric_name` | VARCHAR(100) | No | Metric being monitored |
| `operator` | VARCHAR(5) | No | `>=`, `<=`, `=` |
| `threshold_breach` | NUMERIC(19,4) | No | Breach threshold value |
| `threshold_warning` | NUMERIC(19,4) | Yes | Warning threshold (earlier alert) |
| `current_value` | NUMERIC(19,4) | Yes | Most recently measured value |
| `status` | ENUM(`OK`, `WARNING`, `BREACH`, `WAIVED`) | No | |
| `last_checked_at` | TIMESTAMP | Yes | |
| `breach_date` | DATE | Yes | When breach first detected |
| `notes` | TEXT | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: Deal Intelligence

### `deal_screens`

AI deal screening report for a project. One per project (updated on re-screen).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `project_id` | UUID → `projects` | No | |
| `status` | ENUM(`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) | No | |
| `recommendation` | ENUM(`PASS`, `REVIEW`, `REJECT`) | Yes | AI recommendation |
| `overall_score` | NUMERIC(5,2) | Yes | Deal screening score (0–100) |
| `rationale` | TEXT | Yes | AI explanation of recommendation |
| `key_strengths` | JSONB | Yes | List of identified strengths |
| `key_risks` | JSONB | Yes | List of identified risks |
| `next_steps` | JSONB | Yes | Suggested due diligence next steps |
| `model_used` | VARCHAR(100) | Yes | |
| `triggered_by` | UUID → `users` | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `investment_memos`

Generated investment memo documents for projects.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `project_id` | UUID → `projects` | No | |
| `deal_screen_id` | UUID → `deal_screens` | Yes | Memo generated from this screen |
| `title` | VARCHAR(500) | No | |
| `content` | TEXT | No | Full memo text (may include markdown) |
| `summary` | TEXT | Yes | Executive summary |
| `sections` | JSONB | Yes | Structured sections with headings and content |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: Matching

### `match_results`

An AI-calculated compatibility match between an investor org and a project.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `investor_org_id` | UUID → `organizations` | No | The investor |
| `ally_org_id` | UUID → `organizations` | No | The project developer |
| `project_id` | UUID → `projects` | No | The matched project |
| `mandate_id` | UUID → `investor_mandates` | Yes | Investor mandate this match is against |
| `overall_score` | INTEGER | No | 0–100 compatibility score |
| `score_breakdown` | JSONB | Yes | Per-dimension scores (geography, sector, stage, deal size, ESG) |
| `status` | ENUM(`SUGGESTED`, `VIEWED`, `INTERESTED`, `DECLINED`, `CONNECTED`, `WITHDRAWN`) | No | Match lifecycle status |
| `initiated_by` | ENUM(`SYSTEM`, `INVESTOR`, `ALLY`) | No | Who initiated the match |
| `investor_notes` | TEXT | No | Investor's private notes |
| `ally_notes` | TEXT | No | Ally's private notes |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `investor_org_id`, `ally_org_id`, `project_id`, `status`, `(investor_org_id, status)`, `(ally_org_id, status)`

---

### `match_messages`

Messages exchanged within a match (between investor and ally).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `match_id` | UUID → `match_results` | No | |
| `sender_id` | UUID → `users` | No | |
| `content` | TEXT | No | |
| `created_at` | TIMESTAMP | No | |

---

## Domain: Webhooks

### `webhook_subscriptions`

A registered webhook endpoint for an organisation.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID | No | |
| `created_by` | UUID → `users` | Yes | |
| `url` | VARCHAR(2048) | No | HTTPS target URL |
| `secret` | VARCHAR(255) | No | Per-subscription HMAC secret (shown only on creation) |
| `events` | JSONB | No | Array of subscribed event type strings |
| `is_active` | BOOLEAN | No | False = auto-disabled after 10 failures |
| `failure_count` | INTEGER | No | Consecutive failure count; resets on success |
| `disabled_reason` | TEXT | Yes | Reason for auto-disable |
| `description` | TEXT | Yes | User-provided label |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `webhook_deliveries`

One row per HTTP delivery attempt for a webhook event.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `subscription_id` | UUID → `webhook_subscriptions` | No | |
| `org_id` | UUID | No | |
| `event_type` | VARCHAR(100) | No | e.g. `signal_score.completed` |
| `payload` | JSONB | No | Full event payload delivered |
| `status` | VARCHAR(20) | No | `pending`, `delivered`, `failed`, `retrying` |
| `response_status_code` | INTEGER | Yes | HTTP response code from target |
| `response_body` | TEXT | Yes | First 1000 chars of response |
| `attempts` | INTEGER | No | Total delivery attempts |
| `next_retry_at` | TIMESTAMP | Yes | Scheduled retry time |
| `delivered_at` | TIMESTAMP | Yes | Time of first successful delivery |
| `error_message` | TEXT | Yes | Last error description |
| `created_at` | TIMESTAMP | No | |

**Retention:** 30 days for delivered deliveries

---

## Domain: CRM Integration

### `crm_connections`

Stores OAuth credentials and configuration for a CRM provider connection.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `provider` | VARCHAR(20) | No | `hubspot` or `salesforce` |
| `access_token` | TEXT | No | Fernet-encrypted OAuth access token |
| `refresh_token` | TEXT | Yes | Fernet-encrypted OAuth refresh token |
| `token_expires_at` | TIMESTAMP | Yes | When the access token expires |
| `portal_id` | VARCHAR(100) | Yes | HubSpot portal ID |
| `instance_url` | VARCHAR(500) | Yes | Salesforce instance URL |
| `field_mappings` | JSONB | No | CRM field → SCR field mapping config |
| `sync_frequency` | VARCHAR(20) | No | `15min`, `hourly`, `daily` |
| `sync_direction` | VARCHAR(20) | No | `push`, `pull`, `bidirectional` |
| `last_sync_at` | TIMESTAMP | Yes | |
| `is_active` | BOOLEAN | No | False = credentials expired or revoked |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `crm_sync_logs`

Append-only log of individual sync operations.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `connection_id` | UUID → `crm_connections` | No | |
| `direction` | VARCHAR(10) | No | `push` or `pull` |
| `entity_type` | VARCHAR(50) | No | e.g. `Project`, `Deal`, `Contact` |
| `scr_entity_id` | UUID | Yes | SCR record ID |
| `crm_entity_id` | VARCHAR(100) | Yes | CRM record ID |
| `status` | VARCHAR(20) | No | `success`, `failed`, `skipped` |
| `error_message` | TEXT | Yes | |
| `records_processed` | INTEGER | No | |
| `created_at` | TIMESTAMP | No | |

---

## Domain: Q&A Workflow

### `qa_questions`

A due diligence question from an investor to a project team.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | The asking investor org |
| `deal_room_id` | UUID → `deal_rooms` | Yes | Associated deal room |
| `project_id` | UUID → `projects` | No | Project being asked about |
| `question_number` | INTEGER | No | Sequential number within project |
| `question` | TEXT | No | Question text |
| `category` | VARCHAR(50) | No | e.g. `financial`, `legal`, `technical`, `esg` |
| `priority` | VARCHAR(20) | No | `urgent`, `high`, `normal`, `low` |
| `asked_by` | UUID → `users` | No | |
| `assigned_to` | UUID → `users` | Yes | Project team member responsible |
| `assigned_team` | VARCHAR(50) | Yes | Team category |
| `status` | VARCHAR(30) | No | `open`, `in_progress`, `answered`, `closed` |
| `sla_deadline` | TIMESTAMP | Yes | Response deadline |
| `answered_at` | TIMESTAMP | Yes | When the final answer was submitted |
| `sla_breached` | BOOLEAN | No | True if answered after deadline |
| `linked_documents` | UUID[] | Yes | Documents referenced in the question |
| `tags` | TEXT[] | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Indexes:** `org_id`, `project_id`, `(org_id, project_id)`, `status`, `(project_id, status)`

---

### `qa_answers`

An answer submitted to a Q&A question (one question may have multiple answers/revisions).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `question_id` | UUID → `qa_questions` | No | |
| `answered_by` | UUID → `users` | No | |
| `content` | TEXT | No | Answer text |
| `linked_documents` | UUID[] | Yes | Supporting documents |
| `is_final` | BOOLEAN | No | The authoritative answer (replaces drafts) |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: Gamification

### `badges`

Platform-defined badge definitions (seeded at deployment, not user-created).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `slug` | VARCHAR(100) | No | Unique machine key |
| `name` | VARCHAR(255) | No | |
| `description` | TEXT | Yes | |
| `icon` | VARCHAR(20) | Yes | Emoji or icon name |
| `category` | VARCHAR(50) | No | `onboarding`, `data_room`, `signal_score`, `matching`, `certification` |
| `criteria` | JSONB | No | Machine-readable criteria for automatic award |
| `points` | INTEGER | No | XP points awarded |
| `rarity` | VARCHAR(20) | No | `common`, `uncommon`, `rare`, `epic`, `legendary` |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `user_badges`

Record of a badge earned by a user, optionally scoped to a project.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `user_id` | UUID → `users` | No | |
| `project_id` | UUID → `projects` | Yes | Project context (NULL for org-wide badges) |
| `badge_id` | UUID → `badges` | No | |
| `created_at` | TIMESTAMP | No | Award timestamp |

**Unique constraint:** `(user_id, project_id, badge_id)` — prevents duplicate awards

---

### `improvement_quests`

AI-generated improvement quests for a project, guiding users toward higher scores.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `project_id` | UUID → `projects` | No | |
| `title` | VARCHAR(255) | No | Quest title |
| `description` | TEXT | Yes | Full quest description |
| `action_type` | VARCHAR(50) | No | `upload_document`, `complete_section`, `add_team_member`, `improve_dimension` |
| `target_dimension` | VARCHAR(100) | Yes | Signal score dimension targeted |
| `estimated_score_impact` | INTEGER | No | Projected score improvement |
| `reward_badge_id` | UUID → `badges` | Yes | Badge awarded on completion |
| `status` | VARCHAR(20) | No | `active`, `completed`, `expired` |
| `completed_at` | TIMESTAMP | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: External Data Connectors

### `data_connectors`

Platform-level catalog of available third-party data connectors.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `name` | VARCHAR(100) | No | Machine key (unique) |
| `display_name` | VARCHAR(255) | No | |
| `category` | VARCHAR(50) | No | `market_data`, `esg`, `energy`, `company`, `weather` |
| `description` | TEXT | Yes | |
| `base_url` | VARCHAR(500) | Yes | |
| `auth_type` | VARCHAR(20) | No | `api_key`, `oauth2`, `basic`, `none` |
| `is_available` | BOOLEAN | No | False = connector disabled platform-wide |
| `pricing_tier` | VARCHAR(20) | No | `free`, `professional`, `enterprise` |
| `rate_limit_per_minute` | INTEGER | No | |
| `documentation_url` | VARCHAR(500) | Yes | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

### `org_connector_configs`

Per-organisation enablement and credentials for a connector.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID | No | |
| `connector_id` | UUID → `data_connectors` | No | |
| `is_enabled` | BOOLEAN | No | |
| `api_key_encrypted` | VARCHAR(1000) | Yes | Fernet-encrypted API key |
| `config` | JSONB | No | Connector-specific settings |
| `last_sync_at` | TIMESTAMP | Yes | |
| `last_error` | VARCHAR(1000) | Yes | |
| `total_calls_this_month` | INTEGER | No | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Unique constraint:** `(org_id, connector_id)`

---

### `data_fetch_logs`

Immutable log of each API call made through a connector.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID | No | |
| `connector_id` | UUID → `data_connectors` | No | |
| `endpoint` | VARCHAR(500) | Yes | Specific API endpoint called |
| `status_code` | INTEGER | Yes | HTTP response code |
| `response_time_ms` | INTEGER | Yes | |
| `error_message` | VARCHAR(1000) | Yes | |
| `created_at` | TIMESTAMP | No | |

---

## Domain: Blockchain Audit

### `blockchain_records`

SHA-256 hash and Polygon anchoring record for a document.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `document_id` | UUID → `documents` | No | |
| `document_hash` | CHAR(64) | No | SHA-256 of the document bytes |
| `merkle_root` | CHAR(64) | Yes | Merkle root of the batch |
| `transaction_hash` | VARCHAR(66) | Yes | Polygon transaction hash |
| `block_number` | BIGINT | Yes | Block number on Polygon |
| `anchored_at` | TIMESTAMP | Yes | Time of blockchain confirmation |
| `status` | VARCHAR(20) | No | `pending`, `submitted`, `confirmed`, `failed` |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: API Keys

### `api_keys`

API keys for programmatic access.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `created_by` | UUID → `users` | No | |
| `name` | VARCHAR(255) | No | User-provided label |
| `key_hash` | VARCHAR(64) | No | SHA-256 of the plaintext key (unique) |
| `key_prefix` | VARCHAR(8) | No | First 8 chars of key for identification (e.g. `scr_a8f3`) |
| `scopes` | JSONB | No | Array of allowed scope strings |
| `rate_limit_override` | INTEGER | Yes | Custom req/min limit (NULL = org tier default) |
| `expires_at` | TIMESTAMP | Yes | Expiry (NULL = never expires) |
| `last_used_at` | TIMESTAMP | Yes | |
| `is_active` | BOOLEAN | No | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: Feature Flags

### `feature_flags`

Per-org feature toggle with optional configuration.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `feature_key` | VARCHAR(100) | No | Machine key (e.g. `blockchain_audit`) |
| `is_enabled` | BOOLEAN | No | |
| `config` | JSONB | Yes | Feature-specific configuration |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

**Unique constraint:** `(org_id, feature_key)`

---

## Domain: White-Label / Custom Domains

### `custom_domains`

Custom domain mapping for white-label partners.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `domain` | VARCHAR(255) | No | The custom domain (e.g. `app.partner.com`) |
| `ssl_status` | VARCHAR(20) | No | `PENDING`, `ACTIVE`, `FAILED` |
| `acm_certificate_arn` | VARCHAR(500) | Yes | ARN of the ACM cert |
| `is_active` | BOOLEAN | No | |
| `created_at` | TIMESTAMP | No | |
| `updated_at` | TIMESTAMP | No | |

---

## Domain: Data Lineage

### `lineage_records`

Source chain tracking for computed values.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `entity_type` | VARCHAR(100) | No | The computed entity (e.g. `SignalScore`) |
| `entity_id` | UUID | No | |
| `source_type` | VARCHAR(100) | No | Source entity type (e.g. `Document`) |
| `source_id` | UUID | No | Source entity ID |
| `contribution` | VARCHAR(100) | Yes | How the source contributed |
| `created_at` | TIMESTAMP | No | |

---

## Domain: Source Citations

### `citations`

Source citations on AI-generated outputs (`[1]`, `[2]` style references).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | |
| `org_id` | UUID → `organizations` | No | |
| `ai_output_type` | VARCHAR(100) | No | What AI output this citation belongs to |
| `ai_output_id` | UUID | No | |
| `citation_number` | INTEGER | No | Sequential citation number in the output |
| `document_id` | UUID → `documents` | Yes | Source document |
| `page_number` | INTEGER | Yes | Specific page in document |
| `excerpt` | TEXT | Yes | Quoted text from the source |
| `created_at` | TIMESTAMP | No | |

---

## Table Count Summary

| Domain | Approximate Table Count |
|--------|------------------------|
| Core (orgs, users, projects, audit) | 6 |
| Signal Score & AI Infrastructure | 8 |
| Data Room & Documents | 8 |
| Portfolio & Covenants | 7 |
| Deal Intelligence | 4 |
| Matching & Warm Intros | 4 |
| Webhooks | 2 |
| CRM Integration | 3 |
| Q&A Workflow | 2 |
| Gamification | 3 |
| Ralph AI Conversations | 2 |
| Connectors & External Data | 4 |
| Blockchain Audit | 1 |
| API Keys | 1 |
| Feature Flags | 1 |
| Custom Domains / White-label | 1 |
| Data Lineage & Citations | 2 |
| Reporting, Legal, Risk, ESG, Valuation, Carbon, Certification, Marketplace, Insurance, Backtesting, Expert Insights, Annotations, etc. | ~54 |
| **Total** | **~113** |

---

## Key Indexes Summary

The following composite indexes exist for performance on the most common query patterns:

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| `ix_projects_org_id_status` | `projects` | `org_id, status` | Project list by org + status filter |
| `ix_match_results_investor_status` | `match_results` | `investor_org_id, status` | Investor's match inbox |
| `ix_match_results_ally_status` | `match_results` | `ally_org_id, status` | Ally's match inbox |
| `ix_qa_questions_org_project` | `qa_questions` | `org_id, project_id` | Q&A list per investor+project |
| `ix_qa_questions_project_status` | `qa_questions` | `project_id, status` | Open questions per project |
| `ix_ai_task_logs_entity` | `ai_task_logs` | `entity_type, entity_id` | AI history per entity |
| `ix_users_org_id_role` | `users` | `org_id, role` | RBAC queries |
| `uq_prompt_task_version` | `prompt_templates` | `task_type, version` | Unique prompt version per task |
| `uq_user_project_badge` | `user_badges` | `user_id, project_id, badge_id` | Prevent duplicate badge awards |
