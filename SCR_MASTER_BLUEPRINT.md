# SCR PLATFORM — MASTER BLUEPRINT
**Generated:** 2026-02-28
**Last updated:** 2026-02-28 (post-fix pass)
**Status:** All API tests passing — 436 passed, 0 failed, 7 skipped
**Codebase root:** `/Users/martin/Projects/scr-platform`

---

## TABLE OF CONTENTS

1. [Platform Overview](#1-platform-overview)
2. [Session Status Map (S01–S43 + F01–F18)](#2-session-status-map)
3. [Database Schema Map](#3-database-schema-map)
4. [API Endpoint Map](#4-api-endpoint-map)
5. [Frontend Page Map](#5-frontend-page-map)
6. [AI Integration Map](#6-ai-integration-map)
7. [Integration & Dependency Map](#7-integration--dependency-map)
8. [Gap Analysis](#8-gap-analysis)
9. [Improvement Recommendations](#9-improvement-recommendations)
10. [Metrics Summary](#10-metrics-summary)

---

## 1. PLATFORM OVERVIEW

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER / CLIENT                     │
│          Next.js 14 App Router — apps/web:3000           │
│  Clerk Auth │ React Query │ Zustand │ Tailwind/shadcn-ui │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS + JWT
                       ▼
┌─────────────────────────────────────────────────────────┐
│            FASTAPI — apps/api:8000                       │
│  ASGI / Uvicorn                                          │
│  ├── TenantMiddleware  (org_id injection)                 │
│  ├── AuditMiddleware   (immutable write log)              │
│  ├── RateLimitMiddleware (Redis token bucket)             │
│  ├── SecurityHeadersMiddleware (CSP, HSTS, etc.)         │
│  ├── 72 routers — 374 endpoints                          │
│  ├── 53 backend modules                                  │
│  └── Celery worker (apps/api/app/worker.py)              │
└──────┬────────────────────┬────────────────────────────┘
       │                    │
       ▼                    ▼
┌─────────────┐   ┌─────────────────────────────────────┐
│ PostgreSQL  │   │   AI GATEWAY — services/ai-gateway   │
│ (SQLAlchemy │   │   :8001                              │
│  async)     │   │   ├── llm_router.py (litellm)        │
│             │   │   ├── validation.py (S33 — auto)     │
│ Redis       │   │   ├── rag.py (S36)                   │
│ (Celery +   │   │   ├── task_batcher.py (S39)          │
│  rate limit)│   │   ├── token_tracker.py               │
│             │   │   ├── rate_limiter.py                │
│ ElasticSearch│  │   ├── vector_store.py                │
│ (S12 search)│   │   └── external_data.py               │
└─────────────┘   └───────────────┬─────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
           ┌──────────┐  ┌──────────────┐  ┌──────────┐
           │Anthropic │  │  OpenAI API  │  │ Pinecone │
           │Claude    │  │ (embeddings) │  │(vector DB│
           │Sonnet 4  │  └──────────────┘  │  RAG)    │
           └──────────┘                   └──────────┘
                                               ▼
                                      ┌──────────────┐
                                      │   AWS S3     │
                                      │ (documents,  │
                                      │  reports)    │
                                      └──────────────┘
```

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend framework | Next.js (App Router) | 14.2.25 |
| Frontend UI | React | 18.3.1 |
| Styling | Tailwind CSS | 3.4.17 |
| Component library | Custom `@scr/ui` (shadcn-based) | workspace |
| State management | Zustand | 5.0.2 |
| Data fetching | TanStack React Query | 5.62.8 |
| Forms | React Hook Form + Zod | 7.54.2 / 3.24.1 |
| Charting | Recharts | 3.7.0 |
| Auth (frontend) | Clerk Next.js | 6.9.6 |
| Backend framework | FastAPI | 0.115.6 |
| ORM | SQLAlchemy 2.0 (async) | 2.0.36 |
| Migrations | Alembic | 1.14.0 |
| Background tasks | Celery + Redis | 5.4.0 |
| HTTP client | httpx | 0.28.1 |
| Data validation | Pydantic v2 | 2.10.3 |
| AI routing | litellm (in AI gateway) | — |
| Primary AI model | Claude Sonnet 4 | claude-sonnet-4-20250514 |
| Auth (backend) | Clerk JWT + Webhook (svix) | — |
| Object storage | AWS S3 / MinIO (local) | boto3 3.135 |
| Search | ElasticSearch | 8.17.0 |
| Cache / Queue | Redis | 5.2.1 |
| Report generation | openpyxl, python-pptx, Jinja2 | — |
| Logging | structlog | 24.4.0 |
| Testing (API) | pytest-asyncio | 0.25.0 |
| Testing (web) | Vitest + Testing Library | 2.1.8 |

### Codebase Statistics

| Metric | Count |
|--------|-------|
| Python source files (API) | 353 |
| TypeScript/React files (Web) | 114 |
| Python files (AI Gateway) | 25 |
| Backend modules | 53 |
| API endpoints | 374 |
| Database tables | 79 |
| Frontend pages (routes) | 48 |
| Frontend components | 21 |
| Alembic migrations | 28 |
| API test files | 17 |
| AI Gateway test files | 5 |
| Total Python lines (API) | ~60,957 |
| Total Python lines (Gateway) | ~3,470 |
| Total TypeScript/TSX lines | ~40,081 |
| **Total lines of code** | **~104,508** |

---

## 2. SESSION STATUS MAP

### Legend
- ✅ **COMPLETE** — All expected code exists and is functional
- 🟡 **PARTIAL** — Some code exists but missing pieces
- ❌ **NOT BUILT** — No code found
- 🔧 **BUILT BUT NOT WIRED** — Infrastructure exists but not adopted by consuming modules

---

### Phase 0 — Foundation

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S01 | Monorepo Scaffolding | ✅ COMPLETE | `apps/`, `services/`, `packages/`, `infrastructure/` | Turborepo monorepo, docker compose, all workspace packages |
| S02 | Database Schema & Migrations | ✅ COMPLETE | `alembic/versions/` (27 files) | Initial schema: 36 tables. Subsequent migrations add all new tables |
| S03 | Authentication & RBAC | ✅ COMPLETE | `app/auth/` (5 files), `middleware/tenant.py`, `middleware/audit.py` | Clerk JWT, webhook, RBAC with 4 roles, tenant middleware |
| S04 | Design System & Layout Shell | ✅ COMPLETE | `packages/ui/src/`, `components/sidebar.tsx`, `components/topbar.tsx`, `app/(dashboard)/layout.tsx` | Sidebar, topbar, dark mode, responsive |

---

### Phase 1 — Core

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S05 | Data Room Backend | ✅ COMPLETE | `modules/dataroom/` (4 files, **23 endpoints**) | Upload, extraction (Celery), folders, sharing, access logs, AI classification |
| S06 | Data Room Frontend | ✅ COMPLETE | `app/(dashboard)/data-room/page.tsx` | Page exists; component coverage moderate |
| S07 | Dashboards (Ally + Investor) | ✅ COMPLETE | `app/(dashboard)/dashboard/page.tsx`, role-based sidebar nav | Ally/investor/admin nav differentiation in sidebar |
| S08 | Onboarding | ✅ COMPLETE | `modules/onboarding/` (4 files), `app/(onboarding)/onboarding/page.tsx` | Multi-step onboarding, voice input page |
| S09 | Reporting & Analytics | ✅ COMPLETE | `modules/reporting/` (8 files), `generators/` (PDF/PPTX/XLSX) | Report templates, Celery generation tasks, seed templates |
| S10 | Collaboration & Notifications | ✅ COMPLETE | `modules/collaboration/`, `modules/notifications/` (SSE) | Comments, activities, SSE push notifications |

---

### Phase 2 — Investor Track

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S11 | Signal Score Engine | ✅ COMPLETE | `modules/signal_score/` (7 files, **10 endpoints**) | AI scorer, criteria, engine, Celery tasks, improvement guidance |
| S11B | Investor Signal Score | ✅ COMPLETE | `modules/investor_signal_score/` (6 files, **10 endpoints**) | Separate engine and scorer for investor side |
| S12 | Deal Intelligence | ✅ COMPLETE | `modules/deal_intelligence/` (5 files, **8 endpoints**) | Pipeline, discovery, AI screening, investment memos, ElasticSearch |
| S13 | Risk Analysis & Compliance | ✅ COMPLETE | `modules/risk/` (4 files, **12 endpoints**), `modules/compliance/` (4 files, **7 endpoints**) | Five-domain risk, monitoring alerts, audit trail |
| S14 | Investor Matching | ✅ COMPLETE | `modules/matching/` (5 files, **10 endpoints**) | Algorithm, mandates, match messaging, Celery |
| S15 | Valuation Analysis | ✅ COMPLETE | `modules/valuation/` (6 files, **9 endpoints**) | AI assistant, DCF/comparable engine, sensitivity matrix |
| S16 | Marketplace & Tax Credits | ✅ COMPLETE | `modules/marketplace/` (4 files, **12 endpoints**), `modules/tax_credits/` (5 files, **5 endpoints**) | Listings, RFQs, Celery tax credit calculation |

---

### Phase 3 — Ally Track

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S17 | Business Planning | 🟡 PARTIAL | `models/financial.py` (business_plans table), no dedicated module | `business_plans` table exists. No `/business-plan` router or page. Business plan logic may live inside `projects` module as embedded feature |
| S18 | Legal Automation | ✅ COMPLETE | `modules/legal/` (6 files, **13 endpoints**) | Templates, document generation, AI review (Celery), comparison |
| S19 | Carbon Credits | ✅ COMPLETE | `modules/carbon_credits/` (5 files, **8 endpoints**) | Estimator, Celery, project-scoped |
| S20 | Tokenization + Ecosystem + Dev OS + Value Quantifier | ✅ COMPLETE | `modules/tokenization/`, `modules/ecosystem/`, `modules/development_os/`, `modules/value_quantifier/` | 4 modules, all with routers; also `modules/board_advisor/`, `modules/equity_calculator/`, `modules/capital_efficiency/`, `modules/investor_personas/`, `modules/impact/` |

---

### Phase 4 — AI Layer

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S21 | AI Gateway | ✅ COMPLETE | `services/ai-gateway/` (25 files) | litellm routing, rate limiting, token tracking, S33 validation auto-applied, streaming endpoint |
| S22 | Ralph AI | ✅ COMPLETE | `modules/ralph_ai/` (6 files, **6 endpoints**) | Tool-using agent, 22 tools, SSE streaming, context window manager, panel UI |
| S23 | Insurance | 🟡 PARTIAL | `models/advisory.py` (insurance_policies + insurance_quotes tables) | Tables exist, Ralph tool `get_insurance_impact` exists. **No dedicated insurance router or frontend page** |
| S24 | Integration Testing | ✅ COMPLETE | `apps/api/tests/` (17 files), `services/ai-gateway/tests/` (5 files) | **436 passed, 0 failed, 7 skipped.** All previously failing tests fixed. Board advisor, investor personas, equity calculator, capital efficiency, valuation, ralph_ai, matching all passing. |

---

### Phase 5 — Production

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S25 | Security Hardening | ✅ COMPLETE | `middleware/security.py`, `middleware/audit.py`, `middleware/tenant.py`, `core/security.py` | Rate limiting (Redis), body size limits, security headers (CSP/HSTS/XFO), audit log |
| S26 | DevOps & Infrastructure | ✅ COMPLETE | `infrastructure/docker/`, `infrastructure/terraform/`, `infrastructure/scripts/` | Docker Compose, Terraform IaC, deployment scripts |
| S27 | Comprehensive Testing | 🟡 PARTIAL | `apps/api/tests/` | 17 test files, **436 passed, 0 failed**. Covers auth, core, advisory (board_advisor, equity_calculator, capital_efficiency, investor_personas), financial (valuation), AI (ralph_ai), matching. Remaining modules still have no dedicated test files. No frontend tests. |
| S28 | Documentation | ✅ COMPLETE | `docs/` (7 files) | architecture.md, api-reference.md, deployment.md, development.md, modules.md, ralph-ai.md, security.md |

---

### Phase 6–7 — Launch

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S29 | Admin Panel | ✅ COMPLETE | `modules/admin/` (4 files, **11 endpoints**), `modules/admin/prompts/` (**8 endpoints**), `app/(dashboard)/admin/page.tsx` | User management, org management, prompt template admin |
| S30 | White-Label & Branding | ❌ NOT BUILT | — | No white-label module, no tenant branding/custom domain logic found anywhere in codebase |
| S31 | Performance Optimization | 🟡 PARTIAL | `services/analysis_cache.py`, `services/ai-gateway/app/services/rate_limiter.py`, `modules/ralph_ai/context_manager.py` | Redis rate limiting + AI gateway caching in place. S35 analysis cache built but not wired in. No HTTP response caching, no CDN config |
| S32 | Launch Preparation | ❌ NOT BUILT | — | No launch-specific features (beta flags, launch checklist, waitlist, etc.). Docs exist but no launch tooling |

---

### Phase 8 — AI Enhancements

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| S33 | AI Output Validation | ✅ COMPLETE (gateway) | `services/ai-gateway/app/validation.py`, `app/routers/completions.py` | Auto-validates all gateway responses by `task_type`. Returns `validation_repairs` / `validation_warnings`. **Already wired into route_completion()** — zero changes needed in modules |
| S34 | Prompt Registry & Versioning | 🔧 BUILT BUT NOT WIRED | `app/services/prompt_registry.py`, `models/ai.py:PromptTemplate`, migration `d5e6f7a8b9c0_add_prompt_templates.py` | Admin UI for templates exists. **No AI-calling module uses `PromptRegistry.render()`** — all use hardcoded prompt strings |
| S35 | Document Analysis Cache | 🔧 BUILT BUT NOT WIRED | `app/services/analysis_cache.py` | `DocumentAnalysisCache` class complete. **Not imported by any module** — all call AI gateway directly |
| S36 | RAG Pipeline Upgrade | 🔧 BUILT BUT NOT WIRED | `services/ai-gateway/app/services/rag.py`, `app/services/vector_store.py` | RAG pipeline complete in gateway. Ralph AI's `agent.py` passes `rag_context=""` (empty string) — **RAG never actually invoked** |
| S37 | AI Feedback & Quality | 🔧 BUILT BUT NOT WIRED | `modules/ai_feedback/router.py`, `models/ai.py:AIOutputFeedback`, `components/ai-feedback.tsx` | Backend + component exist. **`<AIFeedback>` component not used in any module page** |
| S38 | Context Window Manager | ✅ COMPLETE | `modules/ralph_ai/context_manager.py` | 16K budget, 4 buckets, Haiku summarization fallback. **Used only in Ralph AI** — other AI modules do not use it |
| S39 | Task Batching | 🔧 BUILT BUT NOT WIRED | `services/ai-gateway/app/task_batcher.py` | Batcher complete with 9 batchable task types. **Not called by any module** |
| S40 | Smart Screener | ✅ COMPLETE | `modules/smart_screener/` (4 files, **3 endpoints**), `app/(dashboard)/screener/page.tsx` | NL query → parsed filters → project search. Saved searches. Works standalone |
| S41 | AI Risk Profiling | ✅ COMPLETE | `modules/risk_profile/` (4 files), `models/investor_risk.py:InvestorRiskProfile` | Deterministic scoring (no AI needed). Investor risk questionnaire + scoring |
| S42 | Ralph AI Workflow Tools | ✅ COMPLETE | `modules/ralph_ai/tools.py` | 22 tools including `deep_dive_project`, `portfolio_health_check`, `deal_readiness_check` |
| S43 | Weekly AI Digest | 🟡 PARTIAL | `modules/digest/service.py`, `app/tasks/weekly_digest.py` | Celery task + aggregation service complete. **No HTTP endpoint to trigger/preview digest**. No frontend page |

---

### Phase 9 — Core Investment Workflows

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| F01 | Smart DD Checklist | ✅ COMPLETE | `modules/due_diligence/` (5 files, **8 endpoints**), `app/(dashboard)/projects/[id]/due-diligence/page.tsx` | Templates, checklist instances, Celery auto-generation from doc extractions ✅ |
| F02 | Investor Readiness Certification | 🟡 PARTIAL | `modules/certification/` (4 files, **5 endpoints**), `models/certification.py`, `components/certification-badge.tsx` | Backend integrates with SignalScore ✅. **No dedicated `/certification` page** — badge component exists but not surfaced in nav |
| F03 | Deal Flow Analytics | ✅ COMPLETE | `modules/deal_flow/` (4 files, **7 endpoints**), `models/deal_flow.py:DealStageTransition`, `app/(dashboard)/analytics/deal-flow/page.tsx` | Stage transitions tracked ✅, funnel analytics ✅ |
| F04 | Automated LP Reporting | ✅ COMPLETE | `modules/lp_reporting/` (4 files, **7 endpoints**), `app/(dashboard)/reports/lp/page.tsx` | LP report generation, portfolio metrics ✅ |

---

### Phase 10 — Portfolio Intelligence

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| F05 | ESG Impact Dashboard | 🟡 PARTIAL | `modules/esg/` (4 files, **9 endpoints**), `models/esg.py:ESGMetrics`, `lib/esg.ts` | Backend ✅. **No dedicated `/esg` page** — `lib/esg.ts` helper exists but no route |
| F06 | Comparable Transaction Database | ✅ COMPLETE | `modules/comps/` (4 files, **8 endpoints**), `models/comps.py:ComparableTransaction`, `app/(dashboard)/comps/page.tsx` | Backend ✅, frontend ✅; valuation `ai_assistant.py` has `find_comparables()` method (uses AI suggestions, not the comps table directly) |
| F09 | Multi-Currency Tracking | ✅ COMPLETE | `modules/fx/` (4 files, **4 endpoints**), `models/fx.py:FXRate`, `app/(dashboard)/portfolio/fx/page.tsx`, `app/tasks/fx_rates.py` | FX rates, Celery auto-refresh ✅ |
| F12 | Portfolio Stress Testing | ✅ COMPLETE | `modules/stress_test/` (4 files, **4 endpoints**), `models/stress_test.py:StressTestRun`, `app/(dashboard)/portfolio/stress-test/page.tsx` | Monte Carlo / scenario engine ✅ |

---

### Phase 11 — Collaboration & Communication

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| F07 | Warm Introduction Scoring | ✅ COMPLETE | `modules/warm_intros/` (4 files, **9 endpoints**), `models/connections.py:ProfessionalConnection`, `app/(dashboard)/warm-intros/page.tsx` | Scoring + introduction requests ✅ |
| F08 | Document Version Control | 🟡 PARTIAL | `modules/doc_versions/` (4 files, **5 endpoints**), `models/doc_versions.py:DocumentVersion` | Backend complete. **No dedicated frontend page** — version history not surfaced in data-room or document UI |
| F10 | AI Meeting Prep | ✅ COMPLETE | `modules/meeting_prep/` (4 files, **5 endpoints**), `models/meeting_prep.py:MeetingBriefing`, `app/(dashboard)/projects/[id]/meeting-prep/page.tsx` | AI-generated briefings ✅ |
| F14 | Collaborative Deal Rooms | ✅ COMPLETE | `modules/deal_rooms/` (4 files, **9 endpoints**), `models/deal_rooms.py`, `app/(dashboard)/deal-rooms/page.tsx` | Members, messages, documents, activity feed ✅ |

---

### Phase 12 — Compliance & Infrastructure

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| F11 | Regulatory Calendar | ✅ COMPLETE | `modules/compliance/` (4 files, **7 endpoints**), `models/compliance.py:ComplianceDeadline`, `app/(dashboard)/compliance/page.tsx` | Deadlines, Celery alerts ✅ |
| F13 | API Marketplace / Connectors | ✅ COMPLETE | `modules/connectors/` (6 files, **5 endpoints**), `app/(dashboard)/connectors/page.tsx` | 4 connector implementations (Companies House, ECB, ENTSO-E, OpenWeather) ✅ |
| F16 | Blockchain Audit Trail | 🟡 PARTIAL | `modules/blockchain_audit/` (3 files), `models/blockchain.py:BlockchainAnchor`, `app/tasks/blockchain.py` | Backend ✅, Celery anchoring ✅. **No dedicated frontend page** — blockchain hashes not surfaced in UI |

---

### Phase 13 — Engagement & Onboarding

| Session | Name | Status | Key Files | Notes |
|---------|------|--------|-----------|-------|
| F15 | Watchlists & Alerts | ✅ COMPLETE | `modules/watchlists/` (4 files, **8 endpoints**), `models/watchlists.py`, `app/(dashboard)/watchlists/page.tsx`, `app/tasks/watchlists.py` | Watchlist CRUD + alert generation ✅. Smart screener filters **not yet integrated** |
| F17 | Voice-to-Text Input | ✅ COMPLETE | `modules/voice_input/` (3 files), `app/(dashboard)/onboarding/voice/page.tsx` | Transcription service ✅, onboarding page ✅ |
| F18 | Gamified Score Improvement | ✅ COMPLETE | `modules/gamification/` (3 files, **6 endpoints**), `models/gamification.py`, `app/(dashboard)/gamification/page.tsx` | Badges, quests, leaderboard ✅. **Badge evaluation not triggered from signal_score, onboarding, or project events** |

---

## 3. DATABASE SCHEMA MAP

**Total: 79 tables across 27 migrations**

### Foundation / Auth (S01–S04)
| Table | Key Columns | Module |
|-------|------------|--------|
| `organizations` | id, name, org_type (ally/investor/admin), slug | core |
| `users` | id, org_id, clerk_id, full_name, email, role | core |
| `audit_logs` | id, org_id, user_id, action, resource, changes, ip | middleware |
| `activities` | id, org_id, user_id, type, entity_id, metadata | collaboration |

### Data Room (S05)
| Table | Key Columns |
|-------|------------|
| `documents` | id, org_id, project_id, folder_id, filename, s3_key, status, classification, size |
| `document_folders` | id, org_id, project_id, name, parent_id |
| `document_extractions` | id, document_id, extraction_type, result (JSONB), model_used, tokens_in/out |
| `document_access_logs` | id, document_id, user_id, action, ip |
| `share_links` | id, document_id, token, expires_at, allow_download |
| `document_versions` | id, document_id, version_number, s3_key, created_by (F08) |

### Projects (S05/S07)
| Table | Key Columns |
|-------|------------|
| `projects` | id, org_id, name, type (20 project types), stage, description, location, budget, currency |
| `project_milestones` | id, project_id, title, due_date, status |
| `project_budget_items` | id, project_id, category, amount, currency |
| `transactions` | id, project_id, type, amount, date, description |

### Portfolios & Investments (S11–S15)
| Table | Key Columns |
|-------|------------|
| `portfolios` | id, org_id, name, description |
| `portfolio_holdings` | id, portfolio_id, project_id, allocation_pct, invested_amount |
| `portfolio_metrics` | id, portfolio_id, nav, irr, moic, period_start, period_end |
| `signal_scores` | id, project_id, org_id, overall_score, dimension scores (6), ai_explanation |
| `investor_signal_scores` | id, investor_id, org_id, overall_score, dimension scores |
| `risk_assessments` | id, project_id, portfolio_id, risk_level, dimensions (5), mitigations |
| `investor_risk_profiles` | id, org_id, user_id, risk_tolerance, experience, horizon, questionnaire |
| `investor_mandates` | id, org_id, min_ticket, max_ticket, sectors, geographies, asset_classes |
| `match_results` | id, project_id, investor_id, org_id, score, explanation, status |
| `match_messages` | id, match_id, sender_id, content |
| `valuations` | id, project_id, org_id, methodology, npv, irr, moic, equity_value, comparable_multiples |
| `monitoring_alerts` | id, org_id, portfolio_id, type, severity, resolved_at |

### Marketplace & Tax Credits (S16)
| Table | Key Columns |
|-------|------------|
| `listings` | id, org_id, project_id, listing_type, price, status |
| `rfqs` | id, listing_id, buyer_id, message, status |
| `tax_credits` | id, project_id, org_id, type, estimated_value, status |

### Legal & Compliance (S18, F11)
| Table | Key Columns |
|-------|------------|
| `legal_documents` | id, org_id, project_id, template_id, content, status, jurisdiction |
| `legal_templates` | id, type, jurisdiction, content_template |
| `compliance_deadlines` | id, org_id, deadline_type, due_date, status, recurrence |

### Carbon & Impact (S19, S20)
| Table | Key Columns |
|-------|------------|
| `carbon_credits` | id, project_id, org_id, methodology, estimated_tons, price_per_ton, status |
| `esg_metrics` | id, project_id, org_id, environmental_score, social_score, governance_score, period |

### AI Layer (S21–S22, S33–S38, S43)
| Table | Key Columns |
|-------|------------|
| `ai_conversations` | id, org_id, user_id, title, context_type, context_entity_id, deleted_at |
| `ai_messages` | id, conversation_id, role, content, tool_calls, tool_results, model_used, tokens_in/out |
| `ai_task_logs` | id, org_id, user_id, task_type, model_used, tokens_in/out, latency_ms, status, validated |
| `ai_output_feedback` | id, task_log_id, user_id, rating, edit_distance, accepted, correction |
| `prompt_templates` | id, task_type, version, system_prompt, user_template, is_active, a_b_weight |

### F-Series Tables (F01–F18)
| Table | Key Columns | Feature |
|-------|------------|---------|
| `dd_checklist_templates` | id, name, project_types, items (JSONB) | F01 |
| `dd_project_checklists` | id, project_id, template_id, status | F01 |
| `dd_checklist_items` | id, checklist_id, title, category | F01 |
| `dd_item_statuses` | id, item_id, status, evidence_doc_id, reviewed_by | F01 |
| `investor_readiness_certifications` | id, project_id, tier, score, certified_at, expires_at | F02 |
| `deal_stage_transitions` | id, project_id, investor_id, from_stage, to_stage, notes | F03 |
| `lp_reports` | id, org_id, portfolio_id, period, content (JSONB), status | F04 |
| `comparable_transactions` | id, org_id, project_type, sector, deal_size, irr, moic, year | F06 |
| `introduction_requests` | id, requester_id, target_id, connector_id, project_id, status | F07 |
| `professional_connections` | id, user_id, connected_user_id, strength_score | F07 |
| `fx_rates` | id, base_currency, quote_currency, rate, source, fetched_at | F09 |
| `meeting_briefings` | id, project_id, org_id, counterparty, agenda, ai_summary, key_questions | F10 |
| `stress_test_runs` | id, portfolio_id, org_id, scenario, results (JSONB) | F12 |
| `data_connectors` | id, org_id, connector_type, config (JSONB), last_sync | F13 |
| `org_connector_configs` | id, org_id, connector_id, api_key, settings | F13 |
| `data_fetch_logs` | id, connector_id, status, records_fetched | F13 |
| `deal_rooms` | id, org_id, project_id, name, status | F14 |
| `deal_room_members` | id, room_id, user_id, role | F14 |
| `deal_room_messages` | id, room_id, user_id, content | F14 |
| `deal_room_documents` | id, room_id, document_id | F14 |
| `deal_room_activities` | id, room_id, user_id, type, metadata | F14 |
| `watchlists` | id, org_id, user_id, name, filters (JSONB), is_active | F15 |
| `watchlist_alerts` | id, watchlist_id, project_id, type, is_read | F15 |
| `blockchain_anchors` | id, org_id, entity_type, entity_id, tx_hash, block_number, anchored_at | F16 |
| `badges` | id, code, name, description, criteria (JSONB), icon | F18 |
| `user_badges` | id, user_id, badge_id, earned_at, context | F18 |
| `improvement_quests` | id, project_id, user_id, quest_type, status, xp_reward | F18 |

### Standalone / Advisory
| Table | Module |
|-------|--------|
| `business_plans` | No module — table only |
| `insurance_quotes` | No module — table only |
| `insurance_policies` | No module — table only |
| `board_advisor_profiles` | `board_advisor` |
| `board_advisor_applications` | `board_advisor` |
| `investor_personas` | `investor_personas` |
| `equity_scenarios` | `equity_calculator` |
| `capital_efficiency_metrics` | `capital_efficiency` |
| `comments` | `collaboration` |
| `notifications` | `notifications` |
| `report_templates` | `reporting` |
| `generated_reports` | `reporting` |
| `scheduled_reports` | `reporting` |
| `saved_searches` | `smart_screener` |

---

## 4. API ENDPOINT MAP

**Total: 374 endpoints across 72 routers**

### By Module (endpoints sorted by count)

| Module | Count | Prefix | Notable Endpoints |
|--------|-------|--------|-------------------|
| `dataroom` | 23 | `/documents`, `/folders` | upload, extract, share, classify, bulk |
| `projects` | 17 | `/projects` | CRUD, milestones, budget, trigger signal score |
| `legal` | 13 | `/legal` | templates, generate, AI review, compare |
| `risk` | 12 | `/risk` | dashboard, assess, scenarios, mitigation, alerts |
| `marketplace` | 12 | `/marketplace` | listings CRUD, RFQs |
| `settings` | 11 | `/settings` | org, user, preferences, team |
| `admin` | 11 | `/admin` | users, orgs, analytics, impersonate |
| `admin/prompts` | 8 | `/admin/prompts` | CRUD prompt templates, A/B config |
| `signal_score` | 10 | `/signal-score` | compute, live, gaps, strengths, history |
| `reporting` | 10 | `/reports` | templates, generate, schedule, download |
| `portfolio` | 10 | `/portfolio` | CRUD, metrics, holdings, performance |
| `matching` | 10 | `/matching` | recommendations, mandates, messaging |
| `investor_signal_score` | 10 | `/investor-signal-score` | compute, scores, questionnaire |
| `warm_intros` | 9 | `/warm-intros` | connections, requests, scoring |
| `valuation` | 9 | `/valuations` | suggest, DCF, sensitivity, approve |
| `impact` | 9 | `/impact` | metrics, SDG mapping, categories |
| `deal_rooms` | 9 | `/deal-rooms` | CRUD, members, messages, documents |
| `watchlists` | 8 | `/watchlists` | CRUD, toggle, alerts |
| `due_diligence` | 8 | `/due-diligence` | templates, checklists, items, AI auto-fill |
| `deal_intelligence` | 8 | `/deal-intelligence` | pipeline, discover, screen, memos |
| `comps` | 8 | `/comps` | CRUD, search, statistics |
| `carbon_credits` | 8 | `/carbon` | estimate, CRUD, project-scoped |
| `lp_reporting` | 7 | `/lp-reports` | generate, list, portfolio metrics |
| `compliance` | 7 | `/compliance` | deadlines CRUD, calendar |
| `collaboration` | 7 | `/collaboration` | comments, activities |
| `board_advisor` | 7 | `/board-advisor` | profiles, applications, matches |
| `ralph_ai` | 6 | `/ralph` | conversations CRUD, message, stream (SSE) |
| `notifications` | 6 | `/notifications` | list, read, SSE stream |
| `investor_personas` | 6 | `/investor-personas` | CRUD, match |
| `gamification` | 6 | `/gamification` | badges, quests, leaderboard, evaluate |
| `ai_feedback` | 5 | `/ai-feedback` | rate, track_edit, track_accept, admin_report |
| `tax_credits` | 5 | `/tax-credits` | estimate, CRUD |
| `meeting_prep` | 5 | `/meeting-prep` | generate, list, detail |
| `development_os` | 5 | `/development-os` | milestones, OS dashboard |
| `connectors` | 5 | `/connectors` | CRUD, sync, test |
| `certification` | 5 | `/certification` | check, certify, list, badge |
| `auth` | 5 | `/auth` | webhook, profile, orgs |
| `esg` | 9 | `/esg` | metrics CRUD, scores, categories |
| `deal_flow` | 7 | `/deal-flow` | transitions, funnel, analytics |
| `tokenization` | 4 | `/tokenization` | CRUD, status |
| `stress_test` | 4 | `/stress-test` | run, scenarios, history |
| `fx` | 4 | `/fx` | rates, convert, portfolio exposure |
| `search` | 3 | `/search` | universal search |
| `smart_screener` | 3 | `/screener` | search, saved, save |
| `risk_profile` | 3 | `/risk-profile` | questionnaire, score, profile |
| `doc_versions` | 5 | `/doc-versions` | list, upload, compare, restore |
| `blockchain_audit` | 3 | `/blockchain` | anchor, verify, trail |
| `voice_input` | 2 | `/voice` | transcribe, status |
| `onboarding` | 4 | `/onboarding` | start, step, complete, status |
| `ecosystem` | 5 | `/ecosystem` | partners, network |
| `equity_calculator` | 4 | `/equity` | calculate, scenarios |
| `capital_efficiency` | 4 | `/capital-efficiency` | metrics, benchmarks |
| `value_quantifier` | 4 | `/value-quantifier` | calculate, breakdown |

---

## 5. FRONTEND PAGE MAP

**Total: 48 pages (routes)**

| Route | Page | Status | Notes |
|-------|------|--------|-------|
| `/` | Landing page | ✅ | Root page.tsx |
| `/onboarding` | Onboarding wizard | ✅ | Multi-step |
| `/dashboard` | Main dashboard | ✅ | Role-based widget layout |
| `/dashboard/portfolio` | Portfolio overview | ✅ | Holdings, metrics |
| `/dashboard/portfolio/[id]` | Portfolio detail | ✅ | |
| `/dashboard/portfolio/fx` | FX Exposure | ✅ | F09 |
| `/dashboard/portfolio/stress-test` | Stress Testing | ✅ | F12 |
| `/dashboard/projects` | Project list | ✅ | |
| `/dashboard/projects/new` | Create project | ✅ | |
| `/dashboard/projects/[id]` | Project detail | ✅ | |
| `/dashboard/projects/[id]/signal-score` | Signal Score | ✅ | |
| `/dashboard/projects/[id]/matching` | Investor Matching | ✅ | |
| `/dashboard/projects/[id]/due-diligence` | DD Checklist | ✅ | F01 |
| `/dashboard/projects/[id]/meeting-prep` | Meeting Prep | ✅ | F10 |
| `/dashboard/projects/[id]/carbon` | Carbon Credits | ✅ | S19 |
| `/dashboard/deals` | Deal pipeline | ✅ | S12 |
| `/dashboard/deals/[projectId]` | Deal detail | ✅ | |
| `/dashboard/screener` | Smart Screener | ✅ | S40 |
| `/dashboard/data-room` | Data Room | ✅ | S05/S06 |
| `/dashboard/risk` | Risk Dashboard | ✅ | S13 |
| `/dashboard/marketplace` | Marketplace | ✅ | S16 |
| `/dashboard/marketplace/[listingId]` | Listing detail | ✅ | |
| `/dashboard/reports` | Reports | ✅ | S09 |
| `/dashboard/reports/lp` | LP Reports | ✅ | F04 |
| `/dashboard/settings` | Settings | ✅ | |
| `/dashboard/admin` | Admin Panel | ✅ | S29 |
| `/dashboard/ralph` | Ralph AI Panel | ✅ | S22 — sliding panel in layout |
| `/analytics/deal-flow` | Deal Flow Analytics | ✅ | F03 |
| `/matching` | Matching | ✅ | S14 |
| `/valuations` | Valuations | ✅ | S15 |
| `/comps` | Comparable Transactions | ✅ | F06 |
| `/compliance` | Compliance Calendar | ✅ | F11 |
| `/watchlists` | Watchlists & Alerts | ✅ | F15 |
| `/deal-rooms` | Deal Rooms | ✅ | F14 |
| `/warm-intros` | Warm Introductions | ✅ | F07 |
| `/connectors` | API Connectors | ✅ | F13 |
| `/legal` | Legal Documents | ✅ | S18 |
| `/gamification` | Gamification | ✅ | F18 |
| `/onboarding/voice` | Voice Input | ✅ | F17 |
| `/investor-signal-score` | Investor Signal Score | ✅ | S11B |
| `/tax-credits` | Tax Credits | ✅ | S16 |
| `/tokenization` | Tokenization | ✅ | S20 |
| `/impact` | Impact Metrics | ✅ | S20 |
| `/ecosystem` | Ecosystem | ✅ | S20 |
| `/board-advisor` | Board Advisors | ✅ | S20 |
| `/equity-calculator` | Equity Calculator | ✅ | S20 |
| `/capital-efficiency` | Capital Efficiency | ✅ | S20 |
| `/value-quantifier` | Value Quantifier | ✅ | S20 |
| `/investor-personas` | Investor Personas | ✅ | S20 |
| `/development-os/[projectId]` | Development OS | ✅ | S20 |

### ❌ Missing Frontend Pages (Backend exists, no page)

| Feature | Backend | Missing Page |
|---------|---------|-------------|
| F02: Investor Readiness Certification | `modules/certification/` ✅ | `/certification` or `/projects/[id]/certification` |
| F05: ESG Dashboard | `modules/esg/` ✅ | `/esg` or `/portfolio/esg` |
| F08: Document Version Control | `modules/doc_versions/` ✅ | Embedded version history in data-room |
| F16: Blockchain Audit Trail | `modules/blockchain_audit/` ✅ | `/audit-trail` or admin view |
| S23: Insurance | `models/advisory.py` (tables) | `/insurance` |
| S43: Weekly Digest | `modules/digest/service.py` ✅ | Preview/settings in `/settings` |
| S30: White-Label | ❌ not built | N/A |
| S32: Launch Prep | ❌ not built | N/A |

### Pages Not in Sidebar Navigation
The following pages exist but are **not in any sidebar nav section** (discoverable only by direct URL or deep link):
`/board-advisor`, `/capital-efficiency`, `/comps`, `/connectors`, `/deal-rooms`, `/development-os/[id]`, `/ecosystem`, `/equity-calculator`, `/impact`, `/investor-personas`, `/investor-signal-score`, `/matching`, `/onboarding/voice`, `/tax-credits`, `/tokenization`, `/value-quantifier`, `/warm-intros`, `/watchlists`

---

## 6. AI INTEGRATION MAP

### S33 Validation: Built into gateway — auto-applies to all `task_type` calls ✅
### S34 Prompt Registry: Built but **zero adoption** — all modules use hardcoded prompts

| Module | Model | task_type | Uses S34 Registry | S35 Cached | S37 Feedback UI |
|--------|-------|-----------|-------------------|------------|-----------------|
| `signal_score` | Sonnet 4 | `score_quality`, `score_deal_readiness` | ❌ hardcoded | ❌ | ❌ not in page |
| `ralph_ai` | Sonnet 4 | `chat_with_tools` | ❌ hardcoded | N/A (live chat) | ❌ not in page |
| `deal_intelligence` | Sonnet 4 | `screen_deal`, `generate_memo` | ❌ hardcoded | ❌ | ❌ |
| `risk` | Sonnet 4 | `assess_risk`, `generate_compliance_narrative` | ❌ hardcoded | ❌ | ❌ |
| `valuation` | Sonnet 4 | `suggest_assumptions`, `find_comparables` | ❌ hardcoded | ❌ | ❌ |
| `legal` | Sonnet 4 | `review_contract`, `generate_document` | ❌ hardcoded | ❌ | ❌ |
| `meeting_prep` | Sonnet 4 | `generate_briefing` | ❌ hardcoded | ❌ | ❌ |
| `lp_reporting` | Sonnet 4 | `generate_lp_narrative` | ❌ hardcoded | ❌ | ❌ |
| `due_diligence` | Haiku 4.5 | `auto_fill_checklist` | ❌ hardcoded | ✅ uses doc_extractions | ❌ |
| `dataroom` | Haiku 4.5 | `classify_document`, `extract_kpis` | ❌ hardcoded | ✅ stores in doc_extractions | ❌ |
| `digest` | Haiku 4.5 | `generate_digest` | ❌ hardcoded | N/A | N/A |
| `smart_screener` | Haiku 4.5 | `parse_nl_query` | ❌ hardcoded | ❌ | N/A |
| `esg` | Sonnet 4 | `generate_esg_narrative` | ❌ hardcoded | ❌ | ❌ |
| `comps` | Sonnet 4 | `analyze_transaction` | ❌ hardcoded | ❌ | ❌ |
| `investor_personas` | Sonnet 4 | `generate_persona_summary` | ❌ hardcoded | ❌ | ❌ |
| `matching` | Embeddings | cosine similarity | N/A | ❌ (no embedding cache) | N/A |
| `risk_profile` | None | deterministic | N/A | N/A | N/A |
| `voice_input` | Whisper | transcription | N/A | N/A | N/A |

### Summary of S33–S39 Adoption

| Enhancement | Built | Wired in Gateway | Adopted by Modules |
|------------|-------|-----------------|-------------------|
| S33 Validation | ✅ | ✅ auto in `route_completion()` | ✅ transparent |
| S34 Prompt Registry | ✅ | N/A | ❌ 0/15 AI modules |
| S35 Analysis Cache | ✅ | N/A | ❌ 0/15 AI modules |
| S36 RAG Pipeline | ✅ | ✅ `/search` endpoint | ❌ Ralph passes `rag_context=""` |
| S37 Feedback UI | ✅ | ✅ `/ai-feedback` endpoint | ❌ 0 page uses `<AIFeedback>` |
| S38 Context Window | ✅ | N/A | ✅ Ralph only (1/15) |
| S39 Task Batcher | ✅ | ✅ in gateway | ❌ 0 modules call batcher |

---

## 7. INTEGRATION & DEPENDENCY MAP

| External Service | Module(s) Using It | Status | Notes |
|-----------------|-------------------|--------|-------|
| **Clerk (Auth)** | S03, all routes | ✅ Connected | JWT validation, webhook for user sync |
| **AWS S3 / MinIO** | S05 Data Room, S09 Reports | ✅ Connected | boto3 + presigned URLs |
| **PostgreSQL** | All modules | ✅ Connected | asyncpg, SQLAlchemy 2.0 |
| **Redis** | Rate limiting, Celery broker | ✅ Connected | Redis 5.2 |
| **Anthropic Claude API** | AI Gateway → all AI modules | ✅ Connected | Sonnet 4 primary model |
| **OpenAI API** | AI Gateway → embeddings, matching | ✅ Connected | Embeddings for matching |
| **Celery** | dataroom, signal_score, deal_intelligence, legal, matching, valuation, projects, tax_credits, fx_rates, watchlists, blockchain, digest | ✅ Connected | Celery 5.4 + Redis |
| **ElasticSearch** | deal_intelligence (search), search module | ✅ Connected | ES 8.17 async |
| **Pinecone / Vector Store** | AI Gateway RAG, search | ✅ Configured | `vector_store.py` + gateway `/search` |
| **svix (Clerk webhooks)** | auth/clerk_webhook.py | ✅ Connected | User/org sync |
| **litellm** | AI Gateway routing | ✅ Connected | Multi-model routing |
| **SSE (Server-Sent Events)** | notifications, ralph_ai stream | ✅ Connected | FastAPI `StreamingResponse` |

### Celery Task Registry (`app/tasks/`)

| Task File | Tasks |
|-----------|-------|
| `weekly_digest.py` | `send_weekly_digests` |
| `fx_rates.py` | `refresh_fx_rates` |
| `watchlists.py` | `check_watchlist_triggers` |
| `blockchain.py` | `anchor_entity` |
| `compliance.py` | `check_compliance_deadlines` |
| `screener_notifications.py` | `notify_screener_matches` |

---

## 8. GAP ANALYSIS

### 8A. S33–S43 Integration Check (CRITICAL)

**S33 — AI Output Validation:** ✅ WIRED
The validation is automatically called inside `route_completion()` in the AI gateway whenever `task_type` is provided. All modules that call `/v1/completions` with a `task_type` get validated responses automatically. **No action needed from application modules.**

**S34 — Prompt Registry:** ❌ NOT ADOPTED
`PromptRegistry` class is complete and the `prompt_templates` table exists with an admin UI to manage templates. However, **zero AI-calling modules import or use `PromptRegistry.render()`**. Every module has hardcoded system prompts embedded directly in service/task files. Without adoption, S34 provides no value beyond its admin UI.
**Affected modules (15):** signal_score, risk, valuation, legal, deal_intelligence, meeting_prep, lp_reporting, esg, comps, investor_personas, smart_screener, ralph_ai, digest, dataroom, due_diligence.

**S35 — Document Analysis Cache:** ❌ NOT ADOPTED
`DocumentAnalysisCache` in `app/services/analysis_cache.py` is complete with ANALYSIS_TASK_MAPPING and `get_or_analyze()`. **Not imported or called anywhere** in the application. All modules that analyze documents (signal_score, due_diligence, deal_intelligence, risk) call the AI gateway directly and do redundant analysis on the same documents.

**S36 — RAG Pipeline:** ❌ NOT WIRED FOR RALPH
The RAG infrastructure in the AI gateway is complete (`/search` endpoint, `rag.py`, `vector_store.py`). However, `ralph_ai/agent.py` calls `context_manager.prepare_context(rag_context="")` — passing an empty string. Ralph never retrieves document context via RAG despite having the infrastructure for it. The `search_documents` tool in Ralph's tool set does call the gateway search endpoint (a workaround), but proactive RAG augmentation is absent.

**S37 — AI Feedback:** ❌ NOT WIRED IN FRONTEND
`<AIFeedback>` React component exists and the `/ai-feedback` endpoint works. However, the component is **not used on any module page**. Users cannot rate AI outputs from the signal score, risk, valuation, legal review, or any other AI-generated output page. The admin feedback report endpoint has no data to show.

**S38 — Context Window Manager:** ✅ (Ralph only)
Works correctly for Ralph AI. Other AI modules that build long conversation histories (e.g., deal_intelligence memos, legal reviews) do not use it.

**S39 — Task Batcher:** ❌ NOT ADOPTED
`TaskBatcher` in the AI gateway is complete. The `classify_document` and `extract_kpis` tasks in the dataroom module run individually per document in Celery tasks. **No module routes Haiku calls through the batcher.**

---

### 8B. F-Series Integration Check

| Feature | Depends On | Integration Status |
|---------|-----------|-------------------|
| F01 (DD Checklist) | S05 doc extractions | ✅ `due_diligence/tasks.py` queries `DocumentExtraction` |
| F02 (Certification) | S11 Signal Score | ✅ `certification/service.py` queries `SignalScore` |
| F03 (Deal Flow) | S12/S14 stage transitions | ✅ `deal_flow/service.py` tracks `DealStageTransition` |
| F04 (LP Reports) | S15 portfolio metrics | ✅ `lp_reporting/service.py` queries portfolio data |
| F05 (ESG) | S11 signal score | 🟡 ESG has own metrics; not surfaced in main UI |
| F06 (Comps) | S15 Valuation | 🟡 `valuation/ai_assistant.py` has AI-suggested comparables but does **not query the `comparable_transactions` table** |
| F07 (Warm Intros) | S14 matching | 🟡 Standalone — not linked to match results |
| F08 (Doc Versions) | S05 Data Room | 🟡 Tables exist, backend works, but UI not surfaced |
| F09 (FX) | S15 portfolio | ✅ FX rates used in portfolio holdings valuation |
| F10 (Meeting Prep) | S12/S14 deals | ✅ Briefings tied to project + counterparty context |
| F11 (Compliance) | S13 risk | 🟡 Compliance deadlines standalone; not cross-linked to risk assessments |
| F12 (Stress Test) | S15/portfolio | ✅ Uses portfolio holdings + valuation data |
| F13 (Connectors) | S05/S12 | 🟡 Connectors fetch data; ingestion into dataroom not wired |
| F14 (Deal Rooms) | S12/S14 | 🟡 Standalone; not auto-created from match results |
| F15 (Watchlists) | S40 Smart Screener | ❌ Watchlists store JSONB filters manually; S40's NL→filter parsing **not used** |
| F16 (Blockchain) | All write operations | 🟡 Tasks/module exist; **not triggered from other modules** |
| F17 (Voice) | S08 Onboarding | ✅ Voice page in onboarding flow |
| F18 (Gamification) | S08, S11, S14 | ❌ Badge evaluation endpoint exists but **not called** from signal_score compute, onboarding completion, or match creation |

---

### 8C. Missing or Incomplete Sessions

| Session | Gap | Priority |
|---------|-----|----------|
| **S17 Business Planning** | `business_plans` table exists but no module, router, or frontend page | HIGH |
| **S23 Insurance** | Tables exist in `advisory.py`; no router, no frontend | MEDIUM |
| **S30 White-Label** | Nothing built | LOW |
| **S32 Launch Prep** | Nothing built | LOW |
| **S27 Testing** | 436 passed, 0 failed. Board advisor, investor personas, equity calculator, capital efficiency, valuation, ralph_ai, matching all now tested. ~30 modules still have no dedicated test file. No frontend tests (Vitest unused). | MEDIUM |
| **S43 Digest** | No HTTP endpoint to trigger or preview digest | LOW |

---

### 8D. Dead Code & Unused Modules

| Item | Location | Issue |
|------|----------|-------|
| `_build_messages_for_llm()` | `ralph_ai/agent.py:351` | Duplicate of `_history_to_dicts()`, never called |
| `DocumentAnalysisCache` | `app/services/analysis_cache.py` | Built, not imported anywhere |
| `PromptRegistry` | `app/services/prompt_registry.py` | Admin UI only; never used in AI calls |
| `TaskBatcher` | `services/ai-gateway/app/task_batcher.py` | Built, not called by any module |
| RAG retrieval | `services/ai-gateway/app/services/rag.py` | Pipeline complete but `rag_context=""` in Ralph |
| `seed_prompts.py` | `app/services/seed_prompts.py` | Prompt seeding script — unclear if ever run |

---

### 8E. Broken References

| Issue | Location | Details |
|-------|----------|---------|
| `digest` module has no router | `app/modules/digest/` | Only `service.py` and `__init__.py`. No router registered in `main.py`. No HTTP endpoint to trigger or view digest |
| `voice_input` router thin | `modules/voice_input/router.py` | Only 2 endpoints; no `schemas.py` |
| `gamification` router lacks schemas | `modules/gamification/router.py` | 6 endpoints but no `schemas.py` — inline Pydantic models |
| `blockchain_audit` no schemas | `modules/blockchain_audit/` | Only `router.py` + `service.py`; no `schemas.py` |
| Insurance tables orphaned | `models/advisory.py` | `insurance_quotes`, `insurance_policies` tables — no module, no router |
| Business plan table orphaned | `models/financial.py` | `business_plans` table — no module |

---

### 8F. Frontend Gaps

**Pages with no backend module (theoretical — needs verification):**
None found — all existing frontend pages have corresponding backend modules.

**Backend modules with no frontend page:**

| Module | Backend | Frontend Gap |
|--------|---------|-------------|
| `certification` | ✅ 5 endpoints | No dedicated page — badge component only |
| `esg` | ✅ 9 endpoints | No `/esg` page |
| `doc_versions` | ✅ 5 endpoints | No version history UI in data-room |
| `blockchain_audit` | ✅ 3 endpoints | No audit trail page |
| `digest` | ✅ service + Celery | No digest preview/settings page |
| `insurance` | Tables only | No page |
| `business_plans` | Table only | No page |

**Sidebar navigation gaps:**
18 pages exist but are not linked from the sidebar. Users must navigate by URL. This is a significant UX gap for: warm-intros, watchlists, connectors, deal-rooms, comps, compliance, gamification, equity-calculator, board-advisor, investor-personas, value-quantifier, capital-efficiency, tokenization, development-os, ecosystem, impact, investor-signal-score, matching.

---

### 8G. Test Status — Updated

**Test suite: 436 passed, 0 failed, 7 skipped** (as of 2026-02-28)

**Modules with passing tests:**
- Auth (5 files): dependencies, RBAC, router, tenant, webhook
- Core: health, AI integration (`test_ai_integration.py`)
- Advisory: board_advisor, equity_calculator, capital_efficiency, investor_personas
- Financial: valuation (create, update, approve, sensitivity, report trigger)
- AI: ralph_ai (conversation create, delete, multi-turn coherence)
- Matching: express_interest, match record creation
- Ally journey: end-to-end signal score → gap analysis → improvement plan
- Modules: collaboration, dataroom, onboarding, portfolio, projects, reporting, signal_score
- AI Gateway (5 files): batcher, health, RAG, token_tracker, validation

**No dedicated test file (still ~30 modules):**
admin, ai_feedback, blockchain_audit, carbon_credits, certification, comps, compliance, connectors, deal_flow, deal_intelligence, deal_rooms, development_os, digest, doc_versions, due_diligence, ecosystem, esg, fx, gamification, impact, investor_signal_score, legal, lp_reporting, marketplace, meeting_prep, notifications, risk, risk_profile, search, settings, smart_screener, stress_test, tax_credits, tokenization, value_quantifier, voice_input, warm_intros, watchlists

**No frontend tests:**
No `.spec.tsx` or `.test.tsx` files found. Vitest is installed but not used.

**Key bugs fixed to reach 0 failures:**
- Advisory module PostgreSQL enum binding: added `_lc_enum()` with `values_callable=lambda x: [e.value for e in x]` in `models/advisory.py` (all advisory enums were created lowercase in migrations but SQLAlchemy bound them uppercase by `.name`)
- Migration `aa1122334455`: adds `is_deleted` column to 9 advisory tables (was missing, caused NOT NULL violations)
- `datetime.utcnow()` in `investor_signal_score/service.py` (asyncpg rejects timezone-aware datetimes for TIMESTAMP WITHOUT TIME ZONE)
- `await db.refresh(match)` after `flush()` in `matching/service.py` (MissingGreenlet accessing `updated_at`)
- `.execution_options(populate_existing=True)` in `ralph_ai/service.py` (SQLAlchemy identity map cached empty `messages` list)
- `generated_by` set from `current_user.user_id` in valuation `trigger_report` (was None, violated NOT NULL)
- `GapItem` seeded with all 9 required fields in `test_ai_integration.py` ally journey test

---

### 8H. Security Gaps

| Gap | Severity | Details |
|-----|----------|---------|
| Missing rate limiting on SSE endpoints | MEDIUM | `/notifications/stream` and `/ralph/conversations/{id}/stream` are long-lived connections; not covered by token bucket |
| S34 prompt injection surface | MEDIUM | Prompt templates stored in DB can be edited by admins — no sanitization of template variables before rendering |
| Connector API keys stored in JSONB | MEDIUM | `org_connector_configs.api_key` column — should be encrypted at rest |
| No CSP nonce for inline scripts | LOW | SecurityHeadersMiddleware sets CSP but Next.js inline scripts may violate it in production |
| Voice input endpoint — no size limit on audio | LOW | `voice_input/router.py` — no documented max audio duration/size |
| Public share links — no HMAC verification | LOW | `share_links` table uses random tokens — no signing |

---

### 8I. Migration Status

**28 migrations covering all known tables.**

Potential gaps (tables in models not confirmed in migration names):
- `insurance_quotes`, `insurance_policies` — in `models/advisory.py`; likely in `initial_schema` (36 tables)
- `business_plans` — likely in initial schema
- `comments`, `notifications`, `activities` — likely in initial or `patch1`/`patch2`

**Migrations confirmed by name:**
- Initial schema: 36 tables
- patch1 + patch2: schema updates + new models
- Subsequent 25 migrations: ai_output_feedback, professional_connections, deal_stage_transitions, saved_searches, document_versions, investor_risk_profiles, fx_rates, esg_metrics, document_classification, deal_rooms, data_connectors, watchlists, comparable_transactions, blockchain_anchors, gamification, meeting_briefings, lp_reports, compliance_deadlines, due_diligence_tables, prompt_templates, ai_validation_columns, analysis_types, investor_readiness_certifications, stress_test_runs, deal_rooms

**All 79 tables appear to be covered.**

Migration `aa1122334455` added: `is_deleted` column to 9 advisory tables that were missing it (`board_advisor_profiles`, `board_advisor_applications`, `investor_personas`, `equity_scenarios`, `capital_efficiency_metrics`, `monitoring_alerts`, `investor_signal_scores`, `insurance_quotes`, `insurance_policies`).

---

## 9. IMPROVEMENT RECOMMENDATIONS

### Critical (Fix Before Any New Features)

**1. Wire S34 Prompt Registry into AI Modules (Est: 6–8h)**
All 15 AI-calling modules hardcode prompt strings. The registry + admin UI already exist. The fix is to replace hardcoded prompts with `await registry.render(task_type, variables)` in each module. Start with the highest-value modules: `signal_score/ai_scorer.py`, `risk/service.py`, `valuation/ai_assistant.py`. This unlocks A/B testing, prompt version control, and admin-editable prompts.

**2. Wire S37 AIFeedback Component into Module Pages (Est: 4–6h)**
The `<AIFeedback>` component and `/ai-feedback` endpoint are complete. Add the component to the 10 most important AI output pages: signal-score, risk, valuation, legal, meeting-prep, due-diligence, deal-intelligence, matching, comps, lp-reports. Each page already shows the AI output — it's a one-line addition per page.

**3. Fix Ralph AI RAG Integration (Est: 2–3h)**
`agent.py` passes `rag_context=""` — Ralph never uses document context from the RAG pipeline. The fix is to call the gateway `/search` endpoint at the start of `process_message_stream()` using the user's message as a query and inject results into `prepare_context()`. This is the single highest-impact Ralph improvement.

**4. Wire F18 Gamification Triggers (Est: 3–4h)**
`/gamification/evaluate` endpoint exists. Wire it to be called after: signal_score compute, onboarding completion, first match creation, first DD checklist item completion. These are Celery-task callouts — one line each. Without this, no badges are ever awarded automatically.

**5. Add Missing Frontend Pages (Est: 8–12h)**
Four backend modules have no frontend page: ESG Dashboard, Certification, Document Version History, Blockchain Audit Trail. These are built features invisible to users. ESG and Certification are highest priority (investor-facing).

### High Priority

**6. Wire S35 Analysis Cache (Est: 4–6h)**
Replace direct AI gateway calls in `signal_score`, `deal_intelligence`, and `due_diligence` with `DocumentAnalysisCache.get_or_analyze()`. This eliminates redundant analysis of the same document across modules — the cache stores results in `document_extractions`.

**7. Wire S39 Task Batcher for Haiku Calls (Est: 3–4h)**
The dataroom's `classify_document` Celery task processes one document at a time. Using the batcher for batch uploads would reduce latency and cost. Replace the per-document call in `dataroom/tasks.py` with `batcher.batch_complete("classify_document", [...])`.

**8. Add F15 Smart Screener Integration to Watchlists (Est: 2–3h)**
Watchlists store raw JSONB filters. The smart screener can parse natural-language queries into structured filters. Add an optional `nl_query` parameter to watchlist creation that calls the screener's NL parser to populate `filters`.

**9. Build S17 Business Planning Module (Est: 6–8h)**
The `business_plans` table exists. Build a minimal router (generate AI business plan from project data), service (CRUD), and a `/projects/[id]/business-plan` frontend page. This completes S17.

**10. Add F06 Comps → Valuation Integration (Est: 2–3h)**
`valuation/ai_assistant.py:find_comparables()` uses AI to suggest comparables but never queries the actual `comparable_transactions` table. Wire it to first search the local comps database before falling back to AI suggestions.

**11. Fix Sidebar Navigation (Est: 2–3h)**
18 pages are not linked from the sidebar. Add role-appropriate nav items for the most important ones: warm-intros, watchlists, deal-rooms, comps, compliance, gamification, investor-signal-score.

### Medium Priority

**12. Add Test Coverage for Remaining Untested Modules (Est: 15–20h)**
Board advisor, equity calculator, capital efficiency, investor personas, valuation, ralph_ai, and matching now have passing tests. ~30 modules still have zero dedicated test files. Prioritize: risk, legal, due_diligence, deal_intelligence, carbon_credits, tax_credits. AI modules need mocked gateway responses.

**13. Wire Connector Data Ingestion (Est: 4–6h)**
The 4 connector implementations (Companies House, ECB, ENTSO-E, OpenWeather) fetch external data but don't push it into the dataroom or project models. Add ingestion step after successful fetch.

**14. Build S23 Insurance Module (Est: 4–6h)**
Tables exist. Build a minimal CRUD router for insurance quotes and policies, integrate with the `risk` module dashboard, and add a section in the project/risk page.

**15. Wire F14 Deal Room Auto-Creation (Est: 2h)**
When a match reaches "meeting scheduled" status, auto-create a deal room with both parties as members. One Celery task hook in `matching/service.py`.

**16. Fix F02 Certification Frontend (Est: 2–3h)**
Add a `/projects/[id]/certification` page showing current certification status, tier requirements, and next steps. The `CertificationBadge` component already exists. Add certification status to the project detail page.

### Low Priority / Nice to Have

**17. S43 Digest HTTP Endpoint (Est: 1–2h)**
Add a GET endpoint to preview the weekly digest and a PUT endpoint to opt in/out. Add digest preferences to the settings page.

**18. Build S30 White-Label (Est: 16–24h)**
Custom domain, brand colors, logo, and email templates per organization. Requires tenant config table extension, CNAME validation, and CSS variable injection.

**19. S32 Launch Preparation (Est: 8–12h)**
Beta feature flags, waitlist management, launch checklist tracking, error monitoring integration (Sentry), analytics integration.

**20. Encrypt Connector API Keys (Est: 2–3h)**
Use Fernet or AWS KMS to encrypt `org_connector_configs.api_key` before storing. Add decrypt step in connector service.

**21. Add Frontend Tests (Est: 20–30h)**
Vitest is installed. Add component tests for the most critical UI flows: onboarding, signal score page, Ralph AI panel, data room upload.

**22. S36 RAG Document Sync (Est: 4–6h)**
When a document is uploaded and extracted, automatically embed and index it in the vector store so Ralph can search it. Wire the indexing step into `dataroom/tasks.py` after extraction completes.

---

## 10. METRICS SUMMARY

```
╔══════════════════════════════════════════════════════════════════════╗
║              SCR PLATFORM — STATUS AT A GLANCE (Feb 2026)           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  SESSIONS PLANNED:          62  (S01–S43 + F01–F18)                 ║
║  ─────────────────────────────────────────────────────────────────── ║
║  ✅ Sessions COMPLETE:        41  (66%)                              ║
║  🟡 Sessions PARTIAL:          9  (15%)                              ║
║  🔧 Built But Not Wired:       4  (S34, S35, S36, S39)              ║
║  ❌ NOT BUILT:                 2  (S30, S32)                         ║
║  Sessions with issues:        17  (26% need attention)               ║
║                                                                      ║
║  BACKEND                                                             ║
║  Python Source Files:         353                                    ║
║  Backend Modules:             53                                     ║
║  API Endpoints:               374                                    ║
║  Database Tables:             79                                     ║
║  Alembic Migrations:          27                                     ║
║  Celery Task Files:           6                                      ║
║                                                                      ║
║  FRONTEND                                                            ║
║  TypeScript/React Files:      114                                    ║
║  Frontend Pages:              48                                     ║
║  Frontend Components:         21                                     ║
║  Pages Missing from Sidebar:  18                                     ║
║  Backend Features with No UI: 5                                      ║
║                                                                      ║
║  AI GATEWAY                                                          ║
║  AI Gateway Files:            25                                     ║
║  Total AI Endpoints:          8+                                     ║
║                                                                      ║
║  CODE VOLUME                                                         ║
║  Python Lines (API):          ~60,957                                ║
║  Python Lines (Gateway):      ~3,470                                 ║
║  TypeScript Lines (Web):      ~40,081                                ║
║  Total Lines of Code:         ~104,508                               ║
║                                                                      ║
║  TESTING                                                             ║
║  API Test Files:              17 (436 passed, 0 failed, 7 skipped)   ║
║  Gateway Test Files:          5                                      ║
║  Frontend Test Files:         0 (Vitest installed, not used)         ║
║  Estimated Coverage:          ~25% (advisory + financial + AI added) ║
║                                                                      ║
║  AI INFRASTRUCTURE ADOPTION                                          ║
║  S33 Validation wired:        ✅ 15/15 (transparent in gateway)      ║
║  S34 Prompt Registry used:    ❌ 0/15 AI modules                     ║
║  S35 Analysis Cache used:     ❌ 0/15 AI modules                     ║
║  S36 RAG actually invoked:    ❌ 0/1 (Ralph passes empty context)    ║
║  S37 Feedback buttons live:   ❌ 0/10 key AI output pages            ║
║  S38 Context Manager used:    ✅ 1/1 (Ralph only — correct scope)    ║
║  S39 Task Batcher used:       ❌ 0 modules                           ║
║                                                                      ║
║  F-SERIES INTEGRATION                                                ║
║  F01–F18 with frontend pages: 14/18 (78%)                           ║
║  Missing pages:               4 (F02, F05, F08, F16)                ║
║  F-series backend→backend     10/18 cross-wired (56%)               ║
║                                                                      ║
║  PLATFORM COMPLETENESS (by session):  ~66% fully complete            ║
║  PLATFORM COMPLETENESS (by feature):  ~80% (code exists, gaps wired) ║
║                                                                      ║
║  ESTIMATED REMAINING WORK                                            ║
║  S33–S39 wiring into modules:   ~20–28h                              ║
║  F-series integration fixes:    ~15–20h                              ║
║  Missing frontend pages:        ~8–12h                               ║
║  Sidebar navigation fixes:      ~2–3h                                ║
║  Test coverage (critical mods): ~15–20h (advisory/financial done)    ║
║  S17 Business Planning build:   ~6–8h                                ║
║  S23 Insurance build:           ~4–6h                                ║
║  S30 White-Label (if needed):   ~16–24h                              ║
║  Security fixes (medium prio):  ~4–6h                                ║
║  ─────────────────────────────────────────────────────────────────── ║
║  TOTAL ESTIMATED:               ~95–137h of remaining work           ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## PRIORITY ACTION LIST

### Immediate (do these first — highest ROI, lowest effort)

| # | Action | Est. | Impact |
|---|--------|------|--------|
| 1 | Wire `<AIFeedback>` to 10 AI output pages | 4–6h | S37 fully live |
| 2 | Fix Ralph RAG (`rag_context` → actual search call) | 2–3h | S36 + Ralph quality |
| 3 | Wire gamification triggers (signal_score, onboarding) | 3–4h | F18 actually awards badges |
| 4 | Build ESG Dashboard page (`/esg`) | 2–3h | F05 visible to users |
| 5 | Build Certification page (`/projects/[id]/certification`) | 2–3h | F02 visible to users |

### Short-term (next sprint)

| # | Action | Est. | Impact |
|---|--------|------|--------|
| 6 | Migrate 5 core modules to S34 Prompt Registry | 6–8h | Admin-editable prompts |
| 7 | Wire S35 Analysis Cache for signal_score + deal_intelligence | 4–6h | Eliminate redundant AI calls |
| 8 | Add sidebar nav for 8 most-used orphan pages | 2–3h | UX discoverability |
| 9 | Build Doc Version History UI in data-room | 3–4h | F08 visible |
| 10 | Build Blockchain Audit Trail page | 2–3h | F16 visible |

### Medium-term

| # | Action | Est. | Impact |
|---|--------|------|--------|
| 11 | S17 Business Planning module | 6–8h | Complete S17 |
| 12 | Wire F15 Watchlists with S40 NL filter parsing | 2–3h | Smart watchlists |
| 13 | S39 Task Batcher for dataroom classification | 3–4h | Cost + latency reduction |
| 14 | Wire F06 Comps → Valuation table lookup | 2–3h | Richer valuations |
| 15 | Add tests for risk, legal, deal_intelligence, carbon_credits | 10–15h | Test coverage |

---

*End of SCR Platform Master Blueprint*
*Document auto-generated from codebase scan — 2026-02-28*
