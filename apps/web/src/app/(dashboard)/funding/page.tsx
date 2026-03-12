"use client";

import {
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  Clock,
  Download,
  Landmark,
  Percent,
  Users,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import {
  Area,
  AreaChart,
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  cn,
} from "@scr/ui";
import { useProjects, useProjectStats, formatCurrency, type ProjectResponse } from "@/lib/projects";
import { InfoBanner } from "@/components/info-banner";

// ── Mock fund data ────────────────────────────────────────────────────────────

const FUND = {
  name: "SCR Sustainable Infrastructure Fund I",
  vintage: 2022,
  target_size: 500_000_000,
  committed: 347_000_000,
  called: 215_000_000,
  distributed: 28_400_000,
  nav: 308_000_000,
  dpi: 0.13,
  rvpi: 0.89,
  tvpi: 1.02,
  gross_irr: 12.4,
  net_irr: 9.8,
  preferred_return: 8.0,
  management_fee_pct: 1.5,
  carried_interest_pct: 20,
  gp_commitment_pct: 2.0,
  investment_period_end: "2026-12-31",
  fund_term_years: 12,
};

const LP_TABLE = [
  { name: "Meridian Capital Partners", committed: 65_000_000, called_pct: 62, type: "Pension Fund", region: "North America" },
  { name: "Impact Horizons Ltd", committed: 64_000_000, called_pct: 58, type: "Family Office", region: "Europe" },
  { name: "Nordic Sustainable Ventures", committed: 55_000_000, called_pct: 65, type: "Sovereign Wealth", region: "Europe" },
  { name: "GreenBridge Institutional", committed: 48_000_000, called_pct: 60, type: "Insurance", region: "Europe" },
  { name: "Atlantic Infra Fund", committed: 42_000_000, called_pct: 55, type: "Endowment", region: "North America" },
  { name: "Pioneer Climate Finance", committed: 38_000_000, called_pct: 70, type: "DFI", region: "Global" },
  { name: "EuroCapital ESG", committed: 35_000_000, called_pct: 63, type: "Asset Manager", region: "Europe" },
];

const CAPITAL_CALLS = [
  { number: 1, date: "Feb 2023", amount: 43_000_000, status: "settled", purpose: "Initial portfolio deployment" },
  { number: 2, date: "Aug 2023", amount: 58_000_000, status: "settled", purpose: "Solar & wind acquisitions" },
  { number: 3, date: "Mar 2024", amount: 67_000_000, status: "settled", purpose: "Construction financing" },
  { number: 4, date: "Oct 2024", amount: 47_000_000, status: "settled", purpose: "Follow-on investments" },
  { number: 5, date: "Q2 2025", amount: 52_000_000, status: "planned", purpose: "Greenfield pipeline" },
  { number: 6, date: "Q4 2025", amount: 30_000_000, status: "planned", purpose: "Reserve & fees" },
];

const DEPLOYMENT_BY_SECTOR = [
  { sector: "Solar PV", deployed: 82, committed: 95, color: "#F59E0B" },
  { sector: "Onshore Wind", deployed: 45, committed: 60, color: "#3B82F6" },
  { sector: "Battery Storage", deployed: 33, committed: 40, color: "#8B5CF6" },
  { sector: "Hydro", deployed: 28, committed: 28, color: "#06B6D4" },
  { sector: "Other Renewables", deployed: 27, committed: 35, color: "#10B981" },
];

const DISTRIBUTIONS = [
  { quarter: "Q4 2023", amount: 3_200_000, type: "Income" },
  { quarter: "Q1 2024", amount: 4_100_000, type: "Income" },
  { quarter: "Q2 2024", amount: 5_800_000, type: "Income" },
  { quarter: "Q3 2024", amount: 6_200_000, type: "Income" },
  { quarter: "Q4 2024", amount: 9_100_000, type: "Return of Capital" },
];

const J_CURVE_DATA = [
  { quarter: "Q1 22", cumulative: 0, contributions: 0, distributions: 0 },
  { quarter: "Q2 22", cumulative: -2, contributions: -2, distributions: 0 },
  { quarter: "Q3 22", cumulative: -5, contributions: -3, distributions: 0 },
  { quarter: "Q4 22", cumulative: -8, contributions: -3, distributions: 0 },
  { quarter: "Q1 23", cumulative: -10, contributions: -2, distributions: 0 },
  { quarter: "Q2 23", cumulative: -50, contributions: -43, distributions: 3 },
  { quarter: "Q3 23", cumulative: -52, contributions: -6, distributions: 4 },
  { quarter: "Q4 23", cumulative: -107, contributions: -58, distributions: 3.2 },
  { quarter: "Q1 24", cumulative: -108, contributions: -5, distributions: 4.1 },
  { quarter: "Q2 24", cumulative: -170, contributions: -67, distributions: 5.8 },
  { quarter: "Q3 24", cumulative: -171, contributions: -7, distributions: 6.2 },
  { quarter: "Q4 24", cumulative: -212, contributions: -47, distributions: 9.1 },
  { quarter: "Q1 25", cumulative: -213, contributions: -6, distributions: 5 },
];

const ALERTS = [
  { type: "warning", title: "Capital Call #5 approaching", detail: "€52M call scheduled for Q2 2025 — LP notices required 30 days prior.", date: "Due Apr 15, 2025" },
  { type: "info", title: "Investment period ends in 21 months", detail: "New investments must be committed before Dec 2026.", date: "Dec 31, 2026" },
  { type: "success", title: "DPI target on track", detail: "Current DPI of 0.13x aligned with vintage 2022 peer median.", date: "As of Q1 2025" },
  { type: "warning", title: "Management fee step-down approaching", detail: "Fee base transitions from committed to invested capital at end of investment period.", date: "Dec 31, 2026" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number, currency = "€") {
  if (n >= 1_000_000_000) return `${currency}${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${currency}${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000) return `${currency}${(n / 1_000).toFixed(0)}K`;
  return `${currency}${n.toFixed(0)}`;
}

function pct(n: number) {
  return `${n.toFixed(1)}%`;
}

function ProgressBar({ value, max, colorClass = "bg-indigo-500" }: { value: number; max: number; colorClass?: string }) {
  const w = Math.min(100, (value / max) * 100);
  return (
    <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
      <div className={cn("h-2 rounded-full transition-all", colorClass)} style={{ width: `${w}%` }} />
    </div>
  );
}

// ── Hero card ─────────────────────────────────────────────────────────────────

function FundHeroCard() {
  const calledPct = (FUND.called / FUND.committed) * 100;
  const committedPct = (FUND.committed / FUND.target_size) * 100;

  return (
    <div className="rounded-2xl bg-[#1B2A4A] text-white p-6">
      <div className="flex flex-col lg:flex-row lg:items-start gap-6">
        {/* Fund info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Landmark className="h-5 w-5 text-indigo-300" />
            <span className="text-xs font-medium text-indigo-300 uppercase tracking-widest">
              Fund Overview
            </span>
          </div>
          <h2 className="text-xl font-bold leading-tight mb-1">{FUND.name}</h2>
          <p className="text-sm text-slate-300">Vintage {FUND.vintage} · {FUND.fund_term_years}-year term · Target {fmt(FUND.target_size)}</p>

          <div className="mt-4 space-y-3">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400">Commitments raised</span>
                <span className="font-semibold">{fmt(FUND.committed)} / {fmt(FUND.target_size)} ({pct(committedPct)})</span>
              </div>
              <div className="h-2 rounded-full bg-white/10">
                <div className="h-2 rounded-full bg-indigo-400 transition-all" style={{ width: `${committedPct}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400">Capital called</span>
                <span className="font-semibold">{fmt(FUND.called)} ({pct(calledPct)} of committed)</span>
              </div>
              <div className="h-2 rounded-full bg-white/10">
                <div className="h-2 rounded-full bg-emerald-400 transition-all" style={{ width: `${calledPct}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Returns metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4 gap-3 lg:shrink-0">
          {[
            { label: "DPI", value: `${FUND.dpi.toFixed(2)}x`, sub: "Distributions/Paid-in" },
            { label: "RVPI", value: `${FUND.rvpi.toFixed(2)}x`, sub: "Residual/Paid-in" },
            { label: "TVPI", value: `${FUND.tvpi.toFixed(2)}x`, sub: "Total Value/Paid-in" },
            { label: "Gross IRR", value: `${FUND.gross_irr}%`, sub: `Net: ${FUND.net_irr}%` },
          ].map(({ label, value, sub }) => (
            <div key={label} className="rounded-xl bg-white/10 px-3 py-3 text-center">
              <p className="text-xs text-slate-400 mb-0.5">{label}</p>
              <p className="text-xl font-bold">{value}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom stats */}
      <div className="mt-5 grid grid-cols-3 sm:grid-cols-6 gap-3 pt-4 border-t border-white/10">
        {[
          { label: "LPs", value: LP_TABLE.length },
          { label: "Capital Calls", value: `${CAPITAL_CALLS.filter(c => c.status === "settled").length} done` },
          { label: "Distributed", value: fmt(FUND.distributed) },
          { label: "NAV", value: fmt(FUND.nav) },
          { label: "Pref. Return", value: pct(FUND.preferred_return) },
          { label: "Carry", value: pct(FUND.carried_interest_pct) },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <p className="text-xs text-slate-400">{label}</p>
            <p className="text-sm font-semibold mt-0.5">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab() {
  return (
    <div className="space-y-6">
      <FundHeroCard />

      {/* Alerts strip */}
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
              <span className="text-opacity-80"> — {a.detail}</span>
            </div>
            <span className="text-xs opacity-60 shrink-0">{a.date}</span>
          </div>
        ))}
      </div>

      {/* LP summary + deployment */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Users className="h-4 w-4 text-indigo-500" /> LP Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {LP_TABLE.map((lp) => (
                <div key={lp.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-neutral-800 truncate mr-2">{lp.name}</span>
                    <span className="text-neutral-500 shrink-0">{fmt(lp.committed)}</span>
                  </div>
                  <ProgressBar value={lp.called_pct} max={100} colorClass="bg-indigo-500" />
                  <div className="flex justify-between text-[10px] text-neutral-400 mt-0.5">
                    <span>{lp.type} · {lp.region}</span>
                    <span>{lp.called_pct}% called</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-500" /> Capital Deployment by Sector (€M)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={DEPLOYMENT_BY_SECTOR} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `€${v}M`} />
                <YAxis type="category" dataKey="sector" tick={{ fontSize: 11 }} width={90} />
                <Tooltip formatter={(v) => [`€${v}M`]} />
                <Bar dataKey="deployed" name="Deployed" radius={[0, 4, 4, 0]}>
                  {DEPLOYMENT_BY_SECTOR.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Fundraising tab ───────────────────────────────────────────────────────────

function FundraisingTab({ projects }: { projects: ProjectResponse[] }) {
  return (
    <div className="space-y-6">
      {/* LP Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Limited Partners</CardTitle>
            <Button size="sm" variant="outline">
              <Download className="h-3.5 w-3.5 mr-1.5" /> Export
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-neutral-100 bg-neutral-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">LP Name</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Committed</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Called</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Called %</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Region</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {LP_TABLE.map((lp) => (
                  <tr key={lp.name} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-neutral-900">{lp.name}</td>
                    <td className="px-4 py-3 text-right text-neutral-700">{fmt(lp.committed)}</td>
                    <td className="px-4 py-3 text-right text-neutral-700">{fmt(lp.committed * lp.called_pct / 100)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                          <div className="h-1.5 rounded-full bg-indigo-500" style={{ width: `${lp.called_pct}%` }} />
                        </div>
                        <span className="text-xs text-neutral-500 w-8 text-right">{lp.called_pct}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-neutral-500 text-xs">{lp.type}</td>
                    <td className="px-4 py-3 text-neutral-500 text-xs">{lp.region}</td>
                    <td className="px-4 py-3">
                      <Badge variant="success" className="text-xs">Active</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-neutral-50 border-t border-neutral-200">
                <tr>
                  <td className="px-4 py-3 font-semibold text-neutral-900">Total</td>
                  <td className="px-4 py-3 text-right font-semibold text-neutral-900">{fmt(FUND.committed)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-neutral-900">{fmt(FUND.called)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-neutral-900">{pct((FUND.called / FUND.committed) * 100)}</td>
                  <td colSpan={3} />
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Funding by project */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Funding by Project</CardTitle>
        </CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <EmptyState title="No projects" description="Create a project to track fundraising." />
          ) : (
            <div className="space-y-3">
              {projects.slice(0, 8).map((p) => (
                <div key={p.id} className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-neutral-800 truncate">{p.name}</span>
                      <span className="text-sm font-semibold text-neutral-700 ml-2 shrink-0">
                        {formatCurrency(parseFloat(p.total_investment_required))}
                      </span>
                    </div>
                    <ProgressBar
                      value={p.stage === "operational" ? 100 : p.stage === "construction" ? 75 : p.stage === "ready_to_build" ? 50 : p.stage === "development" ? 25 : 10}
                      max={100}
                      colorClass="bg-emerald-500"
                    />
                  </div>
                  <Badge variant="neutral" className="text-[10px] shrink-0 capitalize">{p.stage.replace(/_/g, " ")}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Deployment tab ────────────────────────────────────────────────────────────

function DeploymentTab() {
  return (
    <div className="space-y-6">
      {/* Capital calls */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Capital Call Schedule</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Call #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Amount</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Purpose</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {CAPITAL_CALLS.map((call) => (
                <tr key={call.number} className="border-b border-neutral-50 hover:bg-neutral-50">
                  <td className="px-4 py-3 font-mono text-xs text-neutral-400">#{call.number}</td>
                  <td className="px-4 py-3 text-neutral-700">{call.date}</td>
                  <td className="px-4 py-3 text-right font-semibold text-neutral-900">{fmt(call.amount)}</td>
                  <td className="px-4 py-3 text-neutral-500 text-xs">{call.purpose}</td>
                  <td className="px-4 py-3">
                    {call.status === "settled" ? (
                      <Badge variant="success">Settled</Badge>
                    ) : (
                      <Badge variant="warning">Planned</Badge>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Deployment by sector chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Deployed vs Committed by Sector (€M)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={DEPLOYMENT_BY_SECTOR} margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="sector" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}M`} />
                <Tooltip formatter={(v) => [`€${v}M`]} />
                <Bar dataKey="committed" name="Committed" fill="#E0E7FF" radius={[4, 4, 0, 0]} />
                <Bar dataKey="deployed" name="Deployed" fill="#4F46E5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Deployment Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {DEPLOYMENT_BY_SECTOR.map((s) => (
                <div key={s.sector}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="font-medium text-neutral-700">{s.sector}</span>
                    <span className="text-neutral-500">€{s.deployed}M / €{s.committed}M</span>
                  </div>
                  <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-all"
                      style={{ width: `${(s.deployed / s.committed) * 100}%`, backgroundColor: s.color }}
                    />
                  </div>
                </div>
              ))}
              <div className="pt-2 border-t border-neutral-100 flex justify-between text-sm font-semibold">
                <span className="text-neutral-700">Total Deployed</span>
                <span>{fmt(DEPLOYMENT_BY_SECTOR.reduce((a, b) => a + b.deployed, 0) * 1_000_000)} / {fmt(DEPLOYMENT_BY_SECTOR.reduce((a, b) => a + b.committed, 0) * 1_000_000)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Distributions tab ─────────────────────────────────────────────────────────

function DistributionsTab() {
  return (
    <div className="space-y-6">
      {/* DPI/RVPI/TVPI/IRR hero */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "DPI", value: `${FUND.dpi.toFixed(2)}x`, sub: "Distributions/Paid-in", color: "text-emerald-600" },
          { label: "RVPI", value: `${FUND.rvpi.toFixed(2)}x`, sub: "Residual/Paid-in", color: "text-indigo-600" },
          { label: "TVPI", value: `${FUND.tvpi.toFixed(2)}x`, sub: "Total Value/Paid-in", color: "text-violet-600" },
          { label: "Net IRR", value: `${FUND.net_irr}%`, sub: `Gross: ${FUND.gross_irr}%`, color: "text-blue-600" },
        ].map(({ label, value, sub, color }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <p className="text-xs text-neutral-500 font-medium">{label}</p>
              <p className={cn("text-3xl font-bold mt-1", color)}>{value}</p>
              <p className="text-xs text-neutral-400 mt-1">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Distribution history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Distribution History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Quarter</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Amount</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Type</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Cumulative</th>
              </tr>
            </thead>
            <tbody>
              {DISTRIBUTIONS.reduce<{ rows: typeof DISTRIBUTIONS; cumulative: number }>(
                (acc, d) => {
                  acc.cumulative += d.amount;
                  acc.rows.push(d);
                  return acc;
                },
                { rows: [], cumulative: 0 }
              ).rows.map((d, i) => {
                const cum = DISTRIBUTIONS.slice(0, i + 1).reduce((s, x) => s + x.amount, 0);
                return (
                  <tr key={d.quarter} className="border-b border-neutral-50 hover:bg-neutral-50">
                    <td className="px-4 py-3 font-medium text-neutral-800">{d.quarter}</td>
                    <td className="px-4 py-3 text-right text-emerald-700 font-semibold">{fmt(d.amount)}</td>
                    <td className="px-4 py-3">
                      <Badge variant={d.type === "Income" ? "success" : "info"} className="text-xs">{d.type}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-500">{fmt(cum)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-neutral-50 border-t border-neutral-200">
              <tr>
                <td className="px-4 py-3 font-semibold">Total Distributed</td>
                <td className="px-4 py-3 text-right font-semibold text-emerald-700">{fmt(FUND.distributed)}</td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Projections tab ───────────────────────────────────────────────────────────

function ProjectionsTab() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">J-Curve — Cumulative Net Cash Flow (€M)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={J_CURVE_DATA} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="positiveGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="negativeGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="quarter" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `€${v}M`} />
              <Tooltip formatter={(v: number) => [`€${v}M`]} />
              <Area
                type="monotone"
                dataKey="cumulative"
                name="Cumulative NCF"
                stroke="#4F46E5"
                strokeWidth={2}
                fill="url(#positiveGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Scenario summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { scenario: "Pessimistic", tvpi: "0.85x", irr: "−2.1%", color: "border-red-200 bg-red-50", text: "text-red-700" },
          { scenario: "Base Case", tvpi: "1.02x", irr: "9.8%", color: "border-indigo-200 bg-indigo-50", text: "text-indigo-700" },
          { scenario: "Optimistic", tvpi: "1.35x", irr: "18.4%", color: "border-emerald-200 bg-emerald-50", text: "text-emerald-700" },
        ].map(({ scenario, tvpi, irr, color, text }) => (
          <div key={scenario} className={cn("rounded-xl border p-4", color)}>
            <p className={cn("text-xs font-semibold uppercase tracking-wide mb-2", text)}>{scenario}</p>
            <div className="flex justify-between">
              <div>
                <p className="text-xs text-neutral-500">TVPI</p>
                <p className={cn("text-xl font-bold", text)}>{tvpi}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-neutral-500">Net IRR</p>
                <p className={cn("text-xl font-bold", text)}>{irr}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Economics tab ─────────────────────────────────────────────────────────────

function EconomicsTab() {
  const mgmtFeeBase = FUND.committed;
  const annualMgmtFee = mgmtFeeBase * (FUND.management_fee_pct / 100);
  const gpCommitment = FUND.committed * (FUND.gp_commitment_pct / 100);

  return (
    <div className="space-y-6">
      {/* Fee structure */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Percent className="h-4 w-4 text-indigo-500" /> Fee Structure
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "Management Fee", value: pct(FUND.management_fee_pct), sub: `${fmt(annualMgmtFee)}/yr on committed capital` },
              { label: "Carried Interest", value: pct(FUND.carried_interest_pct), sub: "Above preferred return hurdle" },
              { label: "Preferred Return (Hurdle)", value: pct(FUND.preferred_return), sub: "LP preferred return before carry" },
              { label: "GP Commitment", value: pct(FUND.gp_commitment_pct), sub: `${fmt(gpCommitment)} committed by GP` },
            ].map(({ label, value, sub }) => (
              <div key={label} className="flex items-center justify-between py-2 border-b border-neutral-50 last:border-0">
                <div>
                  <p className="text-sm font-medium text-neutral-800">{label}</p>
                  <p className="text-xs text-neutral-400">{sub}</p>
                </div>
                <span className="text-lg font-bold text-indigo-700">{value}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Building2 className="h-4 w-4 text-indigo-500" /> Fund Economics Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-neutral-600">Total Committed Capital</span>
                <span className="font-semibold">{fmt(FUND.committed)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-neutral-600">Management Fees (10yr est.)</span>
                <span className="font-semibold text-orange-600">−{fmt(annualMgmtFee * 10)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-neutral-600">Investable Capital (est.)</span>
                <span className="font-semibold text-indigo-700">{fmt(FUND.committed - annualMgmtFee * 10)}</span>
              </div>
              <div className="border-t border-indigo-200 pt-3 flex justify-between text-sm font-bold">
                <span>NAV (Current)</span>
                <span className="text-indigo-700">{fmt(FUND.nav)}</span>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">Fee Step-Down</p>
              <p className="text-sm text-neutral-600">
                Management fee transitions from committed to invested capital basis at end of investment period
                ({FUND.investment_period_end}).
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* LP Reporting */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">LP Reporting Summary</CardTitle>
            <Button size="sm" variant="outline">
              <Download className="h-3.5 w-3.5 mr-1.5" /> ILPA Report
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: "Reporting Frequency", value: "Quarterly" },
              { label: "Audited Accounts", value: "Annual" },
              { label: "Valuation Standard", value: "IPEV" },
              { label: "Next LP Meeting", value: "Q2 2025" },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                <p className="text-xs text-neutral-500">{label}</p>
                <p className="text-sm font-semibold text-neutral-900 mt-0.5">{value}</p>
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
          <div className="p-2 bg-indigo-100 rounded-lg">
            <Wallet className="h-6 w-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Funding &amp; Capital Management</h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Fund structure, LP commitments, capital deployment and returns
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {stats && (
            <span className="text-xs text-neutral-400 border border-neutral-200 rounded-full px-3 py-1">
              {stats.total_projects} projects · {formatCurrency(parseFloat(stats.total_funding_needed))} pipeline
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
        <strong>Funding &amp; Capital Management</strong> provides a unified view of your fund structure,
        LP commitments, capital call schedules, and deployment progress. Use the <strong>Distributions</strong> tab
        to track DPI/RVPI/TVPI returns, <strong>Projections</strong> for J-curve modelling, and{" "}
        <strong>Economics</strong> for fee structure and LP reporting.
      </InfoBanner>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="fundraising">Fundraising</TabsTrigger>
          <TabsTrigger value="deployment">Deployment</TabsTrigger>
          <TabsTrigger value="distributions">Distributions</TabsTrigger>
          <TabsTrigger value="projections">Projections</TabsTrigger>
          <TabsTrigger value="economics">Economics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab />
        </TabsContent>

        <TabsContent value="fundraising" className="mt-6">
          {loadingProjects ? (
            <div className="flex justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent" />
            </div>
          ) : (
            <FundraisingTab projects={projects} />
          )}
        </TabsContent>

        <TabsContent value="deployment" className="mt-6">
          <DeploymentTab />
        </TabsContent>

        <TabsContent value="distributions" className="mt-6">
          <DistributionsTab />
        </TabsContent>

        <TabsContent value="projections" className="mt-6">
          <ProjectionsTab />
        </TabsContent>

        <TabsContent value="economics" className="mt-6">
          <EconomicsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
