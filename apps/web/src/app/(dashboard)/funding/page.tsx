"use client";

import React from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Clock,
  Download,
  FileText,
  Landmark,
  Target,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  InfoBanner,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  cn,
} from "@scr/ui";
import { useProjects, useProjectStats, formatCurrency, type ProjectResponse } from "@/lib/projects";

// ── Mock data — project-holder / ally perspective ─────────────────────────────

const PORTFOLIO_SUMMARY = {
  total_needed: 285_000_000,
  secured: 47_000_000,
  in_discussion: 118_000_000,
  gap: 120_000_000,
  active_investors: 14,
  term_sheets: 3,
  next_close: "Q3 2025",
  projects_raising: 5,
};

const INVESTOR_PIPELINE = [
  { investor: "Nordic Green Capital", type: "Equity", ticket: 25_000_000, stage: "term_sheet", project: "Solvatten Solar 80MW", last_contact: "2 days ago", next_action: "Legal review" },
  { investor: "EIB Infrastructure", type: "Senior Debt", ticket: 40_000_000, stage: "due_diligence", project: "Väst Wind 120MW", last_contact: "1 week ago", next_action: "Site visit Apr 28" },
  { investor: "Meridian Impact Fund", type: "Equity", ticket: 18_000_000, stage: "term_sheet", project: "BioCircle W2E", last_contact: "3 days ago", next_action: "Term negotiation" },
  { investor: "Climate Finance Partners", type: "Equity", ticket: 15_000_000, stage: "first_meeting", project: "Solvatten Solar 80MW", last_contact: "5 days ago", next_action: "Follow-up call" },
  { investor: "European Investment Bank", type: "Senior Debt", ticket: 55_000_000, stage: "due_diligence", project: "Väst Wind 120MW", last_contact: "2 weeks ago", next_action: "Financial model review" },
  { investor: "Triodos Investment Mgmt", type: "Equity", ticket: 12_000_000, stage: "screening", project: "Coastal Biogas", last_contact: "1 week ago", next_action: "ESG questionnaire" },
  { investor: "Green Transition Fund", type: "Mezzanine", ticket: 8_000_000, stage: "screening", project: "BioCircle W2E", last_contact: "3 weeks ago", next_action: "Intro call scheduled" },
  { investor: "Skandia Livförsäkring", type: "Senior Debt", ticket: 30_000_000, stage: "first_meeting", project: "Nordic Hydro Rehab", last_contact: "1 week ago", next_action: "IM follow-up" },
];

const CAPITAL_STACK = [
  { tranche: "Senior Debt", target: 95_000_000, secured: 0, in_discussion: 55_000_000, color: "#3B82F6" },
  { tranche: "Mezzanine", target: 30_000_000, secured: 0, in_discussion: 8_000_000, color: "#8B5CF6" },
  { tranche: "Equity — Third Party", target: 85_000_000, secured: 22_000_000, in_discussion: 45_000_000, color: "#4F46E5" },
  { tranche: "Equity — Own Capital", target: 35_000_000, secured: 20_000_000, in_discussion: 0, color: "#6366F1" },
  { tranche: "Grants & Subsidies", target: 40_000_000, secured: 5_000_000, in_discussion: 10_000_000, color: "#10B981" },
];

const FUNDING_MILESTONES = [
  { project: "Solvatten Solar 80MW", milestone: "Financial Close", target_date: "Q3 2025", status: "on_track", amount: 43_000_000, open_actions: 3 },
  { project: "Väst Wind 120MW", milestone: "Debt Signing", target_date: "Q4 2025", status: "at_risk", amount: 95_000_000, open_actions: 7 },
  { project: "BioCircle W2E", milestone: "Equity Close", target_date: "Q2 2025", status: "on_track", amount: 26_000_000, open_actions: 2 },
  { project: "Coastal Biogas", milestone: "Grant Application", target_date: "May 2025", status: "delayed", amount: 8_000_000, open_actions: 5 },
  { project: "Nordic Hydro Rehab", milestone: "Financial Close", target_date: "Q1 2026", status: "on_track", amount: 18_000_000, open_actions: 4 },
];

const FUNDING_BY_QUARTER = [
  { quarter: "Q2 2025", equity: 22, debt: 0, grant: 5 },
  { quarter: "Q3 2025", equity: 18, debt: 55, grant: 3 },
  { quarter: "Q4 2025", equity: 25, debt: 40, grant: 8 },
  { quarter: "Q1 2026", equity: 12, debt: 0, grant: 4 },
  { quarter: "Q2 2026", equity: 8, debt: 0, grant: 2 },
];

const DD_MATERIALS = [
  { item: "Investment Memorandum", total: 5, ready: 2, critical: true },
  { item: "Financial Model (Base Case + Scenarios)", total: 5, ready: 4, critical: true },
  { item: "Environmental & Social Impact Report", total: 5, ready: 3, critical: true },
  { item: "Technical Due Diligence Package", total: 5, ready: 2, critical: true },
  { item: "Permitting & Regulatory Documentation", total: 5, ready: 4, critical: false },
  { item: "Off-take / Revenue Contracts", total: 5, ready: 2, critical: true },
  { item: "Legal Structure & SPV Summary", total: 5, ready: 5, critical: false },
  { item: "Insurance & Risk Register", total: 5, ready: 3, critical: false },
];

const ALERTS = [
  { type: "warning", title: "Term sheet expiry — Meridian Impact Fund", detail: "Term sheet expires in 14 days. Legal review of key terms required before countersigning.", date: "Due May 2, 2025" },
  { type: "info", title: "Site visit — EIB lender technical advisor", detail: "Lender's TA visiting Väst Wind site. Ensure O&M and grid connection docs are ready.", date: "Apr 28, 2025" },
  { type: "success", title: "Nordic Green Capital — term sheet signed", detail: "$25M equity commitment for Solvatten Solar progressing to legal close.", date: "Apr 15, 2025" },
  { type: "warning", title: "Financial model update needed", detail: "Coastal Biogas model needs Q1 actuals before grant application deadline.", date: "Due May 10, 2025" },
];

const PIPELINE_STAGES = [
  { key: "screening", label: "Screening", color: "bg-neutral-300" },
  { key: "first_meeting", label: "First Meeting", color: "bg-neutral-400" },
  { key: "due_diligence", label: "Due Diligence", color: "bg-primary-300" },
  { key: "term_sheet", label: "Term Sheet", color: "bg-primary-500" },
  { key: "closing", label: "Closing", color: "bg-primary-700" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number, currency = "$") {
  if (n >= 1_000_000_000) return `${currency}${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${currency}${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000) return `${currency}${(n / 1_000).toFixed(0)}K`;
  return `${currency}${n.toFixed(0)}`;
}

function ProgressBar({ value, max, colorClass = "bg-blue-500" }: { value: number; max: number; colorClass?: string }) {
  const w = Math.min(100, max > 0 ? (value / max) * 100 : 0);
  return (
    <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
      <div className={cn("h-2 rounded-full transition-all", colorClass)} style={{ width: `${w}%` }} />
    </div>
  );
}

function StageBadge({ stage }: { stage: string }) {
  const config: Record<string, { label: string; variant: "neutral" | "info" | "warning" | "success" | "error" }> = {
    screening: { label: "Screening", variant: "neutral" },
    first_meeting: { label: "First Meeting", variant: "info" },
    due_diligence: { label: "Due Diligence", variant: "warning" },
    term_sheet: { label: "Term Sheet", variant: "success" },
    closing: { label: "Closing", variant: "success" },
  };
  const c = config[stage] ?? { label: stage, variant: "neutral" as const };
  return <Badge variant={c.variant} className="text-xs">{c.label}</Badge>;
}

function MilestoneStatusBadge({ status }: { status: string }) {
  if (status === "on_track") return <Badge variant="success" className="text-xs">On Track</Badge>;
  if (status === "at_risk") return <Badge variant="warning" className="text-xs">At Risk</Badge>;
  return <Badge variant="error" className="text-xs">Delayed</Badge>;
}

// ── Hero card ─────────────────────────────────────────────────────────────────

function FundraisingHeroCard() {
  const securedPct = (PORTFOLIO_SUMMARY.secured / PORTFOLIO_SUMMARY.total_needed) * 100;
  const discussionPct = (PORTFOLIO_SUMMARY.in_discussion / PORTFOLIO_SUMMARY.total_needed) * 100;

  return (
    <div className="rounded-xl border border-[#E2E5EA] bg-white p-4">
      <div className="flex items-center gap-2 mb-3">
        <Target className="h-4 w-4 text-neutral-400" />
        <span className="text-xs font-semibold text-[#8A8F9A] uppercase tracking-widest">
          Fundraising Overview
        </span>
        <span className="ml-auto text-xs text-neutral-500">
          {PORTFOLIO_SUMMARY.projects_raising} projects · Next close: {PORTFOLIO_SUMMARY.next_close}
        </span>
      </div>

      {/* KPI stat boxes */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        {[
          { label: "Total Needed", value: fmt(PORTFOLIO_SUMMARY.total_needed), sub: "Across portfolio" },
          { label: "Funding Gap", value: fmt(PORTFOLIO_SUMMARY.gap), sub: "To be raised" },
          { label: "Active Investors", value: PORTFOLIO_SUMMARY.active_investors, sub: "In conversation" },
          { label: "Term Sheets", value: PORTFOLIO_SUMMARY.term_sheets, sub: "Live / under review" },
        ].map(({ label, value, sub }) => (
          <div key={label} className="rounded-lg border border-[#E2E5EA] bg-neutral-50 px-3 py-2.5">
            <p className="text-[11px] text-[#8A8F9A] mb-1">{label}</p>
            <p className="text-2xl font-bold text-[#1A1D23]">{value}</p>
            <p className="text-[10px] text-[#8A8F9A] mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {/* Progress bars */}
      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-[#6B7280]">Secured / closed</span>
            <span className="font-semibold text-[#1A1D23]">{fmt(PORTFOLIO_SUMMARY.secured)} / {fmt(PORTFOLIO_SUMMARY.total_needed)} ({securedPct.toFixed(0)}%)</span>
          </div>
          <div className="h-2 rounded-full bg-neutral-200 overflow-hidden">
            <div className="h-2 rounded-full bg-[#4B9E7A] transition-all" style={{ width: `${securedPct}%` }} />
          </div>
        </div>
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-[#6B7280]">In active discussions</span>
            <span className="font-semibold text-[#1A1D23]">{fmt(PORTFOLIO_SUMMARY.in_discussion)} ({discussionPct.toFixed(0)}%)</span>
          </div>
          <div className="h-2 rounded-full bg-neutral-200 overflow-hidden">
            <div className="h-2 rounded-full bg-[#8BAED4] transition-all" style={{ width: `${discussionPct}%` }} />
          </div>
        </div>
      </div>

      {/* Pipeline stage counts */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 pt-4 border-t border-[#E2E5EA]">
        {PIPELINE_STAGES.map((s) => {
          const count = INVESTOR_PIPELINE.filter((i) => i.stage === s.key).length;
          return (
            <div key={s.key} className="text-center">
              <p className="text-[11px] text-[#8A8F9A]">{s.label}</p>
              <p className="text-sm font-semibold text-[#1A1D23] mt-0.5">{count} investor{count !== 1 ? "s" : ""}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ projects }: { projects: ProjectResponse[] }) {
  return (
    <div className="space-y-6">
      <FundraisingHeroCard />

      {/* Alerts */}
      <div className="space-y-2">
        {ALERTS.map((a, i) => (
          <div
            key={i}
            className={cn(
              "flex items-start gap-3 rounded-lg border px-4 py-3 text-sm",
              a.type === "warning" && "border-amber-200 bg-amber-50 text-amber-800",
              a.type === "info" && "border-blue-200 bg-blue-50 text-blue-800",
              a.type === "success" && "border-green-200 bg-green-50 text-green-800",
            )}
          >
            {a.type === "warning" && <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-500" />}
            {a.type === "info" && <Clock className="h-4 w-4 shrink-0 mt-0.5 text-blue-500" />}
            {a.type === "success" && <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-green-500" />}
            <div className="flex-1 min-w-0">
              <span className="font-semibold">{a.title}</span>
              <span className="opacity-80"> — {a.detail}</span>
            </div>
            <span className="text-xs opacity-60 shrink-0">{a.date}</span>
          </div>
        ))}
      </div>

      {/* Project funding status + capital stack */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-500" /> Funding Status by Project
            </CardTitle>
          </CardHeader>
          <CardContent>
            {projects.length === 0 ? (
              <EmptyState title="No projects" description="Create a project to track fundraising progress." />
            ) : (
              <div className="space-y-4">
                {projects.slice(0, 6).map((p) => {
                  const stagePct =
                    p.stage === "operational" ? 100
                    : p.stage === "construction" ? 85
                    : p.stage === "commissioning" ? 70
                    : p.stage === "permitting" ? 45
                    : p.stage === "feasibility" ? 30
                    : p.stage === "pre_feasibility" ? 15
                    : 10;
                  return (
                    <div key={p.id}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-neutral-800 truncate mr-2">{p.name}</span>
                        <span className="text-xs font-semibold text-neutral-700 shrink-0">
                          {formatCurrency(parseFloat(p.total_investment_required))}
                        </span>
                      </div>
                      <ProgressBar value={stagePct} max={100} colorClass="bg-primary-500" />
                      <div className="flex justify-between text-[10px] text-neutral-400 mt-0.5">
                        <span className="capitalize">{p.stage.replace(/_/g, " ")}</span>
                        <span>{stagePct}% funding progress</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Landmark className="h-4 w-4 text-blue-500" /> Capital Stack — Portfolio Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {CAPITAL_STACK.map((t) => (
                <div key={t.tranche}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="font-medium text-neutral-700">{t.tranche}</span>
                    <span className="text-neutral-500 text-xs">{fmt(t.secured + t.in_discussion)} / {fmt(t.target)}</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-neutral-100 overflow-hidden flex">
                    <div
                      className="h-2.5 rounded-l-full transition-all"
                      style={{ width: `${(t.secured / t.target) * 100}%`, backgroundColor: t.color }}
                    />
                    <div
                      className="h-2.5 transition-all opacity-30"
                      style={{ width: `${(t.in_discussion / t.target) * 100}%`, backgroundColor: t.color }}
                    />
                  </div>
                  <div className="flex gap-3 text-[10px] text-neutral-400 mt-0.5">
                    <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: t.color }} />Secured {fmt(t.secured)}</span>
                    <span className="flex items-center gap-1"><span className="inline-block w-2 h-2 rounded-full opacity-30" style={{ backgroundColor: t.color }} />In discussion {fmt(t.in_discussion)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Investor Pipeline tab ─────────────────────────────────────────────────────

function PipelineTab() {
  return (
    <div className="space-y-6">
      {/* Funnel summary */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {PIPELINE_STAGES.map((s) => {
          const investors = INVESTOR_PIPELINE.filter((i) => i.stage === s.key);
          const totalTicket = investors.reduce((sum, i) => sum + i.ticket, 0);
          return (
            <Card key={s.key}>
              <CardContent className="pt-4 pb-4">
                <div className={cn("w-2 h-2 rounded-full mb-2", s.color)} />
                <p className="text-xs text-neutral-500 font-medium">{s.label}</p>
                <p className="text-2xl font-bold text-neutral-900 mt-0.5">{investors.length}</p>
                <p className="text-xs text-neutral-400">{fmt(totalTicket)}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Investor pipeline table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-6">
            <CardTitle className="text-sm">Investor Tracker</CardTitle>
            <Button size="sm" variant="outline" className="flex-shrink-0">
              <Download className="h-3.5 w-3.5 mr-1.5" /> Export CRM
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-neutral-100 bg-neutral-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Investor</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Type</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Target Ticket</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Stage</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Last Contact</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Next Action</th>
                </tr>
              </thead>
              <tbody>
                {(() => {
                  // Group investors by project, preserving insertion order
                  const projectOrder: string[] = [];
                  const grouped: Record<string, typeof INVESTOR_PIPELINE> = {};
                  for (const inv of INVESTOR_PIPELINE) {
                    if (!grouped[inv.project]) {
                      projectOrder.push(inv.project);
                      grouped[inv.project] = [];
                    }
                    grouped[inv.project].push(inv);
                  }
                  return projectOrder.map((project, pi) => {
                    const investors = grouped[project];
                    const projectTotal = investors.reduce((s, i) => s + i.ticket, 0);
                    return (
                      <React.Fragment key={project}>
                        {/* Project divider row */}
                        <tr className={cn(pi > 0 && "border-t-2 border-neutral-200")}>
                          <td
                            colSpan={6}
                            className="px-4 py-2 bg-neutral-50"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-neutral-700 uppercase tracking-wide">
                                {project}
                              </span>
                              <span className="text-xs text-neutral-400">
                                {investors.length} investor{investors.length !== 1 ? "s" : ""} · {fmt(projectTotal)}
                              </span>
                            </div>
                          </td>
                        </tr>
                        {/* Investor rows for this project */}
                        {investors.map((inv) => (
                          <tr key={`${inv.investor}-${inv.project}`} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                            <td className="px-4 py-3 font-medium text-neutral-900">{inv.investor}</td>
                            <td className="px-4 py-3 text-xs text-neutral-500">{inv.type}</td>
                            <td className="px-4 py-3 text-right font-semibold text-neutral-800">{fmt(inv.ticket)}</td>
                            <td className="px-4 py-3"><StageBadge stage={inv.stage} /></td>
                            <td className="px-4 py-3 text-xs text-neutral-400">{inv.last_contact}</td>
                            <td className="px-4 py-3">
                              <span className="flex items-center gap-1 text-xs text-blue-600 font-medium">
                                <ChevronRight className="h-3 w-3" />{inv.next_action}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  });
                })()}
              </tbody>
              <tfoot className="bg-neutral-50 border-t-2 border-neutral-200">
                <tr>
                  <td className="px-4 py-3 font-semibold text-neutral-900" colSpan={2}>Total pipeline</td>
                  <td className="px-4 py-3 text-right font-semibold text-neutral-900">
                    {fmt(INVESTOR_PIPELINE.reduce((s, i) => s + i.ticket, 0))}
                  </td>
                  <td colSpan={3} />
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Capital Structure tab ─────────────────────────────────────────────────────

function CapitalStructureTab({ projects }: { projects: ProjectResponse[] }) {
  return (
    <div className="space-y-6">
      {/* Stack bar chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Capital Stack by Tranche ($M)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={CAPITAL_STACK} layout="vertical" margin={{ left: 0, right: 30, top: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(0)}M`} />
              <YAxis type="category" dataKey="tranche" tick={{ fontSize: 11 }} width={120} />
              <Tooltip formatter={(value) => [`$${(Number(value) / 1_000_000).toFixed(0)}M`]} />
              <Bar dataKey="secured" name="Secured" stackId="a" radius={[0, 0, 0, 0]}>
                {CAPITAL_STACK.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
              <Bar dataKey="in_discussion" name="In Discussion" stackId="a" radius={[0, 4, 4, 0]}>
                {CAPITAL_STACK.map((entry, i) => (
                  <Cell key={i} fill={entry.color} fillOpacity={0.3} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 justify-center text-xs text-neutral-500 mt-2">
            <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded bg-blue-500" />Secured</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded bg-blue-200" />In Discussion</span>
          </div>
        </CardContent>
      </Card>

      {/* Detailed stack table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Tranche Detail</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Tranche</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Target</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Secured</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">In Discussion</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Gap</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Progress</th>
              </tr>
            </thead>
            <tbody>
              {CAPITAL_STACK.map((t) => {
                const gap = t.target - t.secured - t.in_discussion;
                const filledPct = ((t.secured + t.in_discussion) / t.target) * 100;
                return (
                  <tr key={t.tranche} className="border-b border-neutral-50 hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: t.color }} />
                        <span className="font-medium text-neutral-900">{t.tranche}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-700">{fmt(t.target)}</td>
                    <td className="px-4 py-3 text-right text-emerald-700 font-semibold">{fmt(t.secured)}</td>
                    <td className="px-4 py-3 text-right text-blue-600">{fmt(t.in_discussion)}</td>
                    <td className="px-4 py-3 text-right text-neutral-400">{gap > 0 ? fmt(gap) : "—"}</td>
                    <td className="px-4 py-3 w-32">
                      <div className="h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                        <div className="h-1.5 rounded-full transition-all" style={{ width: `${filledPct}%`, backgroundColor: t.color }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-neutral-50 border-t border-neutral-200">
              <tr>
                <td className="px-4 py-3 font-semibold text-neutral-900">Total</td>
                <td className="px-4 py-3 text-right font-semibold">{fmt(CAPITAL_STACK.reduce((s, t) => s + t.target, 0))}</td>
                <td className="px-4 py-3 text-right font-semibold text-emerald-700">{fmt(CAPITAL_STACK.reduce((s, t) => s + t.secured, 0))}</td>
                <td className="px-4 py-3 text-right font-semibold text-blue-600">{fmt(CAPITAL_STACK.reduce((s, t) => s + t.in_discussion, 0))}</td>
                <td className="px-4 py-3 text-right font-semibold text-neutral-400">{fmt(CAPITAL_STACK.reduce((s, t) => s + Math.max(0, t.target - t.secured - t.in_discussion), 0))}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </CardContent>
      </Card>

      {/* Per-project funding need */}
      {projects.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Funding Required by Project</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead className="border-b border-neutral-100 bg-neutral-50">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-500">Project</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-neutral-500">Required</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-500">Stage</th>
                </tr>
              </thead>
              <tbody>
                {projects.slice(0, 8).map((p) => (
                  <tr key={p.id} className="border-b border-neutral-50 last:border-0 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-neutral-800">{p.name}</td>
                    <td className="px-4 py-3 text-right font-semibold text-neutral-700 tabular-nums">
                      {formatCurrency(parseFloat(p.total_investment_required))}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="neutral" className="text-[10px] capitalize">{p.stage.replace(/_/g, " ")}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Milestones & Schedule tab ─────────────────────────────────────────────────

function MilestonesTab() {
  return (
    <div className="space-y-6">
      {/* Milestone table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Funding Milestones</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Milestone</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Target Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Amount</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-neutral-500">Open Actions</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {FUNDING_MILESTONES.map((m) => (
                <tr key={`${m.project}-${m.milestone}`} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-neutral-900">{m.project}</td>
                  <td className="px-4 py-3 text-neutral-600">{m.milestone}</td>
                  <td className="px-4 py-3 text-neutral-500">{m.target_date}</td>
                  <td className="px-4 py-3 text-right font-semibold text-neutral-800">{fmt(m.amount)}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn(
                      "inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold",
                      m.open_actions <= 2 ? "bg-green-100 text-green-700" : m.open_actions <= 5 ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"
                    )}>
                      {m.open_actions}
                    </span>
                  </td>
                  <td className="px-4 py-3"><MilestoneStatusBadge status={m.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Funding need by quarter */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Capital Required by Quarter ($M)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={FUNDING_BY_QUARTER} margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
              <XAxis dataKey="quarter" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${v}M`} />
              <Tooltip formatter={(value) => [`$${value}M`]} />
              <Bar dataKey="equity" name="Equity" stackId="a" fill="#4F46E5" radius={[0, 0, 0, 0]} />
              <Bar dataKey="debt" name="Debt" stackId="a" fill="#3B82F6" radius={[0, 0, 0, 0]} />
              <Bar dataKey="grant" name="Grant / Subsidy" stackId="a" fill="#10B981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 justify-center text-xs text-neutral-500 mt-2">
            <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded bg-blue-600" />Equity</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded bg-blue-500" />Debt</span>
            <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded bg-emerald-500" />Grant</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Due Diligence tab ─────────────────────────────────────────────────────────

function DueDiligenceTab() {
  const readyCount = DD_MATERIALS.filter((m) => m.ready === m.total).length;

  return (
    <div className="space-y-6">
      {/* Readiness summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Materials Ready", value: `${readyCount} / ${DD_MATERIALS.length}`, color: "text-neutral-900", sub: "Fully complete" },
          { label: "Critical Gaps", value: DD_MATERIALS.filter((m) => m.critical && m.ready < m.total).length, color: "text-neutral-900", sub: "Blocking items" },
          { label: "Projects Investor-Ready", value: "2 / 5", color: "text-neutral-900", sub: "Full DD package" },
          { label: "Avg. Completeness", value: `${Math.round(DD_MATERIALS.reduce((s, m) => s + (m.ready / m.total) * 100, 0) / DD_MATERIALS.length)}%`, color: "text-neutral-900", sub: "Across all materials" },
        ].map(({ label, value, color, sub }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <p className="text-xs text-neutral-500 font-medium">{label}</p>
              <p className={cn("text-3xl font-bold mt-1", color)}>{value}</p>
              <p className="text-xs text-neutral-400 mt-1">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Materials checklist */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-6">
            <CardTitle className="text-sm">Due Diligence Materials</CardTitle>
            <Button size="sm" variant="outline" className="flex-shrink-0">
              <Download className="h-3.5 w-3.5 mr-1.5" /> DD Checklist
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Material</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-neutral-500">Priority</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Projects Ready</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Completeness</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {DD_MATERIALS.map((m) => {
                const pct = Math.round((m.ready / m.total) * 100);
                return (
                  <tr key={m.item} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="h-3.5 w-3.5 text-neutral-300 shrink-0" />
                        <span className="font-medium text-neutral-900">{m.item}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {m.critical ? (
                        <Badge variant="error" className="text-xs">Critical</Badge>
                      ) : (
                        <Badge variant="neutral" className="text-xs">Standard</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-600">{m.ready} / {m.total}</td>
                    <td className="px-4 py-3 w-36">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                          <div
                            className={cn("h-1.5 rounded-full transition-all", pct === 100 ? "bg-emerald-500" : pct >= 60 ? "bg-blue-500" : "bg-amber-500")}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="text-xs text-neutral-400 w-8 text-right">{pct}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {pct === 100 ? (
                        <Badge variant="success" className="text-xs">Complete</Badge>
                      ) : m.critical && pct < 40 ? (
                        <Badge variant="error" className="text-xs">Action Needed</Badge>
                      ) : (
                        <Badge variant="warning" className="text-xs">In Progress</Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Next steps */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-blue-500" /> Recommended Next Steps
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { priority: "High", action: "Complete Investment Memorandum for Väst Wind 120MW", project: "Väst Wind 120MW", due: "Apr 25" },
              { priority: "High", action: "Update financial model with Q1 actuals — Coastal Biogas grant deadline", project: "Coastal Biogas", due: "May 10" },
              { priority: "High", action: "Prepare technical DD package ahead of EIB site visit", project: "Väst Wind 120MW", due: "Apr 27" },
              { priority: "Medium", action: "Draft off-take contract summary for Solvatten Solar investor pack", project: "Solvatten Solar 80MW", due: "May 15" },
              { priority: "Medium", action: "Respond to ESG questionnaire — Triodos Investment Mgmt screening", project: "Coastal Biogas", due: "May 5" },
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-3 py-2 border-b border-neutral-50 last:border-0">
                <Badge variant={step.priority === "High" ? "error" : "warning"} className="text-xs shrink-0 mt-0.5">{step.priority}</Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-800">{step.action}</p>
                  <p className="text-xs text-neutral-400 mt-0.5">{step.project}</p>
                </div>
                <span className="text-xs text-neutral-400 shrink-0">{step.due}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FundingPage() {
  const { data: projectList, isLoading: loadingProjects } = useProjects({ page_size: 50 });
  const { data: stats } = useProjectStats();
  const projects = projectList?.items ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Wallet className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Funding &amp; Capital Raise</h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Track investors, capital structure, funding milestones and due diligence readiness
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {stats && (
            <span className="text-xs text-neutral-400 border border-neutral-200 rounded-full px-3 py-1">
              {stats.total_projects} projects · {formatCurrency(parseFloat(stats.total_funding_needed))} to raise
            </span>
          )}
          <Link href="/matching">
            <Button size="sm">
              <Users className="h-4 w-4 mr-2" />
              Find Investors
            </Button>
          </Link>
        </div>
      </div>

      <InfoBanner>
        <strong>Funding &amp; Capital Raise</strong> helps you manage your fundraising process end-to-end — from
        tracking investor conversations in the <strong>Pipeline</strong> to structuring your{" "}
        <strong>Capital Stack</strong>, monitoring <strong>Milestones</strong> to financial close, and ensuring
        your <strong>Due Diligence</strong> materials are investor-ready.
      </InfoBanner>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="pipeline">Investor Pipeline</TabsTrigger>
          <TabsTrigger value="capital">Capital Structure</TabsTrigger>
          <TabsTrigger value="milestones">Milestones</TabsTrigger>
          <TabsTrigger value="dd">Due Diligence</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          {loadingProjects ? (
            <div className="flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
            </div>
          ) : (
            <OverviewTab projects={projects} />
          )}
        </TabsContent>

        <TabsContent value="pipeline" className="mt-6">
          <PipelineTab />
        </TabsContent>

        <TabsContent value="capital" className="mt-6">
          {loadingProjects ? (
            <div className="flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
            </div>
          ) : (
            <CapitalStructureTab projects={projects} />
          )}
        </TabsContent>

        <TabsContent value="milestones" className="mt-6">
          <MilestonesTab />
        </TabsContent>

        <TabsContent value="dd" className="mt-6">
          <DueDiligenceTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
