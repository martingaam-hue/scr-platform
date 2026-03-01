# SCR Platform — HeyGen Production Document
**22 Scenes · ~8:55 Runtime · 1080p / 4K**
Version 1.0 | March 2026

---

## SECTION A — PROJECT SETUP IN HEYGEN STUDIO

Before building scenes, configure these settings once at the project level.

### A1. Project Settings
| Setting | Value |
|---------|-------|
| **Project name** | SCR Platform — Product Demo v1 |
| **Aspect ratio** | 16:9 |
| **Resolution** | 1080p (or 4K if on Enterprise plan) |
| **Background music** | Subtle ambient — set to 15% volume. Mute completely on Scenes 07–15 (AI output moments) |
| **Transition between all scenes** | Cross-dissolve, 0.4 seconds |

### A2. Avatar Settings (apply to ALL scenes)
| Setting | Value |
|---------|-------|
| **Avatar** | Choose a professional male or female presenter with neutral accent. HeyGen recommended: "Tyler" or "Anna" (Business collection) |
| **Voice** | Match avatar. Set speed to **0.92×** (slightly slower than default for gravitas) |
| **Avatar size** | Circle, **180×180px** |
| **Avatar position** | **Bottom-right**, 40px from edge on both sides |
| **Avatar border** | 3px white ring |
| **Avatar background** | None (transparent circle cutout) |

> **Note:** On title/logo slides (Scenes 01–04 and Scene 22), hide the avatar or set to no-speaking scene.

### A3. Brand Colours
| Name | Hex | Use |
|------|-----|-----|
| **Navy** | `#1F3864` | Overlay backgrounds, lower-thirds |
| **Blue** | `#2F5496` | Accent bars, highlight boxes |
| **White** | `#FFFFFF` | All overlay text |
| **Amber** | `#F5A623` | Warning state highlights |
| **Green** | `#27AE60` | Compliant state highlights |

### A4. Text Overlay Style (apply to all lower-thirds)
- **Font:** Inter Bold (or Calibri Bold if Inter unavailable)
- **Size:** 18px label text, 14px sub-label
- **Background:** Navy pill `#1F3864`, 12px border-radius, 16px horizontal padding, 10px vertical padding
- **Text colour:** White `#FFFFFF`
- **Animation:** Fade-in 0.3s, appear 0.5 seconds after the action it labels
- **Position:** Lower-left, 40px from left edge, 60px from bottom

### A5. Logo Placement (Scenes 05 onwards)
- SCR logo PNG (transparent background) — top-left corner
- Size: 120px wide
- Opacity: 80%

---

## SECTION B — SCREEN RECORDING SHOT LIST

Record these clips **before** opening HeyGen. Each clip maps to one or more scenes. Use 1440×900 browser resolution, 90% zoom, 2× cursor size.

| Clip ID | What to Record | Approx Duration | Notes |
|---------|---------------|-----------------|-------|
| **CLIP-01** | Dashboard landing page — slow pan across KPI cards, then sidebar scroll | 25s | Start on KPI cards, end with sidebar fully expanded |
| **CLIP-02** | Sidebar only — slow scroll from top nav item to bottom, all sections visible | 12s | Shows full navigation depth |
| **CLIP-03** | Navigate Projects → click "Helios Solar Portfolio Iberia" → Signal Score page loads showing gauge at 74 | 18s | Let the gauge animation play fully |
| **CLIP-04** | Signal Score dimension bars — click into breakdown, bars animate in one by one, hover Financial Planning to show tooltip | 30s | Slow hover on each bar |
| **CLIP-05** | Signal Score → Gap Analysis tab — list appears with DSCR item highlighted at top | 14s | Pause on DSCR row |
| **CLIP-06** | Signal Score → What Changed timeline — three events visible with explanations | 14s | Slow scroll down the timeline |
| **CLIP-07** | Smart Screener — click into search bar, type the full query slowly (one word per second) | 22s | Type slowly so it reads on screen |
| **CLIP-08** | Smart Screener — results appear, hover first result to expand panel, click Save Search | 20s | Let hover panel fully expand before moving |
| **CLIP-09** | Nordvik Wind Farm II project page — click Ralph icon in topbar, panel slides open from right | 14s | Show the slide-in animation clearly |
| **CLIP-10** | Ralph — click suggested question, streaming response types out, citations [1][2] visible | 22s | Don't cut away until response is fully typed |
| **CLIP-11** | Ralph — click citation [1], data room document opens at exact highlighted clause | 16s | Show the scroll-to-location animation |
| **CLIP-12** | Ralph — type comparison query, "Searching portfolio..." indicator appears, table response | 20s | Show the tool-use indicator clearly |
| **CLIP-13** | Data Room for Adriatic Infrastructure Holdings — folder structure, click financial model XLSX | 18s | Show folder hierarchy before clicking |
| **CLIP-14** | Document detail — Version History tab active, 3 versions with checksums, click Access Log tab | 16s | Pause on checksum values |
| **CLIP-15** | Data room — click Redact on a document, review interface with highlighted entities, click Apply | 18s | Show entity highlights clearly |
| **CLIP-16** | Monitoring dashboard — covenant table with one amber Warning row (DSCR), click into it | 16s | Make the amber badge visible before clicking |
| **CLIP-17** | Covenant detail — DSCR trend chart showing 6-month downward trend | 14s | Let chart animate in |
| **CLIP-18** | Benchmarks page — quartile chart showing IRR at 68th percentile | 10s | |
| **CLIP-19** | Reports → LP Reports → click Generate Report → select template, fund, PDF → click Generate | 20s | Slow deliberate clicks |
| **CLIP-20** | Report preview renders, scroll slowly through pages showing charts and tables | 22s | Slow scroll, good quality layout visible |
| **CLIP-21** | Report scheduling modal — show frequency options | 10s | |
| **CLIP-22** | Admin → AI Costs dashboard — cost table with provider breakdown | 12s | |
| **CLIP-23** | Admin → Prompt Templates — template list, click into one to show editor | 12s | |
| **CLIP-24** | Admin → Feature Flags — toggle list | 8s | |
| **CLIP-25** | Settings → Custom Domain — verification interface | 8s | |
| **CLIP-26** | Dashboard — final wide shot, pull back slowly | 15s | Same as CLIP-01 but slower |

---

## SECTION C — THE 22 SCENES

Each scene includes: duration, background, avatar script (TTS-optimised), overlays, and HeyGen setup notes.

---

### SCENE 01 — Pain Point 1
**Duration:** 4 seconds
**Background:** Solid black `#0A0A0A`
**Avatar:** Hidden

**Centre text (full screen, white, 32px bold, fade in 0.5s, fade out at 3.5s):**
```
"Every week, a fund manager loses a deal
because their due diligence took too long."
```

**HeyGen setup:** Add a Text element. Centre-align. White `#FFFFFF`. Font size 32. Set element animation to Fade In. No avatar on this scene.

---

### SCENE 02 — Pain Point 2
**Duration:** 4 seconds
**Background:** Solid black `#0A0A0A`
**Avatar:** Hidden

**Centre text:**
```
"Every quarter, an LP receives a report
that took their analyst two weeks to assemble."
```

---

### SCENE 03 — Pain Point 3
**Duration:** 4 seconds
**Background:** Solid black `#0A0A0A`
**Avatar:** Hidden

**Centre text:**
```
"Every day, a covenant breach builds — undetected —
in a spreadsheet no one is watching."
```

---

### SCENE 04 — Logo Reveal
**Duration:** 8 seconds
**Background:** Solid `#0A0A0A`
**Avatar:** Hidden

**Elements:**
1. SCR logo — centre screen, fade in at 1s, scale from 90% to 100% over 0.8s
2. Title text below logo (white, 22px, fade in at 2.5s):
   ```
   SCR Platform
   ```
3. Subtitle text (grey `#AAAAAA`, 14px italic, fade in at 3.5s):
   ```
   The AI-Native Operating System for Sustainable Infrastructure Investment
   ```

---

### SCENE 05 — Dashboard Overview
**Duration:** 25 seconds
**Background:** CLIP-01 (dashboard pan)
**Avatar:** Active, bottom-right

**Avatar script (paste exactly as written):**
> "This is the SCR Platform. A single operating system for every stage of the investment lifecycle. From the first deal screen to LP reporting, every workflow lives here."

**Overlay 1** — appears at 3s:
```
[pill] Live Portfolio Data
```
Position: lower-left

**Overlay 2** — appears at 10s:
```
[pill] Active Deals · Portfolio IRR · Covenants · Documents
```

**Overlay 3** — appears at 18s:
```
[pill] Every number is live — not a weekly extract
```

---

### SCENE 06 — Navigation Depth
**Duration:** 18 seconds
**Background:** CLIP-02 (sidebar scroll)
**Avatar:** Active, bottom-right

**Avatar script:**
> "The platform covers eighty-one distinct modules. Deal origination, due diligence, portfolio monitoring, covenant tracking, and automated LP reporting. We'll walk through the ones that matter most."

**Overlay** — appears at 4s:
```
[pill] 81 Modules · Single Platform
```

---

### SCENE 07 — Signal Score Introduction
**Duration:** 22 seconds
**Background:** CLIP-03 (navigate to Signal Score, gauge at 74)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Every project on SCR receives a Signal Score. An AI-calculated viability rating that tells an investor, in a single number, how investment-ready this project is. Seventy-four out of one hundred. But the number alone tells you nothing. The value is in what's underneath it."

**Overlay 1** — appears at 8s, large, centred above the gauge:
```
[pill, larger — 22px] Signal Score™  74 / 100
```

**Overlay 2** — appears at 16s:
```
[pill] Helios Solar Portfolio Iberia
```

---

### SCENE 08 — Signal Score Dimensions
**Duration:** 32 seconds
**Background:** CLIP-04 (dimension bars + tooltip hover)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Six dimensions. Forty-eight specific criteria. The platform has read every document in this project's data room — financial models, technical studies, legal agreements, ESG reports — and assessed each one against its standard. Hover into any dimension and you see the criterion-level breakdown. This project scores well on its revenue model and PPA structure. But the debt service coverage analysis hasn't been uploaded yet. That's what's holding the financial planning score down."

**Overlay 1** — appears at 2s:
```
[pill] 6 Dimensions · 48 Criteria
```

**Overlay 2** — appears at 18s (when hovering Financial Planning):
```
[pill, amber #F5A623 background] ⚠ Missing: DSCR Analysis
```

---

### SCENE 09 — Gap Analysis
**Duration:** 14 seconds
**Background:** CLIP-05 (Gap Analysis tab)
**Avatar:** Active, bottom-right

**Avatar script:**
> "The Gap Analysis turns the score into an action plan. Uploading the DSCR analysis would add nine points to financial planning. That's the single highest-impact action this developer can take today."

**Overlay** — appears at 4s:
```
[pill] +9 pts if DSCR uploaded
```

---

### SCENE 10 — What Changed Timeline
**Duration:** 16 seconds
**Background:** CLIP-06 (What Changed timeline)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Every score change is explained. Three weeks ago, the team uploaded the grid connection study. That added eleven points to project viability. The developer can see exactly what moved the needle, and why."

**Overlay** — appears at 6s:
```
[pill] Explainable AI — Every change traced to its source
```

---

### SCENE 11 — Smart Screener Query
**Duration:** 22 seconds
**Background:** CLIP-07 (typing the query)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Finding deals shouldn't require a filter panel. The Smart Screener accepts plain English. Watch."

**Overlay 1** — appears at 1s:
```
[pill] Smart Screener — Natural Language Search
```

**Overlay 2** — appears at 8s (when typing begins), larger text, above the search bar:
```
"Operational solar or wind projects in Southern Europe
with equity IRR above 8% and capacity above 30MW"
```
Style: Navy background, white text, 16px, positioned above the search field

---

### SCENE 12 — Screener Results
**Duration:** 22 seconds
**Background:** CLIP-08 (results appear, hover, save search)
**Avatar:** Active, bottom-right

**Avatar script:**
> "The AI reads that query, extracts the intent, and returns ranked results in under a second. Drawing on the full text of every project document in the platform. Not just headline metadata. Save the search, and the platform will notify you the moment a new project matching these criteria is added."

**Overlay 1** — appears at 2s:
```
[pill] Results ranked by relevance
```

**Overlay 2** — appears at 16s (on Save Search click):
```
[pill] Never miss a deal that fits your mandate
```

---

### SCENE 13 — Ralph Introduction
**Duration:** 22 seconds
**Background:** CLIP-09 (Ralph panel slides open)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Ralph is SCR's AI research assistant. He can answer complex investment questions by reasoning across every document in the platform. Not a generic chatbot. An analyst who has read everything you've uploaded. Watch what happens when we ask about legal risk."

**Overlay** — appears at 8s:
```
[pill] Ralph — AI Research Assistant
```

**Second overlay** — appears at 15s:
```
[pill] RAG-powered · Grounded in your documents
```

---

### SCENE 14 — Ralph Citations
**Duration:** 28 seconds
**Background:** CLIP-10 (question typed, response streams, citations visible)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Notice the citations. Every claim Ralph makes is sourced from a specific document. This isn't a hallucination. It's a traceable analysis. Click citation one, and the platform takes you directly to the source. The exact paragraph in the original document that Ralph drew from. Every AI output on this platform works this way. You can verify every conclusion."

**Overlay 1** — appears at 5s (when response starts typing):
```
[pill] Sources cited automatically
```

**Overlay 2** — appears at 18s (when document opens at cited clause):
```
[pill] Click any citation → jumps to exact source paragraph
```

**Note:** This scene covers both CLIP-10 and CLIP-11. Splice them together in HeyGen or use as background video that transitions mid-scene.

---

### SCENE 15 — Ralph Portfolio Comparison
**Duration:** 22 seconds
**Background:** CLIP-12 (comparison query, tool indicator, table response)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Ralph has access to nineteen specialised tools that give him direct access to platform data. Signal scores, portfolio metrics, valuations, carbon credit calculations, legal document analysis. He's not just summarising text. He's computing answers from live data."

**Overlay 1** — appears at 4s (when "Searching portfolio..." shows):
```
[pill] 19 Tools · Live Platform Data
```

**Overlay 2** — appears at 14s (when comparison table appears):
```
[pill] Cross-portfolio analysis in seconds
```

---

### SCENE 16 — Data Room & Document Intelligence
**Duration:** 22 seconds
**Background:** CLIP-13 (data room folder structure, click financial model)
**Avatar:** Active, bottom-right

**Avatar script:**
> "The data room is where deals live. But unlike a traditional VDR, every document here is actively processed by the platform's AI the moment it's uploaded. When this financial model was uploaded, the platform automatically classified it, extracted forty-three key metrics — IRR, NPV, DSCR, revenue by year — and made them available for scoring, benchmarking, and Ralph's analysis. No manual tagging. No copy-paste."

**Overlay 1** — appears at 3s:
```
[pill] AI processes every document on upload
```

**Overlay 2** — appears at 12s (when clicking into the document):
```
[pill] 43 metrics extracted automatically
```

---

### SCENE 17 — Version History, Access Log & Redaction
**Duration:** 28 seconds
**Background:** CLIP-14 + CLIP-15 (version history → access log → redaction)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Full version control on every document. SHA-256 checksums for integrity verification. The Access Log shows exactly which investor viewed which version, and when. That's the engagement data that tells you whether an LP has actually read the materials before a call. And before sharing externally, the redaction tool runs an AI scan for sensitive entities. The AI flags every candidate for human review. Approved redactions are applied, a clean PDF is generated, and the entire decision is in the audit trail."

**Overlay 1** — appears at 4s (on Version History tab):
```
[pill] SHA-256 checksums · Full version history
```

**Overlay 2** — appears at 13s (on Access Log tab):
```
[pill] Who viewed · Which version · How long
```

**Overlay 3** — appears at 22s (on redaction review):
```
[pill] AI-assisted redaction · Human review required
```

---

### SCENE 18 — Covenant Monitoring
**Duration:** 28 seconds
**Background:** CLIP-16 + CLIP-17 + CLIP-18 (covenant table → trend chart → benchmark)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Portfolio management is only as good as its ability to catch problems early. SCR checks every investment covenant every night. This project's Debt Service Coverage Ratio dropped below the warning threshold three nights ago. The portfolio manager received an alert the morning it happened. Not in the next quarterly report. The trend chart shows six months of deterioration. Without this, that conversation happens at the board meeting, not three weeks before it. And every metric is benchmarked. This project's IRR sits at the sixty-eighth percentile versus comparable solar assets from the same vintage year."

**Overlay 1** — appears at 4s (on covenant table):
```
[pill] Daily automated covenant checks
```

**Overlay 2** — appears at 10s (on amber Warning badge):
```
[pill, amber background #F5A623] ⚠  Warning — DSCR below 1.25×
```

**Overlay 3** — appears at 18s (on trend chart):
```
[pill] Compliant → Warning → Breach
```

**Overlay 4** — appears at 24s (on benchmark chart):
```
[pill] 68th percentile vs. peer group
```

---

### SCENE 19 — LP Reporting
**Duration:** 38 seconds
**Background:** CLIP-19 + CLIP-20 + CLIP-21 (generate → preview → schedule)
**Avatar:** Active, bottom-right

**Avatar script:**
> "Quarterly LP reporting is the most time-consuming recurring task in fund management. SCR eliminates most of it. Select the template, select the fund, choose the output format. The platform draws from live data — portfolio performance, benchmark positions, covenant status, pacing analysis, ESG scores — and generates the report. In under ten seconds. A publication-quality quarterly report, compiled automatically. The same report that previously took a two-person analyst team two weeks now takes seconds. Set a schedule once, and the platform generates and distributes the report automatically every quarter."

**Overlay 1** — appears at 5s (on template selection):
```
[pill] 8 templates · PDF · Excel · PowerPoint
```

**Overlay 2** — appears at 16s (on progress indicator):
```
[pill] Generating from live platform data...
```

**Overlay 3** — appears at 22s (on report preview):
```
[pill] Publication-quality · Auto-compiled · Always current
```

**Overlay 4** — appears at 34s (on scheduling modal):
```
[pill] PDF · Excel · PowerPoint — All formats, all automated
```

---

### SCENE 20 — Enterprise & Admin
**Duration:** 30 seconds
**Background:** CLIP-22 + CLIP-23 + CLIP-24 + CLIP-25 (admin panels)
**Avatar:** Active, bottom-right

**Avatar script:**
> "For platform administrators, everything is visible and controllable. The AI cost dashboard shows real-time spend by provider and task type across every organisation on the platform. Every AI behaviour is managed through the Prompt Registry. When an analyst needs the investment memo template to emphasise climate risk differently, an admin changes the prompt here. No code. No redeployment. Live in minutes. Features can be toggled globally or per organisation. And for enterprise clients, the platform deploys under their own brand and domain."

**Overlay 1** — appears at 3s (on AI Costs):
```
[pill] Real-time AI spend by provider & task type
```

**Overlay 2** — appears at 14s (on Prompt Templates):
```
[pill] Prompt Registry — Edit AI behaviour without code
```

**Overlay 3** — appears at 22s (on Custom Domain):
```
[pill] White-label · Custom domain · Auto-SSL
```

---

### SCENE 21 — Closing Monologue
**Duration:** 35 seconds
**Background:** CLIP-26 (dashboard final wide shot, slow pan)
**Avatar:** Active, bottom-right

**Avatar script:**
> "SCR Platform is not a suite of tools bolted together. It's a single operating system where every component shares the same data foundation, and reinforces every other. When a document is uploaded, the score updates. When the score changes, the portfolio manager is notified. When the covenant breaches, the LP report already reflects it. When the analyst asks Ralph a question, the answer cites the document that was uploaded this morning. Eighty-one application modules. One hundred and seventy-six data models. Five AI providers. Twenty-five automated workflows running every day. This is what AI-native infrastructure investment looks like."

**Overlay 1** — appears at 18s:
```
[pill] 81 Modules · 176 Data Models · 5 AI Providers · 25 Automations
```

**Overlay 2** — appears at 30s, larger, centred bottom:
```
[pill, larger 20px] The AI-Native Operating System for Sustainable Infrastructure Investment
```

---

### SCENE 22 — End Card
**Duration:** 10 seconds
**Background:** Solid `#0A0A0A`
**Avatar:** Hidden

**Elements:**
1. SCR logo — centre screen, fade in at 0.5s
2. CTA text below logo (white, 16px, fade in at 2s):
   ```
   Request a live demo
   scr-platform.com
   ```
3. Subtle divider line between logo and CTA

**Music:** Fade to complete silence at second 2 of this scene.

---

## SECTION D — SCENE SUMMARY TABLE

| # | Scene Name | Duration | Clip(s) | Key Overlay |
|---|-----------|----------|---------|-------------|
| 01 | Pain Point 1 | 4s | — | Text slide |
| 02 | Pain Point 2 | 4s | — | Text slide |
| 03 | Pain Point 3 | 4s | — | Text slide |
| 04 | Logo Reveal | 8s | — | Logo + tagline |
| 05 | Dashboard Overview | 25s | CLIP-01 | "Live Portfolio Data" |
| 06 | Navigation Depth | 18s | CLIP-02 | "81 Modules" |
| 07 | Signal Score Intro | 22s | CLIP-03 | "Signal Score™ 74/100" |
| 08 | Score Dimensions | 32s | CLIP-04 | "6 Dimensions · 48 Criteria" |
| 09 | Gap Analysis | 14s | CLIP-05 | "+9 pts if DSCR uploaded" |
| 10 | What Changed | 16s | CLIP-06 | "Explainable AI" |
| 11 | Screener Query | 22s | CLIP-07 | Query text overlay |
| 12 | Screener Results | 22s | CLIP-08 | "Never miss a deal" |
| 13 | Ralph Intro | 22s | CLIP-09 | "RAG-powered" |
| 14 | Ralph Citations | 28s | CLIP-10+11 | "Click citation → exact source" |
| 15 | Ralph Comparison | 22s | CLIP-12 | "19 Tools · Live Data" |
| 16 | Data Room | 22s | CLIP-13 | "43 metrics extracted" |
| 17 | Versions & Redaction | 28s | CLIP-14+15 | "Human review required" |
| 18 | Covenant Monitoring | 28s | CLIP-16+17+18 | Amber warning badge |
| 19 | LP Reporting | 38s | CLIP-19+20+21 | "Two weeks → ten seconds" |
| 20 | Enterprise & Admin | 30s | CLIP-22+23+24+25 | "Edit AI without code" |
| 21 | Closing | 35s | CLIP-26 | Stats pill |
| 22 | End Card | 10s | — | Logo + CTA |
| | **TOTAL** | **~8:54** | | |

---

## SECTION E — HEYGEN STEP-BY-STEP WORKFLOW

1. **Go to** [app.heygen.com](https://app.heygen.com) → **New Video → Blank**
2. **Upload all 26 screen recording clips** to HeyGen Media Library first
3. **Create 22 slides** in order — for each slide:
   - Set background (solid colour or upload the clip)
   - Add avatar (bottom-right circle, 180px) — hide on Scenes 01–04 and 22
   - Paste the avatar script from Section C
   - Add text overlays per the overlay specs
4. **Set transitions** — cross-dissolve 0.4s between every scene
5. **Add background music** — upload a subtle ambient track, set to 15% volume, mute on Scenes 07–15
6. **Preview** — watch through once to check timing sync
7. **Generate** — allow 15–30 minutes for render at 1080p
8. **Download** — MP4, H.264, 1080p or 4K

---

## SECTION F — AVATAR SCRIPT FULL TEXT (copy-paste ready)

Paste each block into the corresponding HeyGen scene's avatar script field.

**SCENE 05:**
This is the SCR Platform. A single operating system for every stage of the investment lifecycle. From the first deal screen to LP reporting, every workflow lives here.

**SCENE 06:**
The platform covers eighty-one distinct modules. Deal origination, due diligence, portfolio monitoring, covenant tracking, and automated LP reporting. We'll walk through the ones that matter most.

**SCENE 07:**
Every project on SCR receives a Signal Score. An AI-calculated viability rating that tells an investor, in a single number, how investment-ready this project is. Seventy-four out of one hundred. But the number alone tells you nothing. The value is in what's underneath it.

**SCENE 08:**
Six dimensions. Forty-eight specific criteria. The platform has read every document in this project's data room, financial models, technical studies, legal agreements, ESG reports, and assessed each one against its standard. Hover into any dimension and you see the criterion-level breakdown. This project scores well on its revenue model and PPA structure. But the debt service coverage analysis hasn't been uploaded yet. That's what's holding the financial planning score down.

**SCENE 09:**
The Gap Analysis turns the score into an action plan. Uploading the DSCR analysis would add nine points to financial planning. That's the single highest-impact action this developer can take today.

**SCENE 10:**
Every score change is explained. Three weeks ago, the team uploaded the grid connection study. That added eleven points to project viability. The developer can see exactly what moved the needle, and why.

**SCENE 11:**
Finding deals shouldn't require a filter panel. The Smart Screener accepts plain English. Watch.

**SCENE 12:**
The AI reads that query, extracts the intent, and returns ranked results in under a second. Drawing on the full text of every project document in the platform. Not just headline metadata. Save the search, and the platform will notify you the moment a new project matching these criteria is added.

**SCENE 13:**
Ralph is SCR's AI research assistant. He can answer complex investment questions by reasoning across every document in the platform. Not a generic chatbot. An analyst who has read everything you've uploaded. Watch what happens when we ask about legal risk.

**SCENE 14:**
Notice the citations. Every claim Ralph makes is sourced from a specific document. This isn't a hallucination. It's a traceable analysis. Click citation one, and the platform takes you directly to the source. The exact paragraph in the original document that Ralph drew from. Every AI output on this platform works this way. You can verify every conclusion.

**SCENE 15:**
Ralph has access to nineteen specialised tools that give him direct access to platform data. Signal scores, portfolio metrics, valuations, carbon credit calculations, legal document analysis. He's not just summarising text. He's computing answers from live data.

**SCENE 16:**
The data room is where deals live. But unlike a traditional VDR, every document here is actively processed by the platform's AI the moment it's uploaded. When this financial model was uploaded, the platform automatically classified it, extracted forty-three key metrics, IRR, NPV, DSCR, revenue by year, and made them available for scoring, benchmarking, and Ralph's analysis. No manual tagging. No copy-paste.

**SCENE 17:**
Full version control on every document. SHA-256 checksums for integrity verification. The Access Log shows exactly which investor viewed which version, and when. That's the engagement data that tells you whether an LP has actually read the materials before a call. And before sharing externally, the redaction tool runs an AI scan for sensitive entities. The AI flags every candidate for human review. Approved redactions are applied, a clean PDF is generated, and the entire decision is in the audit trail.

**SCENE 18:**
Portfolio management is only as good as its ability to catch problems early. SCR checks every investment covenant every night. This project's Debt Service Coverage Ratio dropped below the warning threshold three nights ago. The portfolio manager received an alert the morning it happened. Not in the next quarterly report. The trend chart shows six months of deterioration. Without this, that conversation happens at the board meeting, not three weeks before it. And every metric is benchmarked. This project's IRR sits at the sixty-eighth percentile versus comparable solar assets from the same vintage year.

**SCENE 19:**
Quarterly LP reporting is the most time-consuming recurring task in fund management. SCR eliminates most of it. Select the template, select the fund, choose the output format. The platform draws from live data, portfolio performance, benchmark positions, covenant status, pacing analysis, ESG scores, and generates the report. In under ten seconds. A publication-quality quarterly report, compiled automatically. The same report that previously took a two-person analyst team two weeks now takes seconds. Set a schedule once, and the platform generates and distributes the report automatically every quarter.

**SCENE 20:**
For platform administrators, everything is visible and controllable. The AI cost dashboard shows real-time spend by provider and task type across every organisation on the platform. Every AI behaviour is managed through the Prompt Registry. When an analyst needs the investment memo template to emphasise climate risk differently, an admin changes the prompt here. No code. No redeployment. Live in minutes. Features can be toggled globally or per organisation. And for enterprise clients, the platform deploys under their own brand and domain.

**SCENE 21:**
SCR Platform is not a suite of tools bolted together. It's a single operating system where every component shares the same data foundation, and reinforces every other. When a document is uploaded, the score updates. When the score changes, the portfolio manager is notified. When the covenant breaches, the LP report already reflects it. When the analyst asks Ralph a question, the answer cites the document that was uploaded this morning. Eighty-one application modules. One hundred and seventy-six data models. Five AI providers. Twenty-five automated workflows running every day. This is what AI-native infrastructure investment looks like.
