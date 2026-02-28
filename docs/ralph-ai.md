# Ralph AI — Conversational Agent

Ralph is the flagship AI analyst embedded in SCR Platform. It is a tool-using agent backed by Claude Sonnet 4, capable of querying live platform data to answer questions about projects, portfolios, documents, valuations, risk, matching, carbon credits, tax credits, and more.

---

## Architecture

```
User message
  ↓
RalphAgent.process_message() — or process_message_stream()
  ↓
Build context: conversation history + system prompt
  ↓
Loop (max 10 iterations):
  POST /v1/completions → AI Gateway (with tool definitions)
  ├── stop_reason = "tool_calls"
  │   ├── Execute each tool via RalphTools
  │   ├── Append tool_result message
  │   └── Continue loop
  └── stop_reason = "end_turn"
      ↓
      Save user_message + assistant_message to DB
      ↓
      Return (or stream tokens via SSE)
```

### Key classes

| Class | File | Responsibility |
|-------|------|---------------|
| `RalphAgent` | `modules/ralph_ai/agent.py` | Agentic loop, message orchestration, streaming |
| `RalphTools` | `modules/ralph_ai/tools.py` | 19 tool implementations, delegates to service layer |
| `ralph service` | `modules/ralph_ai/service.py` | Conversation/message CRUD |
| `ralph router` | `modules/ralph_ai/router.py` | 6 HTTP endpoints |

---

## System Prompt

Ralph receives a fixed system prompt that defines its persona, capabilities, asset class coverage, communication style, and constraints. Key directives:

- Be concise and data-driven — lead with numbers and facts
- Explain retrieved data in context, not just raw values
- Proactively surface risks and opportunities
- Use markdown (tables, bullet points, bold for key metrics)
- Always cite which tool was used as the data source
- Never fabricate data — acknowledge errors clearly
- Always operate within the user's org context (multi-tenant)

### Asset classes covered

Renewable Energy (solar, wind, hydro, geothermal, biomass) · Infrastructure · Real Estate · Digital Assets / Tokenization · Impact Investing (ESG, SDG) · Climate Finance (carbon markets, green bonds)

---

## Endpoints

All endpoints require authentication (`Authorization: Bearer <token>`).

```
POST   /ralph/conversations              Create a new conversation
GET    /ralph/conversations              List all conversations (most recent first)
GET    /ralph/conversations/{id}         Conversation detail with full message history
DELETE /ralph/conversations/{id}         Delete conversation and all messages
POST   /ralph/conversations/{id}/message Send message (sync — returns full response)
POST   /ralph/conversations/{id}/stream  Send message (SSE streaming)
```

### Create conversation

```http
POST /ralph/conversations
{
  "title": "Portfolio Q1 review",        # optional, default "New conversation"
  "context_type": "portfolio",           # general | project | portfolio | dataroom | deal
  "context_entity_id": "<uuid>"          # optional, pins context to a specific entity
}
```

Response:
```json
{
  "id": "uuid",
  "title": "Portfolio Q1 review",
  "context_type": "portfolio",
  "context_entity_id": "uuid",
  "created_at": "...",
  "updated_at": "..."
}
```

### Send message (sync)

```http
POST /ralph/conversations/{id}/message
{ "content": "What is the IRR on my solar fund?" }
```

Response:
```json
{
  "user_message": { "id": "...", "role": "user", "content": "...", "created_at": "..." },
  "assistant_message": {
    "id": "...",
    "role": "assistant",
    "content": "Your Solar Impact Fund I has an IRR of **14.3%** ...",
    "tool_calls": { "calls": [{"function": {"name": "get_portfolio_metrics"}, ...}] },
    "tool_results": { "results": [{"tool": "get_portfolio_metrics", "result": {...}}] },
    "created_at": "..."
  }
}
```

### Stream message (SSE)

```http
POST /ralph/conversations/{id}/stream
Content-Type: application/json
{ "content": "Analyse my top 3 projects" }
```

Response: `text/event-stream`

```
data: {"type": "user_message", "message_id": "..."}

data: {"type": "tool_call", "name": "get_project_details", "status": "running"}

data: {"type": "tool_call", "name": "get_project_details", "status": "done", "result": {...}}

data: {"type": "token", "content": "Your top three projects are"}

data: {"type": "token", "content": " **Sunstone Solar I**,"}

...

data: {"type": "done", "message_id": "..."}
```

**Frontend streaming pattern** (POST + ReadableStream — not EventSource):

```typescript
const response = await fetch(`${API_URL}/ralph/conversations/${id}/stream`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ content: userMessage }),
});
const reader = response.body!.getReader();
const decoder = new TextDecoder();
let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop() ?? "";
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const event = JSON.parse(line.slice(6));
      if (event.type === "token") appendToken(event.content);
      if (event.type === "done") setAssistantMessageId(event.message_id);
    }
  }
}
```

> Note: `EventSource` only supports GET with no body. Ralph uses `fetch` + `ReadableStream` to support POST with the auth token.

---

## Tool Reference

Ralph has 19 tools. All tools are scoped to the caller's `org_id` — cross-org data is impossible.

### Project Tools

#### `get_project_details`

Retrieve full details for a project.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |

Returns: name, type, status, stage, country, description, target raise, created_at

---

#### `get_signal_score`

Get the latest AI-powered signal score for a project.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |

Returns: overall_score (0–100), tier, dimension_scores (6 dimensions), created_at

---

#### `get_risk_assessment`

Retrieve the latest risk assessment for a project or portfolio.

| Input | Type | Required |
|-------|------|----------|
| `entity_id` | string (UUID) | Yes |
| `entity_type` | `"project"` \| `"portfolio"` | No (default: project) |

Returns: overall_score, risk_level, status, summary

---

### Portfolio Tools

#### `get_portfolio_metrics`

Get portfolio performance metrics.

| Input | Type | Required |
|-------|------|----------|
| `portfolio_id` | string (UUID) | No (defaults to primary portfolio) |

Returns: name, strategy, total_committed, total_deployed, metrics (IRR, MOIC, total_value, num_holdings)

---

### Document Tools

#### `search_documents`

Semantic search over uploaded documents via AI Gateway RAG.

| Input | Type | Required |
|-------|------|----------|
| `query` | string | Yes |
| `project_id` | string (UUID) | No (scope to project) |

Returns: list of matching document excerpts with relevance scores

---

### Financial Tools

#### `run_valuation`

Get the latest valuation for a project.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |
| `method` | `dcf` \| `comparables` \| `replacement_cost` \| `blended` | No |

Returns: method, estimated value, currency, created_at

---

#### `calculate_equity_scenario`

Calculate equity dilution and return scenarios.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |
| `investment_amount` | number (USD) | Yes |
| `equity_percentage` | number | Yes |

Returns: pre/post-money valuation, diluted ownership, return multiples at exit

---

#### `get_capital_efficiency`

Analyse burn rate, runway, and capital deployment efficiency.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |

Returns: burn rate, runway months, deployment efficiency ratio, use-of-proceeds breakdown

---

### Carbon / Tax Tools

#### `get_carbon_estimate`

Get carbon credit estimates and environmental impact metrics.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |

Returns: estimated credits, methodology, verification status, projected revenue

---

#### `get_tax_credit_info`

Get US tax credit eligibility (IRA, ITC, PTC, NMTC, etc.).

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |

Returns: eligible credits, qualification status, estimated value, transfer eligibility

---

### Signal Score Tools

#### `get_investor_signal_score`

Get the investor signal score for the current organisation.

No inputs required.

Returns: overall_score, tier, dimension_scores (6 dimensions), improvement_priority

---

#### `get_improvement_plan`

Get ranked action items to improve signal score or deal readiness.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | No (project-specific plan) |

Returns: ranked list of actions with effort, impact, and category

---

### Matching Tools

#### `find_matching_investors`

Find investors that match the current organisation's projects.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |
| `limit` | integer | No (default: 5) |

Returns: list of matching investors with compatibility scores and mandate alignment

---

#### `find_matching_projects`

Find projects that match the investor's mandate.

| Input | Type | Required |
|-------|------|----------|
| `limit` | integer | No (default: 5) |

Returns: list of matching projects with compatibility scores

---

### Advisory Tools

#### `find_board_advisors`

Find matching board advisors based on expertise.

| Input | Type | Required |
|-------|------|----------|
| `expertise` | string[] | No |

Returns: list of advisor matches with expertise areas and compensation preferences

---

#### `get_risk_mitigation_strategies`

Get risk mitigation strategies for a specific risk type.

| Input | Type | Required |
|-------|------|----------|
| `risk_type` | `market` \| `operational` \| `regulatory` \| `environmental` \| `financial` | Yes |
| `project_id` | string (UUID) | No |

Returns: list of mitigation actions with implementation guidance

---

#### `get_insurance_impact`

Analyse how insurance coverage affects project risk profile and investor returns.

| Input | Type | Required |
|-------|------|----------|
| `project_id` | string (UUID) | Yes |

Returns: coverage summary, risk reduction, impact on projected returns

---

#### `review_legal_document`

Review a legal document and extract key clauses, risks, and recommendations.

| Input | Type | Required |
|-------|------|----------|
| `document_id` | string (UUID) | Yes |

Returns: key clauses, red flags, negotiation recommendations

---

### Generative Tools

#### `generate_report_section`

Generate a written analysis or report section using available data.

| Input | Type | Required |
|-------|------|----------|
| `topic` | string | Yes |
| `context` | string | Yes |
| `section_type` | `analysis` \| `summary` \| `recommendation` | No |

Returns: generated markdown content

> This tool calls the AI Gateway `/v1/completions` endpoint (not the tool-use loop) — it is a generative call within the agentic loop.

---

## Data Model

Conversations and messages are stored in PostgreSQL.

```
AIConversation
  id          UUID PK
  org_id      UUID FK → organizations
  user_id     UUID FK → users
  title       VARCHAR
  context_type  AIContextType (general | project | portfolio | dataroom | deal)
  context_entity_id  UUID | NULL
  is_deleted  BOOLEAN
  created_at  TIMESTAMP
  updated_at  TIMESTAMP

AIMessage
  id          UUID PK
  conversation_id  UUID FK → ai_conversations
  role        AIMessageRole (user | assistant | tool_call)
  content     TEXT
  tool_calls  JSONB  — {"calls": [...]}
  tool_results  JSONB  — {"results": [...]}
  model_used  VARCHAR
  tokens_in   INTEGER
  tokens_out  INTEGER
  created_at  TIMESTAMP
```

---

## AI Gateway Integration

Ralph calls the AI Gateway rather than Claude directly. This keeps all LLM traffic through a single routing point for rate limiting, cost tracking, and model fallback.

| Endpoint | Purpose |
|---------|---------|
| `POST /v1/completions` | Tool-using loop (model: `claude-sonnet-4-20250514`, max 8192 tokens) |
| `POST /v1/completions/stream` | Final response streaming |
| `POST /v1/search` | RAG semantic search over document vectors |

The gateway authenticates all calls with `AI_GATEWAY_API_KEY` (shared secret in `Authorization: Bearer`).

---

## Rate Limits

Ralph endpoints are rate-limited at the middleware layer:

| Endpoint | Limit |
|----------|-------|
| `POST /ralph/*` | 60 requests / minute per IP |
| (AI Gateway) foundation tier | 100 req/hr, 500K tokens/day |
| (AI Gateway) professional tier | 500 req/hr, 2M tokens/day |
| (AI Gateway) enterprise tier | 2000 req/hr, 10M tokens/day |

---

## Frontend Components

```
apps/web/src/components/ralph-ai/
├── ralph-panel.tsx       # Right-side drawer (400px), open/close via Zustand
├── ralph-chat.tsx        # Message thread with tool call indicators + markdown rendering
├── ralph-input.tsx       # Textarea + context selector + send button
└── ralph-suggestions.tsx # Context-aware suggested questions per page

apps/web/src/lib/
├── ralph.ts              # React Query hooks + key factory
└── store.ts              # useRalphStore (isOpen, toggle, activeConversationId)
```

The Ralph panel is toggled from the Topbar's AI button. It renders as a fixed overlay using the `Drawer` component from `@scr/ui`.

### Suggested questions by context

The `RalphSuggestions` component detects the current pathname via `usePathname()` and renders clickable suggestion pills:

| Page | Example suggestions |
|------|-------------------|
| `/projects` | "What is the signal score for my active projects?", "Which projects are ready to fundraise?" |
| `/portfolio` | "What is the IRR across my portfolio?", "Which holdings have the highest risk?" |
| `/marketplace` | "Find investors matching my solar project", "What deals match my mandate?" |
| `/risk` | "Summarise my critical risks", "What mitigation strategies do you recommend?" |
