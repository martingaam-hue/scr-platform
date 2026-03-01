# SCR Platform — Complete Blueprint v2

> **Single source of truth for the entire SCR Platform.**
> Generated: 2026-03-01 | Scan method: live codebase traversal — no guessing.
> Replaces all previous blueprint documents.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Implementation Status](#2-implementation-status)
3. [Database Inventory](#3-database-inventory)
4. [API Endpoint Reference](#4-api-endpoint-reference)
5. [Frontend Pages](#5-frontend-pages)
6. [AI Integration](#6-ai-integration)
7. [External Services & Infrastructure](#7-external-services--infrastructure)
8. [Gap Analysis](#8-gap-analysis)
9. [Recommended Improvements](#9-recommended-improvements)
10. [Completion Dashboard](#10-completion-dashboard)

---

## Changelog

| Date | Version | Summary |
|------|---------|---------|
| 2026-03-01 | v2.0 | Full codebase scan — 70+ modules, 71 frontend pages, 55 migrations, all services |
| Prior | v1.x | Partial blueprints (superseded) |

---

## 1. Architecture Overview

### 1.1 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USERS (Browser)                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Next.js 14 Frontend  (port 3000)                        │
│   App Router · TypeScript · Tailwind · React Query · Zustand        │
│                                                                      │
│   71 pages · 86 lib hooks · 29 components · 5 Zustand stores        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ REST /v1/*
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                FastAPI Backend  (port 8000)                          │
│                                                                      │
│   70+ modules · 150+ endpoints · 6 middleware layers                │
│   Clerk JWT auth · RBAC · Multi-tenant (org_id)                     │
│                                                                      │
│   Middleware stack:                                                  │
│   CORS → Audit → Tenant → BodySizeLimit → RateLimit → SecurityHdrs │
└──────┬──────────────┬──────────────┬───────────────┬───────────────┘
       │              │              │               │
       ▼              ▼              ▼               ▼
┌──────────┐  ┌──────────────┐  ┌────────┐  ┌──────────────────────┐
│PostgreSQL│  │AI Gateway    │  │ Redis  │  │  Celery Worker       │
│16        │  │(port 8001)   │  │7       │  │  5 queues:           │
│          │  │              │  │        │  │  critical · default  │
│114 models│  │litellm multi-│  │Cache · │  │  bulk · webhooks     │
│55 migr.  │  │provider LLM  │  │Rate ·  │  │  retention           │
│AsyncPG   │  │RAG pipeline  │  │Celery  │  │  25+ periodic tasks  │
│pool 20   │  │Embeddings    │  │broker  │  │                      │
└──────────┘  └──────────────┘  └────────┘  └──────────────────────┘
                    │
       ┌────────────┼────────────────────┐
       ▼            ▼                    ▼
┌──────────┐  ┌──────────┐       ┌──────────────┐
│Anthropic │  │OpenAI    │       │ElasticSearch │
│Claude    │  │GPT-4o    │       │8 (search &   │
│(primary) │  │(vision/  │       │ indexing)    │
│          │  │fallback) │       └──────────────┘
└──────────┘  └──────────┘
       + Google, xAI, DeepSeek (via litellm)
```

### 1.2 Tech Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Frontend | Next.js | 14.2.25 | App Router, SSR |
| Frontend | TypeScript | 5.7.2 | Strict mode |
| Frontend | Tailwind CSS | 3.4.17 | |
| Frontend | React Query | 5.62.8 | Data fetching |
| Frontend | Zustand | 5.0.2 | Client state |
| Frontend | Clerk | 6.9.6 | Auth provider |
| Backend | FastAPI | 0.115.6 | REST API |
| Backend | Python | 3.12 | |
| Backend | SQLAlchemy | 2.0.36 | Async ORM |
| Backend | Alembic | 1.14.0 | Migrations |
| Backend | Celery | 5.4.0 | Task queue |
| Database | PostgreSQL | 16 | Primary store |
| Cache | Redis | 7 | Cache + broker |
| Search | Elasticsearch | 8.12.0 | Full-text |
| Storage | MinIO / S3 | — | Documents |
| AI Primary | Claude Sonnet 4 | claude-sonnet-4-20250514 | |
| AI Vision | GPT-4o | gpt-4o | Fallback |
| AI Routing | litellm | 1.55.3 | Multi-provider |
| Monitoring | Sentry | 2.53.0 | Error tracking |
| Auth | Clerk | — | JWT + webhooks |

### 1.3 Monorepo Structure

```
scr-platform/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py         # 70+ routers registered
│   │   │   ├── worker.py       # Celery worker
│   │   │   ├── models/         # 114 SQLAlchemy classes
│   │   │   ├── modules/        # 70 feature modules
│   │   │   ├── core/           # DB, config, security, Celery
│   │   │   ├── services/       # AI budget, prompt registry, cache
│   │   │   ├── auth/           # Clerk JWT, RBAC
│   │   │   ├── tasks/          # Global Celery tasks
│   │   │   └── middleware/     # Audit, tenant, security
│   │   └── alembic/versions/   # 55 migrations
│   └── web/                    # Next.js frontend
│       └── src/
│           ├── app/            # 71 pages (App Router)
│           ├── lib/            # 86 React Query hooks
│           └── components/     # 29 components
├── packages/
│   ├── ui/                     # Shared component library
│   ├── types/                  # Shared TypeScript types
│   └── config/                 # Shared ESLint, Tailwind configs
├── services/
│   └── ai-gateway/             # AI microservice (port 8001)
│       └── app/
│           ├── routers/        # completions, embeddings, search, feeds
│           └── services/       # llm_router, rag, vector_store, rate_limiter
└── infrastructure/
    ├── docker/
    ├── terraform/
    └── scripts/
```

### 1.4 Multi-Tenancy Pattern

Every request flows through:
1. `TenantMiddleware` — injects `org_id` from authenticated user into request context
2. Every service function receives `org_id` and applies `WHERE org_id = :org_id`
3. AI Gateway namespaces RAG vectors by `org_id`
4. Audit logs record `org_id` on every write

### 1.5 RBAC Matrix

| Role | Resources | Key Permissions |
|------|-----------|-----------------|
| `admin` | all | manage_settings:settings, delete:project, view:audit_log, run_analysis:analysis, manage_team:organization |
| `manager` | most | create:project, run_analysis:analysis, view:analysis, manage_integrations:connectors |
| `analyst` | read + analyze | view:project, view:analysis, run_analysis:analysis |
| `viewer` | read-only | view:project, view:analysis |

---

## 2. Implementation Status

### 2.1 Feature Modules — Complete Inventory

| Module | Backend | Frontend Page | Lib Hook | Tests | Notes |
|--------|---------|--------------|----------|-------|-------|
| **Core** | | | | | |
| Auth (Clerk) | ✅ | ✅ | ✅ | ✅ | JWT + webhook sync |
| Projects | ✅ | ✅ | ✅ | ✅ | Full CRUD + milestones + budgets |
| Onboarding | ✅ | ✅ | ✅ | ✅ | Multi-step wizard |
| Settings | ✅ | ✅ | ✅ | — | User + org preferences |
| Notifications | ✅ | ✅ | ✅ | — | SSE real-time |
| **Data Room** | | | | | |
| Data Room | ✅ | ✅ | ✅ | ✅ | Upload, classify, extract |
| Document Versions | ✅ | ✅ | ✅ | — | Version history + access log tab |
| Document Annotations | ✅ | ✅ | ✅ | — | PDF highlights & notes |
| Redaction | ✅ | — | ✅ | — | PII removal (async); no UI page |
| **Deal Intelligence** | | | | | |
| Signal Score | ✅ | ✅ | ✅ | ✅ | Multi-dimension AI scoring |
| Deal Intelligence | ✅ | ✅ | ✅ | ✅ | Screening + pipeline + compare |
| Deal Rooms | ✅ | ✅ | ✅ | — | Collaborative workspace |
| Deal Flow | ✅ | — | ✅ | — | Stage transitions + analytics |
| Smart Screener | ✅ | ✅ | ✅ | — | Saved searches + alerts |
| Comparable Transactions | ✅ | ✅ | ✅ | ✅ | Comps library + AI matching |
| Matching | ✅ | ✅ | ✅ | — | Investor-deal algorithm |
| Due Diligence | ✅ | ✅ | ✅ | — | Checklists + templates |
| Meeting Prep | ✅ | ✅ | ✅ | — | AI briefing generation |
| Expert Insights | ✅ | ✅ | ✅ | — | AI expert analysis |
| **Financial** | | | | | |
| Valuations | ✅ | ✅ | ✅ | — | DCF + comps + IRR calculator |
| Tax Credits | ✅ | ✅ | ✅ | — | Credit identification + calc |
| Carbon Credits | ✅ | ✅ | ✅ | — | Carbon estimation + tracking |
| Equity Calculator | ✅ | ✅ | ✅ | — | Cap table + dilution modeling |
| Capital Efficiency | ✅ | ✅ | ✅ | — | Deployment metrics |
| FX | ✅ | ✅ | ✅ | — | Exposure + rate tracking |
| Financial Templates | ✅ | ✅ | ✅ | — | Excel/model templates |
| Value Quantifier | ✅ | ✅ | ✅ | — | Impact quantification |
| Stress Test | ✅ | ✅ | ✅ | — | Scenario analysis |
| Pacing (J-Curve) | ✅ | ✅ | ✅ | — | Cash flow projections |
| **Portfolio** | | | | | |
| Portfolio | ✅ | ✅ | ✅ | — | Holdings + metrics + strategy |
| Monitoring | ✅ | ✅ | ✅ | — | KPI + covenant tracking |
| LP Reports | ✅ | ✅ | ✅ | — | LP reporting templates |
| Metrics | ✅ | — | ✅ | — | Snapshots + benchmarks; no UI |
| **Legal & Compliance** | | | | | |
| Legal | ✅ | ✅ | ✅ | — | Documents + templates + review |
| Compliance | ✅ | ✅ | ✅ | — | Deadline calendar |
| Certification | ✅ | ✅ | ✅ | — | Investor readiness |
| Insurance | ✅ | ✅ | ✅ | ✅ | Quotes + policies (advisory) |
| **ESG & Impact** | | | | | |
| ESG | ✅ | ✅ | ✅ | — | Portfolio ESG dashboard |
| Impact | ✅ | ✅ | ✅ | — | SDG + impact KPIs |
| **AI & Intelligence** | | | | | |
| Ralph AI | ✅ | ✅ | ✅ | ✅ | Conversational agent + RAG |
| AI Feedback | ✅ | ✅ | ✅ | — | Output evaluation (7 pages) |
| Citations | ✅ | — | ✅ | — | Source lineage; no dedicated page |
| Lineage | ✅ | — | ✅ | — | Data provenance; no dedicated page |
| Voice Input | ✅ | — | ✅ | — | Voice-to-text |
| **Platform** | | | | | |
| Marketplace | ✅ | ✅ | ✅ | — | Listings + RFQ + transactions |
| Reporting | ✅ | ✅ | ✅ | — | Report gen + scheduling |
| Collaboration | ✅ | ✅ | ✅ | — | Comments + activity |
| Webhooks | ✅ | — | ✅ | ✅ | Outbound webhook delivery |
| Connectors | ✅ | ✅ | ✅ | — | External data integrations |
| CRM Sync | ✅ | — | ✅ | ✅ | Salesforce + HubSpot |
| Gamification | ✅ | ✅ | ✅ | ✅ | Badges + quests |
| Blockchain Audit | ✅ | ✅ | ✅ | — | Immutable record anchoring |
| Search | ✅ | ✅ | ✅ | — | ElasticSearch + ⌘K palette |
| Backtesting | ✅ | — | ✅ | ✅ | Historical score validation |
| Digest | ✅ | ✅ | ✅ | — | Email digest preferences |
| Watchlists | ✅ | ✅ | ✅ | — | Deal alerts |
| Engagement | ✅ | — | ✅ | — | Document engagement; no UI page |
| QA Workflow | ✅ | — | ✅ | — | Q&A management; no UI page |
| **Specialized** | | | | | |
| Tokenization | ✅ | ✅ | ✅ | — | Digital asset tools |
| Board Advisor | ✅ | ✅ | ✅ | — | Advisor network |
| Investor Personas | ✅ | ✅ | ✅ | — | Profile archetypes |
| Investor Signal Score | ✅ | ✅ | ✅ | — | Investor risk scoring |
| Risk | ✅ | ✅ | ✅ | — | Risk analysis + flags |
| Risk Profile | ✅ | ✅ | ✅ | — | Risk questionnaire |
| Warm Intros | ✅ | ✅ | ✅ | — | Introduction network |
| Ecosystem | ✅ | ✅ | ✅ | — | Company network visualization |
| Development OS | ✅ | ✅ | ✅ | — | Dev timeline + milestones |
| Business Plans | ✅ | ✅ | ✅ | — | Business plan templates |
| Market Data | ✅ | ✅ | ✅ | — | Market intelligence feeds |
| Excel API | ✅ | — | — | — | Office.js add-in (packages/) |
| Custom Domain | ✅ | ✅ | ✅ | — | White-label domain config |
| Admin Panel | ✅ | ✅ | ✅ | — | System admin tools |
| Launch / Feature Flags | ✅ | ✅ | ✅ | — | Go-to-market tools |
| Taxonomy | ✅ | — | — | — | Industry taxonomy reference |

**Totals: 70 backend modules · 71 frontend pages · 86 lib hooks**

---

## 3. Database Inventory

### 3.1 Migration Chain (55 revisions)

| Revision | Description |
|----------|-------------|
| `394135f84e64` | Initial schema — 36 core tables |
| `4b570868cd8e` | Composite indexes and unique constraints |
| `7c4e82b31d09` | Expand project_type enum |
| `8d141fa29a9e` | Merge index + AI cost tracking branches |
| `a0b1c2d3e4f5` | Data connectors (Companies House, ECB, ENTSOE, OpenWeather) |
| `a1b2c3d4e5f6` | AI output feedback table |
| `a4b5c6d7e8f9` | Professional connections (warm intros) |
| `a7b8c9d0e1f2` | Deal stage transitions |
| `a9b8c7d6e5f4` | Metric snapshots and benchmark aggregates |
| `aa1122334455` | is_deleted soft-delete on 9 advisory tables |
| `aa9988776655` | Carbon listed status column |
| `b1c2d3e4f5a6` | Deal rooms (collaborative workspaces) |
| `b2c3d4e5f6a7` | Saved searches |
| `b5c6d7e8f9a0` | Document versions (version control) |
| `b9c8d7e6f5a4` | AI citations and data lineage |
| `c1a2b3c4d5e6` | QA workflow tables |
| `c2a2b3c4d5e6` | Engagement tracking |
| `c2d3e4f5a6b7` | Watchlists |
| `c3a2b3c4d5e6` | Covenant and KPI monitoring |
| `c3d4e5f6a7b8` | Investor risk profiles |
| `c4a2b3c4d5e6` | Org API keys (programmatic access) |
| `c5a2b3c4d5e6` | CRM sync (Salesforce, HubSpot) |
| `c6a2b3c4d5e6` | Cash flow pacing and projections |
| `c6d7e8f9a0b1` | FX rates and currencies |
| `c8a2b3c4d5e6` | Taxonomy and financial templates |
| `c9d0e1f2a3b4` | ESG metrics |
| `cb877e7100cf` | Document classification and share links |
| `d1a2b3c4d5e6` | Business plans columns |
| `d3e4f5a6b7c8` | Blockchain anchors |
| `d5e6f7a8b9c0` | Prompt templates |
| `d7e8f9a0b1c2` | Meeting briefings |
| `e1a2b3c4d5e6` | Backtesting (score validation) |
| `e2a2b3c4d5e6` | Expert notes |
| `e2f3a4b5c6d7` | LP reports |
| `e3a2b3c4d5e6` | Redaction jobs (PII removal) |
| `e4a2b3c4d5e6` | Webhooks (subscriptions + deliveries) |
| `e4f5a6b7c8d9` | Gamification (badges, quests) |
| `e5f6a7b8c9d0` | Due diligence checklist tables |
| `e6a2b3c4d5e6` | Document annotations |
| `e8f9a0b1c2d3` | Compliance deadlines |
| `e8f9a1b2c3d4` | AI validation columns |
| `f1a2b3c4d5e6` | ExtractionType enum extension (6 new types) |
| `f3a4b5c6d7e8` | Comparable transactions |
| `f3a9d1e72b08` | Patch1 — new models and schema updates |
| `f6a7b8c9d0e1` | Investor readiness certifications |
| `f9a0b1c2d3e4` | Stress test runs |
| `ff0011223344` | Fix ProjectType enum casing |
| `g1a2b3c4d5e6` | External data points |
| `g2a2b3c4d5e6` | Launch features (feature flags, waitlist) |
| `h1a2b3c4d5e6` | Custom domains |
| `h2a2b3c4d5e6` | Digest logs |
| `i1a2b3c4d5e6` | AI cost tracking (cost_usd, tokens columns) |
| `1793197fd8ed` | Merge all heads (final consolidation) |

### 3.2 Model Classes by Domain (114 total)

**Core (4):** `Organization`, `User`, `AuditLog`, `Notification`

**Data Room (7):** `Document`, `DocumentFolder`, `DocumentExtraction`, `DocumentAccessLog`, `ShareLink`, `DocumentVersion`, `DocumentAnnotation`

**Projects (4):** `Project`, `ProjectMilestone`, `ProjectBudgetItem`, `SignalScore`

**Financial (3):** `Valuation`, `TaxCredit`, `CarbonCredit`

**Investors (4):** `Portfolio`, `PortfolioHolding`, `PortfolioMetrics`, `InvestorMandate`

**AI (6):** `AIConversation`, `AIMessage`, `AITaskLog`, `PromptTemplate`, `AIOutputFeedback`, `AICitation`

**Advisory (9, with soft-delete):** `BoardAdvisorProfile`, `BoardAdvisorApplication`, `InvestorPersona`, `EquityScenario`, `CapitalEfficiencyMetrics`, `MonitoringAlert`, `InvestorSignalScore`, `InsuranceQuote`, `InsurancePolicy`

**Matching (2):** `MatchResult`, `MatchMessage`

**Legal (2):** `LegalDocument`, `LegalTemplate`

**Reporting (3):** `ReportTemplate`, `GeneratedReport`, `ScheduledReport`

**Collaboration (2):** `Comment`, `Activity`

**Marketplace (3):** `Listing`, `RFQ`, `Transaction`

**Risk (2):** `RiskAssessment`, `InvestorRiskProfile`

**Deal Flow (1):** `DealStageTransition`

**Due Diligence (4):** `DDChecklistTemplate`, `DDChecklistItem`, `DDProjectChecklist`, `DDItemStatus`

**ESG (1):** `ESGMetrics`

**LP Reporting (1):** `LPReport`

**Comparable Transactions (1):** `ComparableTransaction`

**Connections (2):** `ProfessionalConnection`, `IntroductionRequest`

**Compliance (1):** `ComplianceDeadline`

**Deal Rooms (5):** `DealRoom`, `DealRoomMember`, `DealRoomDocument`, `DealRoomMessage`, `DealRoomActivity`

**Watchlists (2):** `Watchlist`, `WatchlistAlert`

**Blockchain (1):** `BlockchainAnchor`

**Gamification (3):** `Badge`, `UserBadge`, `ImprovementQuest`

**Metrics (2):** `MetricSnapshot`, `BenchmarkAggregate`

**Q&A (2):** `QAQuestion`, `QAAnswer`

**Engagement (2):** `DocumentEngagement`, `DealEngagementSummary`

**Monitoring (3):** `Covenant`, `KPIActual`, `KPITarget`

**CRM (3):** `CRMConnection`, `CRMSyncLog`, `CRMEntityMapping`

**Pacing (2):** `CashflowAssumption`, `CashflowProjection`

**Launch (4):** `FeatureFlag`, `FeatureFlagOverride`, `UsageEvent`, `WaitlistEntry`

**Other:** `OrgApiKey`, `FXRate`, `MeetingBriefing`, `StressTestRun`, `SavedSearch`, `InvestorReadinessCertification`, `BusinessPlan`, `ExpertNote`, `WebhookSubscription`, `WebhookDelivery`, `RedactionJob`, `ExternalDataPoint`, `CustomDomain`, `DigestLog`, `DataConnector`, `OrgConnectorConfig`, `DataFetchLog`, `BacktestRun`, `DealOutcome`, `IndustryTaxonomy`, `FinancialTemplate`

### 3.3 Base Model Hierarchy

```python
Base                     # SQLAlchemy declarative base
├── BaseModel            # id (UUID), org_id, created_at, updated_at
│   └── (all tenant-scoped models)
├── TimestampedModel     # created_at, updated_at only
└── AuditMixin           # tracks who created/updated
```

### 3.4 Key Enum Types (`models/enums.py`, 527 lines)

`ProjectStatus`, `ProjectType`, `UserRole`, `DocumentClassification`, `ExtractionType` (6 analysis subtypes: QUALITY_ASSESSMENT, RISK_FLAGS, DEAL_RELEVANCE, COMPLETENESS_CHECK, KEY_FIGURES, ENTITY_EXTRACTION), `DealStage`, `RiskLevel`, `ESGCategory`, `BadgeType`, `QuestStatus`, `WebhookEvent`, `ConnectorType`, `CRMProvider`, `InsuranceType`, `LegalDocumentType`, `ValuationMethod`, `CertificationStatus`, and ~30 more.

### 3.5 Advisory Enum Pattern (important)

Advisory module enums use lowercase DB values (`common_equity`, `available`). Model definitions require `_lc_enum()` helper:

```python
def _lc_enum(*values, name):
    return SAEnum(*values, values_callable=lambda x: [e.value for e in x],
                  name=name, create_type=False)
```

Apply to ALL enum columns in `models/advisory.py`. Core models (projecttype, userrole) use UPPERCASE names — no fix needed.

---

## 4. API Endpoint Reference

### 4.1 Registered Routers (70 total under `/v1`)

Global: `GET /health` (deep check: PostgreSQL, Redis, Elasticsearch, S3/MinIO)

| Prefix | Module | Key Endpoints |
|--------|--------|---------------|
| `/v1/auth` | Auth | JWT verify, Clerk webhook, logout |
| `/v1/projects` | Projects | CRUD, milestones, budgets, stats, publish, status, business-plan-actions |
| `/v1/signal-score` | Signal Score | calculate, batch, live, task status, score, details, gaps, strengths, improvement-guidance, history, trend, changes, volatility, dimension-history |
| `/v1/deals` | Deal Intelligence | pipeline, discover, compare, screen, AI screening, start-ai-screening, memo extraction |
| `/v1/dataroom` | Data Room | documents, folders, extractions, access-logs, share-links |
| `/v1/doc-versions` | Doc Versions | version list, upload, access-log |
| `/v1/document-annotations` | Annotations | CRUD annotations on documents |
| `/v1/portfolio` | Portfolio | holdings, metrics, strategy, alerts |
| `/v1/reporting` | Reporting | generate, templates, schedules |
| `/v1/collaboration` | Collaboration | comments, activity timeline |
| `/v1/notifications` | Notifications | list, mark-read, SSE stream |
| `/v1/risk` | Risk | analysis, flags, recommendations |
| `/v1/risk-profiles` | Risk Profile | questionnaire, scoring |
| `/v1/matches` | Matching | find, accept/reject, messages |
| `/v1/settings` | Settings | user prefs, org config, API keys |
| `/v1/impact` | Impact | metrics, SDG tracking |
| `/v1/valuations` | Valuations | DCF, comps, IRR, AI-assisted |
| `/v1/marketplace` | Marketplace | listings, RFQ, transactions |
| `/v1/tax-credits` | Tax Credits | identify, calculate, documentation |
| `/v1/legal` | Legal | documents, templates, review, completion |
| `/v1/carbon-credits` | Carbon Credits | estimation, tracking, certificates |
| `/v1/board-advisor` | Board Advisor | profiles, applications |
| `/v1/investor-personas` | Investor Personas | archetypes, matching |
| `/v1/equity` | Equity Calculator | cap table, dilution, scenarios |
| `/v1/capital-efficiency` | Capital Efficiency | metrics, benchmarks |
| `/v1/investor-signal-score` | Investor Signal Score | scoring, history |
| `/v1/value-quantifier` | Value Quantifier | impact metrics |
| `/v1/tokenization` | Tokenization | digital assets, token economics |
| `/v1/development` | Development OS | timeline, milestones |
| `/v1/ecosystem` | Ecosystem | company network, competitive landscape |
| `/v1/ralph` | Ralph AI | conversations CRUD, message, stream (SSE) |
| `/v1/admin` | Admin | dashboard, prompt management |
| `/v1/search` | Search | ElasticSearch query, suggestions |
| `/v1/ai-feedback` | AI Feedback | rate/flag AI outputs |
| `/v1/smart-screener` | Smart Screener | saved searches, alerts |
| `/v1/certification` | Certification | investor readiness, certificates |
| `/v1/deal-flow` | Deal Flow | stage transitions, analytics |
| `/v1/due-diligence` | Due Diligence | checklists, templates, progress |
| `/v1/esg` | ESG | metrics, portfolio summary |
| `/v1/lp-reports` | LP Reports | generate, templates, history |
| `/v1/comps` | Comparable Txns | search, CRUD, similar (AI), implied-valuation, import-csv |
| `/v1/warm-intros` | Warm Intros | connections, requests |
| `/v1/fx` | FX | rates, exposure, conversion |
| `/v1/meeting-prep` | Meeting Prep | generate briefing, history |
| `/v1/compliance` | Compliance | deadlines, reminders |
| `/v1/stress-test` | Stress Test | scenarios, run, results |
| `/v1/connectors` | Connectors | OAuth, config, fetch, logs |
| `/v1/deal-rooms` | Deal Rooms | rooms, members, docs, messages |
| `/v1/watchlists` | Watchlists | CRUD, alerts, triggers |
| `/v1/blockchain` | Blockchain Audit | anchors, verify, report |
| `/v1/voice` | Voice Input | transcribe, history |
| `/v1/gamification` | Gamification | badges/my, badges/project/{id}, leaderboard, progress/{id} |
| `/v1/insurance` | Insurance | quotes, policies |
| `/v1/digest` | Digest | preferences GET/PUT |
| `/v1/metrics` | Metrics | snapshots, benchmarks |
| `/v1/citations` | Citations | list, get, lineage |
| `/v1/lineage` | Lineage | data provenance graph |
| `/v1/qa` | QA Workflow | questions, answers, SLA |
| `/v1/engagement` | Engagement | document scoring, summaries |
| `/v1/monitoring` | Monitoring | covenants, KPI actuals/targets |
| `/v1/excel` | Excel API | auth, key management |
| `/v1/crm-sync` | CRM Sync | OAuth connect, connections, sync, logs, mappings |
| `/v1/pacing` | Pacing | assumptions, projections, J-curve |
| `/v1/taxonomy` | Taxonomy | industry hierarchy |
| `/v1/financial-templates` | Financial Templates | system templates |
| `/v1/business-plans` | Business Plans | templates, generate, history |
| `/v1/backtesting` | Backtesting | runs, outcomes, validation |
| `/v1/expert-insights` | Expert Insights | notes, generate |
| `/v1/webhooks` | Webhooks | subscriptions CRUD, deliveries, retry |
| `/v1/redaction` | Redaction | jobs, status, download |
| `/v1/market-data` | Market Data | feeds, refresh |
| `/v1/launch` | Launch | feature flags, waitlist |
| `/v1/custom-domain` | Custom Domain | config, verify, SSL |

### 4.2 Signal Score Endpoints (detail)

```
POST  /v1/signal-score/calculate                  # Trigger async scoring
POST  /v1/signal-score/batch-calculate            # Batch scoring
POST  /v1/signal-score/{project_id}/live          # Live preview (sync)
GET   /v1/signal-score/task/{task_log_id}         # Async task status
GET   /v1/signal-score/{project_id}               # Latest score
GET   /v1/signal-score/{project_id}/details       # Dimension breakdown
GET   /v1/signal-score/{project_id}/gaps          # Improvement gaps
GET   /v1/signal-score/{project_id}/strengths
GET   /v1/signal-score/{project_id}/improvement-guidance
GET   /v1/signal-score/{project_id}/history
GET   /v1/signal-score/{project_id}/history-trend
GET   /v1/signal-score/{project_id}/changes
GET   /v1/signal-score/{project_id}/volatility
GET   /v1/signal-score/{project_id}/dimension-history
```

Signal Score field names: `project_viability_score`, `financial_planning_score`, `risk_assessment_score`, `team_strength_score`, `esg_score` (NOT technical/financial/regulatory/team).

### 4.3 Ralph AI Endpoints (detail)

```
POST   /v1/ralph/conversations                    # Create conversation (201)
GET    /v1/ralph/conversations                    # List conversations
GET    /v1/ralph/conversations/{id}               # Get conversation
DELETE /v1/ralph/conversations/{id}               # Delete (204)
POST   /v1/ralph/conversations/{id}/message       # Send message
POST   /v1/ralph/conversations/{id}/stream        # SSE streaming response
```

### 4.4 Comps Endpoints (detail)

```
GET    /v1/comps                                  # Search (asset_type, geography, year, stage, size, quality)
POST   /v1/comps                                  # Create comp
GET    /v1/comps/similar/{project_id}             # AI-ranked similar comps (limit=10)
POST   /v1/comps/implied-valuation               # Calculate implied EV from selected comps
POST   /v1/comps/import-csv                      # Bulk CSV import
GET    /v1/comps/{comp_id}                        # Get single comp
PUT    /v1/comps/{comp_id}                        # Update comp
DELETE /v1/comps/{comp_id}                        # Soft delete (204)
```

Note: `lib/comps.ts` `useUploadComps()` calls `/comps/upload` but backend route is `/comps/import-csv` — **known mismatch, needs fix**.

### 4.5 Gamification Endpoints (detail)

```
GET  /v1/gamification/badges/my                  # User's earned badges
GET  /v1/gamification/badges/project/{id}        # Project-specific badges
GET  /v1/gamification/leaderboard                # Org leaderboard
GET  /v1/gamification/progress/{project_id}      # Progress summary (read-only)
```

### 4.6 Middleware Stack

| Middleware | Purpose |
|-----------|---------|
| `CORSMiddleware` | Allow FRONTEND_URL, credentials |
| `AuditMiddleware` | Immutable log of all POST/PUT/PATCH/DELETE |
| `TenantMiddleware` | Inject org_id from user into every request |
| `RequestBodySizeLimitMiddleware` | Block oversized requests (configurable MAX_REQUEST_BODY_BYTES) |
| `RateLimitMiddleware` | Redis-based per-org rate limiting |
| `SecurityHeadersMiddleware` | CSP, HSTS, X-Frame-Options, etc. |

### 4.7 RBAC Permission Strings (valid only)

**Valid actions:** `view`, `create`, `update`, `delete`, `run_analysis`, `manage_settings`, `manage_team`, `manage_integrations`

**Valid resources:** `project`, `analysis`, `document`, `portfolio`, `settings`, `organization`, `connectors`, `audit_log`

**Common patterns:**
- `require_permission("view", "analysis")` — read AI results, comps, valuations
- `require_permission("run_analysis", "analysis")` — trigger AI jobs, write comps
- `require_permission("create", "project")` — create new projects
- `require_permission("manage_settings", "settings")` — admin-level settings, webhooks

---

## 5. Frontend Pages

### 5.1 All Pages (71 total)

#### Root

| Route | Description |
|-------|-------------|
| `/` | Landing / marketing entry |
| `/onboarding` | Multi-step onboarding wizard (Role → Org → Preferences → Action → Complete) |

#### Dashboard — Core

| Route | Description |
|-------|-------------|
| `/dashboard` | Portfolio summary, radar chart (5 dimensions), quick actions, recent activity |
| `/projects` | Project list with search, filter by type/impact; create project button |
| `/projects/new` | Create new project wizard |
| `/projects/[id]` | Project detail view |
| `/projects/[id]/signal-score` | AI signal scoring with 5-dimension breakdown |
| `/projects/[id]/due-diligence` | DD checklist and generated report |
| `/projects/[id]/expert-insights` | AI expert analysis |
| `/projects/[id]/matching` | Investor matching for this project |
| `/projects/[id]/meeting-prep` | AI-generated meeting briefing |
| `/projects/[id]/certification` | Investor readiness certification progress |
| `/projects/[id]/carbon` | Carbon credit estimation and tracking |
| `/projects/[id]/insurance` | Insurance quotes and policies |

#### Dashboard — Deals

| Route | Description |
|-------|-------------|
| `/deals` | 3 tabs: Pipeline (Kanban) / Discover (AI recommendations) / Compare (side-by-side) |
| `/deals/[projectId]` | AI screening report detail view |
| `/deal-rooms` | Collaborative deal workspace management |
| `/comps` | Comparable transactions library with filters |
| `/screener` | Smart deal screener with saved searches |
| `/matching` | Investor matching engine |
| `/warm-intros` | Professional introduction network |

#### Dashboard — Data Room

| Route | Description |
|-------|-------------|
| `/data-room` | Document browser (grid/list view), upload modal, extraction panel |
| `/data-room/documents/[id]` | PDF viewer, annotations, version history, access log tab |

#### Dashboard — Portfolio

| Route | Description |
|-------|-------------|
| `/portfolio` | Portfolio overview and monitoring |
| `/portfolio/[id]` | Individual holding detail |
| `/monitoring` | Real-time KPI and covenant monitoring |
| `/pacing` | J-Curve pacing analysis and projections |
| `/lp-reports` | LP reporting and templates |
| `/capital-efficiency` | Capital deployment metrics |

#### Dashboard — Financial

| Route | Description |
|-------|-------------|
| `/valuations` | Valuation models (DCF, comps) with "Import from Library" button |
| `/financial-templates` | Financial model templates |
| `/value-quantifier` | Value impact quantification |
| `/equity-calculator` | Cap table + dilution modeling |
| `/fx` | FX exposure management |
| `/stress-test` | Scenario stress testing |
| `/market-data` | Market intelligence feed |

#### Dashboard — ESG & Impact

| Route | Description |
|-------|-------------|
| `/esg` | ESG portfolio dashboard with portfolio-level summary |
| `/impact` | SDG + impact KPI tracking |
| `/compliance` | Compliance deadline calendar |
| `/blockchain-audit` | Blockchain verification with KPIs, anchor table, PolygonScan links |

#### Dashboard — Business Operations

| Route | Description |
|-------|-------------|
| `/business-plan` | Business plan templates |
| `/legal` | Legal document review and templates |
| `/tax-credits` | Tax credit identification and calculation |
| `/insurance` | Insurance management (main page) |
| `/funding` | Funding options |
| `/tokenization` | Tokenization tools |

#### Dashboard — Analytics

| Route | Description |
|-------|-------------|
| `/analytics` | Analytics overview |
| `/analytics/deal-flow` | Deal flow analytics |
| `/analytics/portfolio` | Portfolio analytics |
| `/score-performance` | Score tracking over time |
| `/risk-profile` | Risk profiling questionnaire |
| `/risk` | Risk analysis dashboard |
| `/investor-signal-score` | Investor risk scoring |

#### Dashboard — Team & Collaboration

| Route | Description |
|-------|-------------|
| `/collaboration` | Activity feed + comment threads |
| `/notifications` | Notification center |
| `/investor-personas` | Investor profile management |
| `/ecosystem` | Company network visualization |
| `/board-advisor` | Board advisor network |

#### Dashboard — Marketplace & Reporting

| Route | Description |
|-------|-------------|
| `/marketplace` | Third-party integrations marketplace |
| `/marketplace/[listingId]` | Listing detail view |
| `/reports` | Report generation |
| `/reports/lp` | LP report templates |
| `/digest` | Activity digest email preferences |
| `/watchlists` | Custom deal watchlists |

#### Dashboard — Settings & Admin

| Route | Description |
|-------|-------------|
| `/settings` | Account + org settings |
| `/settings/custom-domain` | White-label domain configuration |
| `/connectors` | Data connector management |
| `/gamification` | Badges + quests overview |
| `/development-os` | Development operating system |
| `/development-os/[projectId]` | Per-project dev OS |
| `/admin` | Admin panel |
| `/admin/health` | System health monitoring |
| `/admin/feature-flags` | Feature flag management |
| `/admin/prompts` | Prompt template editor (live editing) |
| `/admin/benchmarks` | Benchmark configuration |

### 5.2 Sidebar Navigation (role-based)

**Project Sub-Nav** — auto-injected when pathname matches `/projects/[id]/*`:
Signal Score · Due Diligence · Expert Insights · Matching · Meeting Prep · Certification · Carbon · Insurance

**3 roles:** `investor`, `ally`, `admin` (admin has all investor + admin sections)

### 5.3 Components

| Component | Purpose |
|-----------|---------|
| `Sidebar` (`sidebar.tsx`, 628 lines) | Role-based navigation |
| `Topbar` (`topbar.tsx`) | Top bar with Ralph AI toggle |
| `AIFeedback` (`ai-feedback.tsx`) | Rate/flag AI outputs (used on 7 pages) |
| `RalphPanel` + `RalphChat` + `RalphInput` + `RalphSuggestions` | Ralph AI assistant panel |
| `PDFViewer` + `AnnotationLayer` + `AnnotationSidebar` + `ViewerToolbar` | PDF viewer |
| `ExtractionPanel` + `DocumentPreview` + `FolderTree` + `UploadModal` | Data room UI |
| `CommandPalette` (`search/command-palette.tsx`) | ⌘K global search |
| `FeatureTour` (`feature-tour.tsx`) | Role-specific onboarding overlay |
| `LineagePanel` | Data provenance visualization |
| `CitationBadges` | Source reference badges |
| `CertificationBadge` | Certification status indicator |
| `BrandingProvider` | CSS variable injection for white-label |

### 5.4 Zustand Stores

| Store | State | Purpose |
|-------|-------|---------|
| `useRalphStore` | isOpen, activeConversationId | Ralph AI panel |
| `useSidebarStore` | isOpen | Sidebar collapse |
| `useGlobalFilterStore` | search | Global search text |
| `useSearchStore` | isOpen | ⌘K command palette |
| `useNotificationStore` | unreadCount | Notification badge count |

---

## 6. AI Integration

### 6.1 AI Gateway Architecture

All LLM calls from the backend route through a dedicated FastAPI microservice (port 8001):

```
Backend Module → POST http://ai-gateway:8001/v1/completions → litellm → LLM Provider
                                                           → RAG pipeline (optional)
                                                           → Rate limiter (per org)
                                                           → Token tracker
```

**Endpoints:**
```
GET  /health
GET  /v1/models                     # List task types + supported models
POST /v1/completions                # LLM completion (tools/function-calling supported)
POST /v1/completions/stream         # SSE streaming completions
POST /v1/embeddings                 # Text embeddings (text-embedding-3-large)
POST /v1/search/documents           # RAG vector search
GET  /v1/feeds/{feed_type}          # External data feeds (FRED, World Bank, etc.)
```

### 6.2 Model Routing (litellm)

| Task Type | Primary Model | Fallback |
|-----------|--------------|---------|
| All analysis | `claude-sonnet-4-20250514` | `gpt-4o` |
| Vision / document OCR | `gpt-4o` | — |
| Embeddings | `text-embedding-3-large` | — |
| Streaming | `claude-sonnet-4-20250514` | — |

**Providers:** Anthropic (primary), OpenAI, Google, xAI, DeepSeek

**Tool format:** OpenAI function-calling format: `{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}`

### 6.3 Prompt Registry

**Location:** `apps/api/app/services/prompt_registry.py`

```python
registry = PromptRegistry(db)
messages, template_id, version = await registry.render(
    task_type="score_quality",
    variables={"document_text": ..., "criterion_name": ..., ...}
)
```

- DB-backed templates (`PromptTemplate` model)
- Graceful fallback to hardcoded strings on any exception
- Admin editing at `/admin/prompts`
- Seeded defaults in `app/services/seed_prompts.py`

**Modules using registry (try/fallback pattern):**

| Module | File | task_type |
|--------|------|-----------|
| Signal Score | `signal_score/ai_scorer.py` | `score_quality` |
| Deal Intelligence | `deal_intelligence/tasks.py` | `deal_screening`, `investment_memo` |
| Legal | `legal/tasks.py` | `legal_document_completion`, `legal_document_review` |
| Risk | `risk/service.py` | `risk_mitigation` |
| Meeting Prep | `meeting_prep/service.py` | `meeting_preparation` |

For sync Celery tasks: use `asyncio.new_event_loop()` to call async registry. Session: `from app.core.database import async_session_factory`.

### 6.4 Analysis Cache

**Location:** `apps/api/app/services/analysis_cache.py`

```python
cache = make_analysis_cache(db)
result = await cache.get_or_analyze(
    document_id=doc.id,
    analysis_type="quality_assessment",   # ExtractionType value
    context={"criterion_name": ..., "project_type": ...},
)
# result["cached"] == True → no AI call; result["result"] = parsed JSON
```

**ExtractionType values:** `QUALITY_ASSESSMENT`, `RISK_FLAGS`, `DEAL_RELEVANCE`, `COMPLETENESS_CHECK`, `KEY_FIGURES`, `ENTITY_EXTRACTION`

**Active cache integrations:**
- `signal_score/engine.py` — `_get_cached_quality()` before AI scorer call
- `deal_intelligence/tasks.py` — pre-loads `deal_relevance` analyses per document

### 6.5 RAG Pipeline

**Location:** `services/ai-gateway/app/services/rag.py`

- Documents chunked on upload via embeddings endpoint
- Chunks stored in Pinecone (prod) / local vector store (dev)
- Namespaced by `org_id` for multi-tenancy
- Ralph AI (`agent.py`) calls `_fetch_rag_context()` before every message and stream

### 6.6 Context Window Management

**Location:** `apps/api/app/modules/ralph_ai/context_manager.py`

```python
ContextWindowManager(ai_client: GatewayAIClient)
# Class constants:
TOTAL_BUDGET = 16_000     # total token budget
MIN_RECENT_PAIRS = 3      # always keep last 3 message pairs
# Method:
_truncate_messages(messages, budget)  # read-only, returns trimmed list
```

### 6.7 AI Cost Tracking

- Every AI call records `cost_usd`, `tokens_input`, `tokens_output` in `AITaskLog`
- Budget enforcement per org tier (env vars):
  - Foundation: `AI_TOKEN_BUDGET_FOUNDATION=2_000_000`
  - Professional: `AI_TOKEN_BUDGET_PROFESSIONAL=20_000_000`
  - Enterprise: `AI_TOKEN_BUDGET_ENTERPRISE=200_000_000`

### 6.8 AI-Powered Features

| Feature | Trigger | AI Type |
|---------|---------|---------|
| Signal Score | On demand + async Celery | Multi-dimension document analysis |
| Deal Screening | On demand | Deal relevance + memo extraction |
| Meeting Prep | On demand | Briefing generation |
| Expert Insights | On demand | Analysis synthesis |
| Legal Review | On demand | Document completion + review |
| Risk Analysis | On demand | Risk flag identification |
| Carbon Estimation | On demand | Carbon credit calculation |
| Comps Similarity | On demand | AI ranking of comparable transactions |
| Ralph AI | Real-time | Conversational + RAG |
| Valuation | On demand | AI-assisted valuation |
| Due Diligence | On demand | Checklist generation |
| Gamification | Post-signal-score | Badge evaluation + quest generation |

---

## 7. External Services & Infrastructure

### 7.1 Infrastructure Services

| Service | Port | Version | Purpose |
|---------|------|---------|---------|
| PostgreSQL | 5432 | 16 | Primary datastore (multi-tenant, org_id-scoped) |
| Redis | 6379 | 7 | Cache (DB 0), Celery broker (DB 1), rate limiting |
| Elasticsearch | 9200 | 8.12.0 | Full-text search, document indexing |
| MinIO | 9000/9001 | latest | S3-compatible local file storage |
| MailHog | 1025/8025 | — | Email testing (dev only) |

### 7.2 External API Dependencies

| Service | Purpose | Config Key |
|---------|---------|------------|
| Clerk | Auth + user management | `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET` |
| Anthropic | Primary LLM | `ANTHROPIC_API_KEY` |
| OpenAI | Vision + fallback | `OPENAI_API_KEY` |
| Google AI | Alternative LLM | `GOOGLE_API_KEY` |
| xAI | Alternative LLM | `XAI_API_KEY` |
| DeepSeek | Alternative LLM | `DEEPSEEK_API_KEY` |
| Pinecone | Vector database (RAG) | `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` |
| AWS S3 / MinIO | Document storage | `AWS_ACCESS_KEY_ID`, `AWS_S3_BUCKET` |
| Sentry | Error monitoring | `SENTRY_DSN` |
| Resend | Transactional email | `RESEND_API_KEY` |
| FRED | Economic data | `FRED_API_KEY` |
| Alpha Vantage | Market/financial data | `ALPHA_VANTAGE_API_KEY` |
| HubSpot | CRM (OAuth, stored encrypted) | — |
| Salesforce | CRM (OAuth, stored encrypted) | — |
| ECB | FX rates | No key needed |
| ENTSOE | Energy data | Connector config |
| OpenWeather | Climate data | Connector config |
| Companies House | UK company data | Connector config |
| Polygon (Web3) | Blockchain anchoring (chain 137) | Web3.py |

### 7.3 Celery Infrastructure

**5 Queues:**

| Queue | Concurrency | Rate Limit | Timeout | Purpose |
|-------|-------------|-----------|---------|---------|
| `critical` | 4 | 20/min | 120s | Signal scoring, document processing |
| `default` | 8 | — | 180s | Notifications, reports, general |
| `bulk` | 2 | — | 600s | Nightly benchmarks, batch analysis |
| `webhooks` | 6 | 100/min | 30s | Outbound webhook delivery |
| `retention` | 1 | — | 900s | GDPR cleanup, archiving |

**Periodic Task Schedule:**

| Frequency | Task |
|-----------|------|
| Every 5 min | Webhook retry |
| Every 15 min | Watchlist checks, CRM sync |
| Every 30 min | QA SLA monitoring |
| Hourly | FRED data, Yahoo Finance, live score updates |
| Every 6h | Regulatory data, risk monitoring |
| Every 12h | Climate data (NOAA) |
| Daily 2am | Daily metric snapshots |
| Daily 3am | Nightly benchmarks |
| Daily 3:30am | Database backups |
| Daily 4:30am | Data retention cleanup |
| Daily 6am | Compliance checks, covenant monitoring |
| Daily 6:30am | Market data fetch |
| Weekly Sun 8pm | Email digests |
| Monthly 28th | PostgreSQL partition pre-creation |

### 7.4 Database Configuration

| Setting | Value |
|---------|-------|
| Primary pool size | 20 connections + 10 overflow |
| Read replica pool | 15 connections + 10 overflow |
| Statement timeout | 30 seconds |
| Idle-in-transaction timeout | 60 seconds |
| Lock timeout | 10 seconds |
| Financial precision | `Numeric(19,4)` |
| Read replica | Optional via `DATABASE_URL_READ_REPLICA` |

### 7.5 Encryption

**Location:** `apps/api/app/services/encryption.py`

Fernet symmetric encryption for: CRM OAuth tokens, connector API keys. Key source: `SECRET_KEY` env var.

---

## 8. Gap Analysis

### 8.1 Missing Tests

| Module | Test Status | Priority |
|--------|------------|---------|
| Valuations | None | High — complex financial logic |
| Legal AI tasks | None | High — AI pipeline |
| Matching algorithm | None | Medium — core feature |
| Reporting generation | None | Medium |
| Signal Score engine internals | Basic coverage | Medium |
| Deal Intelligence tasks | Basic coverage | Medium |
| Stress Test engine | None | Low |
| Blockchain anchoring | None | Low |
| Redaction pipeline | None | Low |

### 8.2 Missing Loading States

Only `/deals/loading.tsx` exists. All 57+ other dashboard routes lack loading skeletons — users see blank content on slow connections.

### 8.3 Missing Error Boundaries

Zero `error.tsx` files across all routes. Next.js App Router needs these for route-level error UI.

### 8.4 Backend Modules Without Frontend Pages

| Module | Notes |
|--------|-------|
| Citations | Component exists (`citation-badges.tsx`) but no management page |
| Lineage | Panel component exists but no dedicated page |
| QA Workflow | Full API built; no frontend |
| Engagement | Data collected; no management view |
| Metrics (benchmarks) | Data available; no dedicated display page |
| Redaction | Admin-only; no UI intentional |
| Excel API | Separate Office.js add-in in `packages/excel-addin/` |
| Taxonomy | Reference data; UI likely unnecessary |
| CRM Sync detail | `connectors/page.tsx` covers basic config; no sync history page |

### 8.5 API / Frontend Mismatches

| Issue | Detail |
|-------|--------|
| Comps upload route | `lib/comps.ts` `useUploadComps()` calls `POST /comps/upload` but backend is `POST /comps/import-csv` |
| Webhook route in tests (fixed) | Was `/webhooks/subscriptions`, now correctly `/webhooks` |

### 8.6 Security Notes

- All comps endpoints: recently fixed from invalid `require_permission("view", "comp")` → `require_permission("view", "analysis")`
- Webhook endpoints: recently fixed from `require_permission("admin", "project")` → `require_permission("manage_settings", "settings")`
- Connector OAuth tokens use Fernet encryption — no key rotation mechanism implemented
- AI Gateway API key is static — no rotation mechanism
- Pinecone namespaces not cleaned up on org deletion (data retention gap)

---

## 9. Recommended Improvements

### 9.1 High Priority

1. **Fix comps upload route mismatch** — rename `POST /comps/import-csv` → `POST /comps/upload` OR update `lib/comps.ts` to call the correct path. One line fix.

2. **Add `loading.tsx` skeletons** to all 57+ dashboard routes. Use `/deals/loading.tsx` as the template (`animate-pulse` Tailwind divs matching each page's rough layout).

3. **Add `error.tsx` files** for all major route groups. Minimum: `(dashboard)/error.tsx` as a catch-all with a "Something went wrong" + retry button.

4. **Test coverage for financial modules** — Valuations, Tax Credits, and Carbon Credits have complex deterministic calculations. Target ≥80% coverage on business logic. Est. ~40 new tests.

### 9.2 Medium Priority

5. **Citations and Lineage pages** — Backend fully built, panel components exist. Adding `/citations` and `/lineage` pages surfaces high-value transparency features for investors. ~2 hours each.

6. **QA Workflow page** — `QAQuestion`/`QAAnswer` API is complete. A management page would expose this to users.

7. **Engagement dashboard** — Document engagement data is actively collected but not surfaced in a management view for allies to see investor behavior.

8. **CRM Sync history page** — A per-connection sync history page (sync logs, error details, entity mapping status) would improve operator experience.

9. **AI Cost dashboard** — `AITaskLog` has `cost_usd` per call. A real-time cost chart in `/admin` panel would enable budget management.

### 9.3 Architecture Improvements

10. **Read replica routing** — `DATABASE_URL_READ_REPLICA` is configured but analytics/reporting queries still hit the primary. Route heavy reads (benchmarks, metrics, deal analytics) to the replica.

11. **Celery monitoring** — Add Flower (Celery monitoring UI) to docker-compose for visibility into task queues and failure rates.

12. **Pinecone namespace cleanup** — Add a data retention task to delete RAG namespaces for deleted organizations.

13. **Webhook secret rotation** — Add `POST /webhooks/{id}/rotate-secret` endpoint to `WebhookSubscription`.

14. **API key rotation** — The static `AI_GATEWAY_API_KEY` should be rotatable without a full deploy.

### 9.4 Developer Experience

15. **MSW (Mock Service Worker)** — Add for frontend component testing in isolation from the backend.

16. **Startup validation** — Add a startup check verifying `ANTHROPIC_API_KEY` and `AI_GATEWAY_URL` are reachable before FastAPI accepts traffic.

17. **OpenAPI completeness** — Audit all 150+ endpoints for missing `summary`, `description`, and example responses.

---

## 10. Completion Dashboard

### 10.1 Platform Metrics

| Category | Count | Status |
|----------|-------|--------|
| Backend modules | 70 | ✅ All complete |
| API routers | 70 | ✅ All registered in main.py |
| Frontend pages | 71 | ✅ 68 complete, 3 partial |
| Lib hooks | 86 | ✅ All complete |
| DB migrations | 55 | ✅ All applied (head) |
| Model classes | 114 | ✅ All complete |
| Test files | ~25 | ⚠️ 687 passing, 11 skipped; many modules untested |
| Loading skeletons | 1/58+ | ⚠️ Only /deals has loading.tsx |
| Error boundaries | 0 | ❌ None |

### 10.2 Sprint History

| Sprint | Scope | Status |
|--------|-------|--------|
| Sprints 1–8 | Core platform, auth, projects, data room, portfolio | ✅ |
| Sprints 9–12 | Deal intelligence, signal score, matching, comps | ✅ |
| Sprint 13–16 | Insurance, CRM, digest, gamification fixes, Ralph RAG | ✅ |
| Sprint 16 extras | S23 Insurance CRUD, S43 Digest preferences | ✅ |
| ROI Fixes Feb 2026 | S36 Ralph RAG, F18 Gamification, S37 AIFeedback, F05 ESG, F02 Certification | ✅ |
| Short-term Items 6–10 | Item 6 Prompt Registry, Item 7 Analysis Cache, Item 8 Sidebar Nav, Item 9 Access Log, Item 10 Blockchain | ✅ |
| Medium-term Items 11–15 | Items 11–13 + 15 already existed; Item 14 Comps→Valuation wired | ✅ |
| Bug fixes Mar 2026 | 13 test failures fixed, migration chain unblocked, RBAC fixes | ✅ |

### 10.3 Test Suite (2026-03-01)

```
687 passed, 11 skipped
```

**Test files:**
`test_projects.py`, `test_signal_score.py`, `test_deals.py`, `test_portfolio.py`, `test_dataroom.py`, `test_auth.py`, `test_comps.py`, `test_valuations.py`, `test_ralph_ai.py`, `test_webhooks.py`, `test_crm_sync.py`, `test_gamification.py`, `test_insurance.py`, `test_backtesting.py`, `test_celery_tasks.py`

AI Gateway tests: `test_health.py`, `test_validation.py`, `test_batcher.py`, `test_rag.py`, `test_token_tracker.py`

### 10.4 Quick Start

```bash
# 1. Start infrastructure
cd /Users/martin/Projects/scr-platform
docker compose up -d

# 2. Apply migrations
cd apps/api && poetry run alembic upgrade head

# 3. Start services (3 terminals)
poetry run uvicorn app.main:app --reload --port 8000           # API
cd ../../services/ai-gateway && uvicorn app.main:app --reload --port 8001  # AI Gateway
cd ../../apps/api && celery -A app.worker worker --beat --loglevel=info    # Celery

# 4. Start frontend
cd ../web && pnpm dev

# 5. Run tests
cd ../api && poetry run pytest -x -q
```

### 10.5 Key File Index

| What | Path |
|------|------|
| API entry | `apps/api/app/main.py` |
| Dashboard layout | `apps/web/src/app/(dashboard)/layout.tsx` |
| Sidebar | `apps/web/src/components/sidebar.tsx` |
| RBAC | `apps/api/app/auth/rbac.py` |
| DB session | `apps/api/app/core/database.py` |
| Celery config | `apps/api/app/core/celery_config.py` |
| AI Gateway main | `services/ai-gateway/app/main.py` |
| LLM router | `services/ai-gateway/app/services/llm_router.py` |
| Prompt registry | `apps/api/app/services/prompt_registry.py` |
| Analysis cache | `apps/api/app/services/analysis_cache.py` |
| Signal score engine | `apps/api/app/modules/signal_score/engine.py` |
| Ralph agent | `apps/api/app/modules/ralph_ai/agent.py` |
| Context manager | `apps/api/app/modules/ralph_ai/context_manager.py` |
| Encryption | `apps/api/app/services/encryption.py` |
| Zustand stores | `apps/web/src/lib/store.ts` |
| API client | `apps/web/src/lib/api.ts` |
| Docker compose | `docker-compose.yml` |
| Environment template | `.env.example` |
| Enums | `apps/api/app/models/enums.py` |
| Advisory models | `apps/api/app/models/advisory.py` |

---

*SCR Platform Blueprint v2 — Generated 2026-03-01 by live codebase scan.*
*Do not edit manually — regenerate from codebase scan when significant changes are made.*
