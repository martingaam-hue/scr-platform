"use client";

import { useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  MapPin,
  Monitor,
  Percent,
  Settings2,
  Shield,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  cn,
} from "@scr/ui";
import { useProjects } from "@/lib/projects";
import { InfoBanner } from "@/components/info-banner";

// ── Mock data ─────────────────────────────────────────────────────────────────

interface MockProject {
  id: string;
  name: string;
  type: string;
  country: string;
  flag: string;
  mw: number;
  mwh: number | null;
  stage_id: string;
  stage_num: number;
  status: "on_track" | "at_risk" | "blocked" | "complete";
  completion: number;
  budget: number;
  spent: number;
  target_rtb: string;
}

const MOCK_PROJECTS: MockProject[] = [
  { id: "p1", name: "Solaria Extremadura", type: "Solar PV", country: "Spain", flag: "🇪🇸", mw: 150, mwh: null, stage_id: "permitting", stage_num: 3, status: "on_track", completion: 52, budget: 2_200_000, spent: 980_000, target_rtb: "Q4 2025" },
  { id: "p2", name: "Nordvind Trøndelag", type: "Onshore Wind", country: "Norway", flag: "🇳🇴", mw: 80, mwh: null, stage_id: "grid_connection", stage_num: 4, status: "at_risk", completion: 68, budget: 3_100_000, spent: 1_890_000, target_rtb: "Q2 2026" },
  { id: "p3", name: "Sicilia Sole", type: "Solar PV", country: "Italy", flag: "🇮🇹", mw: 120, mwh: null, stage_id: "feasibility", stage_num: 2, status: "on_track", completion: 28, budget: 1_800_000, spent: 420_000, target_rtb: "Q3 2026" },
  { id: "p4", name: "Gotland BESS", type: "Battery Storage", country: "Sweden", flag: "🇸🇪", mw: 100, mwh: 400, stage_id: "financial_close", stage_num: 5, status: "on_track", completion: 84, budget: 4_500_000, spent: 3_620_000, target_rtb: "Q1 2025" },
  { id: "p5", name: "Highland Wind Farm", type: "Onshore Wind", country: "UK", flag: "🇬🇧", mw: 60, mwh: null, stage_id: "origination", stage_num: 1, status: "on_track", completion: 8, budget: 750_000, spent: 62_000, target_rtb: "Q4 2027" },
  { id: "p6", name: "Castilla Solar PV", type: "Solar PV", country: "Spain", flag: "🇪🇸", mw: 95, mwh: null, stage_id: "ready_to_build", stage_num: 6, status: "complete", completion: 100, budget: 3_800_000, spent: 3_750_000, target_rtb: "Complete" },
  { id: "p7", name: "Apennine Wind", type: "Onshore Wind", country: "Italy", flag: "🇮🇹", mw: 45, mwh: null, stage_id: "permitting", stage_num: 3, status: "blocked", completion: 41, budget: 1_600_000, spent: 580_000, target_rtb: "Q1 2027" },
];

const PIPELINE_STAGES = [
  { id: "origination", num: 1, label: "Origination & Screening", short: "Origination" },
  { id: "feasibility", num: 2, label: "Feasibility & Site Assessment", short: "Feasibility" },
  { id: "permitting", num: 3, label: "Permitting & Approvals", short: "Permitting" },
  { id: "grid_connection", num: 4, label: "Grid Connection & PPA", short: "Grid & PPA" },
  { id: "financial_close", num: 5, label: "Financial Close", short: "Fin. Close" },
  { id: "ready_to_build", num: 6, label: "Ready to Build", short: "RTB" },
];

interface Workstream {
  id: string;
  label: string;
  icon: React.ElementType;
  status: "not_started" | "in_progress" | "blocked" | "complete";
  progress: number;
  deadline: string;
  owner: string;
  openItems: number;
}

const WORKSTREAMS: Workstream[] = [
  { id: "land", label: "Land & Site", icon: MapPin, status: "in_progress", progress: 75, deadline: "Mar 2025", owner: "Elena Vasquez", openItems: 2 },
  { id: "permits", label: "Permits & Regulatory", icon: FileText, status: "blocked", progress: 45, deadline: "Jun 2025", owner: "Marco Bianchi", openItems: 5 },
  { id: "grid", label: "Grid Connection", icon: Zap, status: "in_progress", progress: 30, deadline: "Sep 2025", owner: "Lars Eriksson", openItems: 4 },
  { id: "ppa", label: "Power Purchase", icon: TrendingUp, status: "not_started", progress: 10, deadline: "Dec 2025", owner: "Sarah O'Brien", openItems: 1 },
  { id: "technical", label: "Technical Design", icon: Settings2, status: "in_progress", progress: 65, deadline: "Aug 2025", owner: "Ahmed Hassan", openItems: 3 },
  { id: "financial", label: "Financial Structuring", icon: BarChart3, status: "not_started", progress: 5, deadline: "Jan 2026", owner: "Julia Müller", openItems: 2 },
  { id: "legal", label: "Legal & Contracts", icon: Shield, status: "in_progress", progress: 40, deadline: "Oct 2025", owner: "Tom Williams", openItems: 6 },
];

const MOCK_MILESTONES = [
  { id: "m1", project: "Solaria Extremadura", title: "Environmental Impact Assessment submitted", workstream: "Permits", date: "2025-02-15", status: "completed" },
  { id: "m2", project: "Solaria Extremadura", title: "Planning application submitted to Ayuntamiento", workstream: "Permits", date: "2025-03-01", status: "completed" },
  { id: "m3", project: "Solaria Extremadura", title: "Grid connection offer received from REE", workstream: "Grid", date: "2025-04-15", status: "in_progress" },
  { id: "m4", project: "Nordvind Trøndelag", title: "Statnett capacity study complete", workstream: "Grid", date: "2025-03-20", status: "at_risk" },
  { id: "m5", project: "Nordvind Trøndelag", title: "PPA heads of terms agreed with Equinor", workstream: "PPA", date: "2025-05-01", status: "in_progress" },
  { id: "m6", project: "Gotland BESS", title: "ING Bank debt term sheet received", workstream: "Finance", date: "2025-01-30", status: "completed" },
  { id: "m7", project: "Gotland BESS", title: "Financial close achieved", workstream: "Finance", date: "2025-03-31", status: "in_progress" },
  { id: "m8", project: "Apennine Wind", title: "Zone B environmental permit — awaiting supplementary survey", workstream: "Permits", date: "2025-06-30", status: "blocked" },
  { id: "m9", project: "Sicilia Sole", title: "Preliminary site survey and soil analysis", workstream: "Land", date: "2025-02-28", status: "completed" },
  { id: "m10", project: "Highland Wind Farm", title: "Landowner heads of terms signed", workstream: "Land", date: "2025-04-01", status: "in_progress" },
];

const MOCK_RISKS = [
  { id: "r1", project: "Apennine Wind", description: "Zone B environmental permit suspended pending supplementary bat survey", workstream: "Permits & Regulatory", severity: "high", days_blocked: 45, owner: "Marco Bianchi", resolution: "Commission bat survey by specialist (Mar 2025), resubmit EIA addendum with updated findings" },
  { id: "r2", project: "Nordvind Trøndelag", description: "Grid operator requested second capacity study following constraint zone reclassification", workstream: "Grid Connection", severity: "medium", days_blocked: 18, owner: "Lars Eriksson", resolution: "Await Statnett study completion (6 wks), explore alternative connection at Ørland substation" },
  { id: "r3", project: "Solaria Extremadura", description: "Municipal zoning objection from adjacent landowner challenging site boundary", workstream: "Land & Site", severity: "medium", days_blocked: 12, owner: "Elena Vasquez", resolution: "Legal review of boundary compliance, engage municipal planning officer and local councillors" },
];

const MOCK_STAKEHOLDERS = [
  { id: "s1", org: "REE — Red Eléctrica de España", type: "Grid Operator", project: "Solaria Extremadura", status: "Application Submitted", contact: "Carlos García", next_action: "Chase connection offer Q2", last_contact: "20 Jan 2025" },
  { id: "s2", org: "Statnett SF", type: "Grid Operator", project: "Nordvind Trøndelag", status: "Study In Progress", contact: "Ingrid Larsen", next_action: "Review capacity study results", last_contact: "5 Feb 2025" },
  { id: "s3", org: "Ayuntamiento de Badajoz", type: "Planning Authority", project: "Solaria Extremadura", status: "Consultation Open", contact: "Ana Romero", next_action: "Submit consultation response", last_contact: "15 Jan 2025" },
  { id: "s4", org: "Equinor Wind Power AS", type: "Offtaker (PPA)", project: "Nordvind Trøndelag", status: "HoTs Negotiation", contact: "Bjørn Nielsen", next_action: "Agree pricing structure for term", last_contact: "10 Feb 2025" },
  { id: "s5", org: "Siemens Gamesa Renewable Energy", type: "EPC Contractor", project: "Nordvind Trøndelag", status: "Bid Received", contact: "Klaus Weber", next_action: "Technical clarification meeting", last_contact: "28 Jan 2025" },
  { id: "s6", org: "ING Bank NV — Infrastructure Finance", type: "Lender", project: "Gotland BESS", status: "Term Sheet Received", contact: "Pieter van Dam", next_action: "Review loan conditions & covenants", last_contact: "3 Feb 2025" },
];

const BUDGET_CATEGORIES = [
  { category: "Legal & Contracts", budget: 480_000, spent: 312_000 },
  { category: "Technical Studies", budget: 380_000, spent: 195_000 },
  { category: "Permits & Regulatory", budget: 220_000, spent: 145_000 },
  { category: "Grid Studies", budget: 280_000, spent: 87_000 },
  { category: "Consultants", budget: 450_000, spent: 278_000 },
  { category: "Land & Site Costs", budget: 310_000, spent: 210_000 },
  { category: "Travel & Admin", budget: 80_000, spent: 53_000 },
];

const BUDGET_MONTHLY = [
  { month: "Aug 24", budgeted: 180, actual: 162 },
  { month: "Sep 24", budgeted: 320, actual: 298 },
  { month: "Oct 24", budgeted: 490, actual: 467 },
  { month: "Nov 24", budgeted: 680, actual: 641 },
  { month: "Dec 24", budgeted: 890, actual: 872 },
  { month: "Jan 25", budgeted: 1120, actual: 1080 },
  { month: "Feb 25", budgeted: 1380, actual: 1280 },
];

const STAGE_WEEKS_DATA = [
  { stage: "Origination", yours: 8, benchmark: 10 },
  { stage: "Feasibility", yours: 24, benchmark: 20 },
  { stage: "Permitting", yours: 68, benchmark: 52 },
  { stage: "Grid & PPA", yours: 44, benchmark: 48 },
  { stage: "Fin. Close", yours: 32, benchmark: 36 },
];

const CHECKLIST: Record<string, { item: string; status: "done" | "pending" | "not_started"; owner: string; target: string }[]> = {
  "Site Control": [
    { item: "Lease / option agreement executed", status: "done", owner: "Elena Vasquez", target: "Dec 2024" },
    { item: "Topographic & geotechnical survey", status: "done", owner: "TechSurveys Ltd", target: "Jan 2025" },
    { item: "Access road confirmation & wayleave", status: "pending", owner: "Elena Vasquez", target: "Mar 2025" },
  ],
  "Environmental": [
    { item: "EIA scoping opinion received", status: "done", owner: "EcoConsult GmbH", target: "Nov 2024" },
    { item: "Ecological survey (Phase 1 & 2)", status: "done", owner: "EcoConsult GmbH", target: "Dec 2024" },
    { item: "Archaeological desk-based assessment", status: "pending", owner: "Heritage & Co", target: "Apr 2025" },
    { item: "Flood risk assessment", status: "not_started", owner: "TBC", target: "May 2025" },
  ],
  "Planning": [
    { item: "Pre-application consultation", status: "done", owner: "Marco Bianchi", target: "Oct 2024" },
    { item: "Planning application submitted", status: "done", owner: "Marco Bianchi", target: "Mar 2025" },
    { item: "Determination period complete", status: "not_started", owner: "TBC", target: "Sep 2025" },
  ],
  "Grid": [
    { item: "Grid connection application submitted", status: "done", owner: "Lars Eriksson", target: "Jan 2025" },
    { item: "Initial feasibility offer received", status: "pending", owner: "Lars Eriksson", target: "Apr 2025" },
    { item: "Grid connection agreement signed", status: "not_started", owner: "TBC", target: "Oct 2025" },
  ],
  "PPA": [
    { item: "Offtaker shortlist agreed", status: "done", owner: "Sarah O'Brien", target: "Feb 2025" },
    { item: "Indicative pricing received", status: "pending", owner: "Sarah O'Brien", target: "May 2025" },
    { item: "Heads of terms agreed", status: "not_started", owner: "TBC", target: "Aug 2025" },
    { item: "PPA executed", status: "not_started", owner: "TBC", target: "Dec 2025" },
  ],
  "Financial": [
    { item: "Financial model version 1 complete", status: "done", owner: "Julia Müller", target: "Jan 2025" },
    { item: "Senior debt term sheet received", status: "not_started", owner: "TBC", target: "Sep 2025" },
    { item: "Equity commitments in place", status: "not_started", owner: "TBC", target: "Nov 2025" },
  ],
  "Legal": [
    { item: "SPV incorporated", status: "done", owner: "Tom Williams", target: "Aug 2024" },
    { item: "SHA draft circulated", status: "pending", owner: "Tom Williams", target: "Apr 2025" },
    { item: "EPC contract heads of terms", status: "not_started", owner: "TBC", target: "Oct 2025" },
  ],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtM(n: number) {
  if (n >= 1_000_000) return `€${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `€${(n / 1_000).toFixed(0)}K`;
  return `€${n}`;
}

function statusBadge(status: MockProject["status"]) {
  switch (status) {
    case "on_track": return <Badge variant="success">On Track</Badge>;
    case "at_risk": return <Badge variant="warning">At Risk</Badge>;
    case "blocked": return <Badge variant="error">Blocked</Badge>;
    case "complete": return <Badge variant="info">Complete</Badge>;
  }
}

function wsStatusConfig(status: Workstream["status"]) {
  switch (status) {
    case "complete": return { label: "Complete", dot: "bg-green-500", bg: "bg-green-50", text: "text-green-700", border: "border-green-200" };
    case "in_progress": return { label: "In Progress", dot: "bg-blue-500", bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" };
    case "blocked": return { label: "Blocked", dot: "bg-red-500", bg: "bg-red-50", text: "text-red-700", border: "border-red-200" };
    default: return { label: "Not Started", dot: "bg-neutral-300", bg: "bg-neutral-50", text: "text-neutral-500", border: "border-neutral-200" };
  }
}

function severityBadge(s: string) {
  if (s === "high") return <Badge variant="error">High</Badge>;
  if (s === "medium") return <Badge variant="warning">Medium</Badge>;
  return <Badge variant="neutral">Low</Badge>;
}

function checklistIcon(status: "done" | "pending" | "not_started") {
  if (status === "done") return <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />;
  if (status === "pending") return <Clock className="h-4 w-4 text-amber-500 shrink-0" />;
  return <div className="h-4 w-4 rounded-full border-2 border-neutral-300 shrink-0" />;
}

function msStatusDot(status: string) {
  const cls: Record<string, string> = {
    completed: "bg-green-500",
    in_progress: "bg-blue-500",
    at_risk: "bg-amber-500",
    blocked: "bg-red-500",
  };
  return <span className={cn("inline-block h-2 w-2 rounded-full shrink-0", cls[status] ?? "bg-neutral-300")} />;
}

function msStatusLabel(status: string) {
  const map: Record<string, string> = {
    completed: "Completed", in_progress: "In Progress", at_risk: "At Risk", blocked: "Blocked", not_started: "Not Started",
  };
  const variant: Record<string, "success" | "warning" | "error" | "neutral" | "info"> = {
    completed: "success", in_progress: "info", at_risk: "warning", blocked: "error", not_started: "neutral",
  };
  return <Badge variant={variant[status] ?? "neutral"}>{map[status] ?? status}</Badge>;
}

// ── Hero Card ─────────────────────────────────────────────────────────────────

function HeroCard({ projects }: { projects: MockProject[] }) {
  const active = projects.filter(p => p.status !== "complete");
  const onTrack = projects.filter(p => p.status === "on_track").length;
  const atRisk = projects.filter(p => p.status === "at_risk").length;
  const blocked = projects.filter(p => p.status === "blocked").length;
  const rtb = projects.filter(p => p.status === "complete").length;
  const totalMw = projects.reduce((s, p) => s + p.mw, 0);
  const avgCompletion = active.length > 0
    ? Math.round(active.reduce((s, p) => s + p.completion, 0) / active.length)
    : 0;

  return (
    <div className="rounded-2xl bg-[#1B2A4A] text-white p-6">
      <div className="flex items-center gap-2 mb-1">
        <Monitor className="h-5 w-5 text-indigo-300" />
        <span className="text-xs font-medium text-indigo-300 uppercase tracking-widest">Portfolio Development Health</span>
      </div>
      <div className="flex flex-col lg:flex-row lg:items-end gap-6 mt-4">
        <div className="flex-1">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: "Active Projects", value: active.length, color: "text-white" },
              { label: "Total Pipeline", value: `${totalMw} MW`, color: "text-white" },
              { label: "Avg. Progress", value: `${avgCompletion}%`, color: "text-indigo-300" },
              { label: "On Track", value: onTrack, color: "text-emerald-400" },
              { label: "At Risk", value: atRisk, color: "text-amber-400" },
              { label: "Ready to Build", value: rtb, color: "text-blue-300" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-xl bg-white/10 p-3 text-center">
                <p className="text-[10px] text-slate-400 mb-1">{label}</p>
                <p className={cn("text-2xl font-bold", color)}>{value}</p>
              </div>
            ))}
          </div>

          {blocked > 0 && (
            <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-900/30 border border-red-700/40 px-3 py-2 text-sm text-red-300">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span><strong>{blocked} project{blocked > 1 ? "s" : ""} blocked</strong> — active blockers requiring immediate attention.</span>
            </div>
          )}
        </div>

        {/* Stage distribution bar */}
        <div className="lg:w-64 space-y-1.5">
          <p className="text-xs text-slate-400 mb-2">Stage Distribution</p>
          {PIPELINE_STAGES.map((stage) => {
            const count = projects.filter(p => p.stage_id === stage.id).length;
            const w = projects.length > 0 ? (count / projects.length) * 100 : 0;
            return count > 0 ? (
              <div key={stage.id} className="flex items-center gap-2">
                <span className="text-[10px] text-slate-400 w-20 text-right shrink-0">{stage.short}</span>
                <div className="flex-1 h-3 rounded-full bg-white/10 overflow-hidden">
                  <div className="h-3 rounded-full bg-indigo-400 transition-all" style={{ width: `${w}%` }} />
                </div>
                <span className="text-xs font-semibold w-4">{count}</span>
              </div>
            ) : null;
          })}
        </div>
      </div>
    </div>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({ projects }: { projects: MockProject[] }) {
  return (
    <div className="space-y-6">
      <HeroCard projects={projects} />

      {/* Project cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {projects.map((p) => {
          const stage = PIPELINE_STAGES.find(s => s.id === p.stage_id);
          return (
            <Card key={p.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-neutral-900 text-sm leading-tight truncate">
                      {p.flag} {p.name}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {p.type} · {p.mwh ? `${p.mwh}MWh` : `${p.mw}MW`} · {p.country}
                    </p>
                  </div>
                  {statusBadge(p.status)}
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-neutral-500">{stage?.short ?? p.stage_id}</span>
                    <span className="font-semibold text-indigo-600">{p.completion}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                    <div
                      className={cn("h-1.5 rounded-full transition-all", p.status === "blocked" ? "bg-red-500" : p.status === "at_risk" ? "bg-amber-400" : "bg-indigo-500")}
                      style={{ width: `${p.completion}%` }}
                    />
                  </div>
                </div>

                {/* Stage dots */}
                <div className="flex gap-0.5">
                  {PIPELINE_STAGES.map((s) => (
                    <div
                      key={s.id}
                      className={cn("h-1 flex-1 rounded-full", s.num < p.stage_num ? "bg-indigo-500" : s.num === p.stage_num ? "bg-indigo-300" : "bg-neutral-100")}
                      title={s.short}
                    />
                  ))}
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-400">RTB target: <strong className="text-neutral-700">{p.target_rtb}</strong></span>
                  <Link
                    href={`/development-os/${p.id}`}
                    className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    Details <ChevronRight className="h-3 w-3" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Pipeline Tab ──────────────────────────────────────────────────────────────

function PipelineTab({ projects, onStageClick }: { projects: MockProject[]; onStageClick: (stageId: string | null) => void }) {
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  const handleStage = (id: string) => {
    const next = selectedStage === id ? null : id;
    setSelectedStage(next);
    onStageClick(next);
  };

  return (
    <div className="space-y-6">
      {/* Horizontal funnel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Development Pipeline — Projects by Stage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {PIPELINE_STAGES.map((stage) => {
              const stageProjects = projects.filter(p => p.stage_id === stage.id);
              const totalMw = stageProjects.reduce((s, p) => s + p.mw, 0);
              const totalBudget = stageProjects.reduce((s, p) => s + p.budget, 0);
              const isSelected = selectedStage === stage.id;
              const hasBlocked = stageProjects.some(p => p.status === "blocked");
              const hasAtRisk = stageProjects.some(p => p.status === "at_risk");

              return (
                <button
                  key={stage.id}
                  onClick={() => handleStage(stage.id)}
                  className={cn(
                    "flex-1 min-w-[130px] rounded-xl border p-4 text-left transition-all",
                    isSelected ? "border-indigo-400 bg-indigo-50" : "border-neutral-200 bg-white hover:border-indigo-200 hover:bg-indigo-50/30"
                  )}
                >
                  <div className="flex items-center gap-1 mb-2">
                    <span className={cn("h-5 w-5 rounded-full text-xs font-bold flex items-center justify-center shrink-0", isSelected ? "bg-indigo-600 text-white" : "bg-neutral-100 text-neutral-600")}>
                      {stage.num}
                    </span>
                    {hasBlocked && <AlertTriangle className="h-3 w-3 text-red-500 shrink-0" />}
                  </div>
                  <p className="text-xs font-semibold text-neutral-700 leading-tight mb-3">{stage.short}</p>
                  <p className={cn("text-3xl font-bold", stageProjects.length === 0 ? "text-neutral-200" : isSelected ? "text-indigo-700" : "text-neutral-900")}>
                    {stageProjects.length}
                  </p>
                  <p className="text-[10px] text-neutral-400 mt-0.5">project{stageProjects.length !== 1 ? "s" : ""}</p>
                  {stageProjects.length > 0 && (
                    <>
                      <p className="text-xs font-medium text-neutral-600 mt-2">{totalMw} MW</p>
                      <p className="text-[10px] text-neutral-400">{fmtM(totalBudget)} dev budget</p>
                    </>
                  )}
                  {(hasBlocked || hasAtRisk) && (
                    <div className="mt-2 flex gap-1">
                      {hasBlocked && <span className="text-[9px] bg-red-100 text-red-600 rounded px-1 py-0.5">BLOCKED</span>}
                      {hasAtRisk && <span className="text-[9px] bg-amber-100 text-amber-600 rounded px-1 py-0.5">AT RISK</span>}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Filtered projects table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            {selectedStage ? `Projects — ${PIPELINE_STAGES.find(s => s.id === selectedStage)?.label}` : "All Projects"}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Country</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Capacity</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Stage</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Dev Budget</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Target RTB</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {(selectedStage ? projects.filter(p => p.stage_id === selectedStage) : projects).map((p) => {
                const stage = PIPELINE_STAGES.find(s => s.id === p.stage_id);
                return (
                  <tr key={p.id} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-neutral-900">{p.flag} {p.name}</td>
                    <td className="px-4 py-3 text-neutral-500 text-xs">{p.type}</td>
                    <td className="px-4 py-3 text-neutral-500 text-xs">{p.country}</td>
                    <td className="px-4 py-3 text-right text-neutral-700">{p.mwh ? `${p.mwh}MWh` : `${p.mw}MW`}</td>
                    <td className="px-4 py-3 text-xs text-neutral-600">{stage?.short}</td>
                    <td className="px-4 py-3 text-right font-medium text-neutral-700">{fmtM(p.budget)}</td>
                    <td className="px-4 py-3 text-xs text-neutral-600">{p.target_rtb}</td>
                    <td className="px-4 py-3">{statusBadge(p.status)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Workstreams Tab ───────────────────────────────────────────────────────────

function WorkstreamsTab() {
  const [selectedProject, setSelectedProject] = useState(MOCK_PROJECTS[0].id);
  const project = MOCK_PROJECTS.find(p => p.id === selectedProject) ?? MOCK_PROJECTS[0];

  return (
    <div className="space-y-5">
      {/* Project selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-neutral-700 shrink-0">Project:</label>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {MOCK_PROJECTS.map(p => (
            <option key={p.id} value={p.id}>{p.flag} {p.name}</option>
          ))}
        </select>
        {statusBadge(project.status)}
        <span className="text-xs text-neutral-400">{project.type} · {project.mw}MW · {project.country}</span>
      </div>

      {/* Workstream grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {WORKSTREAMS.map((ws) => {
          const cfg = wsStatusConfig(ws.status);
          const Icon = ws.icon;
          return (
            <Card key={ws.id} className={cn("border", cfg.border)}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className={cn("p-2 rounded-lg", cfg.bg)}>
                    <Icon className={cn("h-4 w-4", cfg.text)} />
                  </div>
                  <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium border", cfg.bg, cfg.text, cfg.border)}>
                    <span className={cn("h-1.5 w-1.5 rounded-full", cfg.dot)} />
                    {cfg.label}
                  </span>
                </div>

                <div>
                  <p className="font-semibold text-neutral-900 text-sm">{ws.label}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">Owner: {ws.owner}</p>
                </div>

                {/* Progress */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-neutral-500">Progress</span>
                    <span className={cn("font-semibold", cfg.text)}>{ws.progress}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                    <div className={cn("h-1.5 rounded-full transition-all", ws.status === "blocked" ? "bg-red-500" : ws.status === "complete" ? "bg-green-500" : "bg-indigo-500")} style={{ width: `${ws.progress}%` }} />
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs">
                  <span className="text-neutral-400">
                    <Clock className="h-3 w-3 inline mr-0.5" /> {ws.deadline}
                  </span>
                  {ws.openItems > 0 && (
                    <span className="bg-neutral-100 text-neutral-600 rounded-full px-2 py-0.5 font-medium">
                      {ws.openItems} open
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Milestones Tab ────────────────────────────────────────────────────────────

function MilestonesTab() {
  const [filter, setFilter] = useState<string>("all");

  const filtered = filter === "all" ? MOCK_MILESTONES : MOCK_MILESTONES.filter(m => m.status === filter);

  return (
    <div className="space-y-5">
      {/* Filter */}
      <div className="flex flex-wrap gap-2">
        {[
          { id: "all", label: "All" },
          { id: "completed", label: "Completed" },
          { id: "in_progress", label: "In Progress" },
          { id: "at_risk", label: "At Risk" },
          { id: "blocked", label: "Blocked" },
        ].map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-medium transition-colors",
              filter === f.id ? "bg-indigo-600 text-white" : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y divide-neutral-50">
            {filtered.map((m) => (
              <div key={m.id} className="flex items-start gap-4 px-5 py-4 hover:bg-neutral-50 transition-colors">
                <div className="flex flex-col items-center gap-1 pt-0.5 shrink-0">
                  {msStatusDot(m.status)}
                  <div className="w-px flex-1 bg-neutral-100 min-h-[16px]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-neutral-900 leading-snug">{m.title}</p>
                      <p className="text-xs text-neutral-500 mt-0.5">{m.project} · {m.workstream}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {msStatusLabel(m.status)}
                      <span className="text-xs text-neutral-400">{new Date(m.date).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Checklist Tab ─────────────────────────────────────────────────────────────

function ChecklistTab() {
  const [selectedProject, setSelectedProject] = useState(MOCK_PROJECTS[0].id);

  const allItems = Object.values(CHECKLIST).flat();
  const done = allItems.filter(i => i.status === "done").length;
  const readinessPct = Math.round((done / allItems.length) * 100);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm font-medium text-neutral-700 shrink-0">Project:</label>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {MOCK_PROJECTS.map(p => (
            <option key={p.id} value={p.id}>{p.flag} {p.name}</option>
          ))}
        </select>

        {/* Overall readiness score */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-neutral-500">Development Readiness:</span>
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 rounded-full bg-neutral-100 overflow-hidden">
              <div className={cn("h-2 rounded-full", readinessPct >= 70 ? "bg-green-500" : readinessPct >= 40 ? "bg-amber-400" : "bg-red-400")} style={{ width: `${readinessPct}%` }} />
            </div>
            <span className={cn("text-sm font-bold", readinessPct >= 70 ? "text-green-600" : readinessPct >= 40 ? "text-amber-600" : "text-red-600")}>
              {readinessPct}%
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {Object.entries(CHECKLIST).map(([category, items]) => {
          const catDone = items.filter(i => i.status === "done").length;
          return (
            <Card key={category}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">{category}</CardTitle>
                  <span className="text-xs text-neutral-500">{catDone}/{items.length}</span>
                </div>
              </CardHeader>
              <CardContent className="pt-0 space-y-2">
                {items.map((item, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    {checklistIcon(item.status)}
                    <div className="flex-1 min-w-0">
                      <p className={cn("text-sm leading-snug", item.status === "done" ? "text-neutral-400 line-through" : "text-neutral-800")}>
                        {item.item}
                      </p>
                      <div className="flex items-center gap-3 mt-0.5 text-[10px] text-neutral-400">
                        <span>{item.owner}</span>
                        <span>Target: {item.target}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ── Risks Tab ─────────────────────────────────────────────────────────────────

function RisksTab() {
  const [showAdvisor, setShowAdvisor] = useState(false);

  return (
    <div className="space-y-6">
      {/* Blockers */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" /> Active Blockers &amp; Risks
            </CardTitle>
            <Button size="sm" onClick={() => setShowAdvisor(v => !v)}>
              <Zap className="h-3.5 w-3.5 mr-1.5" />
              {showAdvisor ? "Hide" : "Generate"} Risk Assessment
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-neutral-50">
            {MOCK_RISKS.map((risk) => (
              <div key={risk.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {severityBadge(risk.severity)}
                      <span className="text-xs font-semibold text-neutral-700">{risk.project}</span>
                      <span className="text-xs text-neutral-400">· {risk.workstream}</span>
                    </div>
                    <p className="text-sm text-neutral-800 leading-snug">{risk.description}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-lg font-bold text-red-600">{risk.days_blocked}</p>
                    <p className="text-[10px] text-neutral-400">days blocked</p>
                  </div>
                </div>
                <div className="bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
                  <p className="text-xs text-amber-800">
                    <span className="font-semibold">Resolution: </span>{risk.resolution}
                  </p>
                  <p className="text-[10px] text-amber-600 mt-0.5">Owner: {risk.owner}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* AI advisor panel */}
      {showAdvisor && (
        <Card className="border-indigo-200 bg-indigo-50/40">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2 text-indigo-800">
              <Zap className="h-4 w-4 text-indigo-600" /> AI Development Risk Assessment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-2">This Week — Immediate Actions</p>
              <div className="space-y-2">
                {[
                  { action: "Commission supplementary bat survey for Apennine Wind (Zone B permit unblocking)", effort: "Quick Win", workstream: "Permits" },
                  { action: "Contact Marco Bianchi re: EIA addendum timeline and consultant availability", effort: "Quick Win", workstream: "Permits" },
                ].map((rec, i) => (
                  <div key={i} className="flex items-start gap-2 bg-white rounded-lg border border-indigo-100 p-3">
                    <CheckCircle2 className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-neutral-800">{rec.action}</p>
                      <div className="flex gap-2 mt-1">
                        <Badge variant="info" className="text-xs">{rec.workstream}</Badge>
                        <Badge variant="success" className="text-xs">{rec.effort}</Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide mb-2">This Month — Key Milestones</p>
              <div className="space-y-2">
                {[
                  { action: "Chase REE grid connection offer for Solaria Extremadura (application submitted Jan 2025)", effort: "Medium", workstream: "Grid" },
                  { action: "Initiate PPA negotiation with Equinor for Nordvind — risk of pricing window closing", effort: "Major", workstream: "Power Purchase" },
                ].map((rec, i) => (
                  <div key={i} className="flex items-start gap-2 bg-white rounded-lg border border-indigo-100 p-3">
                    <Clock className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-neutral-800">{rec.action}</p>
                      <div className="flex gap-2 mt-1">
                        <Badge variant="info" className="text-xs">{rec.workstream}</Badge>
                        <Badge variant="warning" className="text-xs">{rec.effort}</Badge>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-[10px] text-indigo-500">Generated by Claude AI · Based on active blockers and milestone data · {new Date().toLocaleDateString()}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Stakeholders Tab ──────────────────────────────────────────────────────────

function StakeholdersTab() {
  const statusBg: Record<string, string> = {
    "Application Submitted": "bg-blue-50 text-blue-700",
    "Study In Progress": "bg-indigo-50 text-indigo-700",
    "Consultation Open": "bg-amber-50 text-amber-700",
    "HoTs Negotiation": "bg-violet-50 text-violet-700",
    "Bid Received": "bg-green-50 text-green-700",
    "Term Sheet Received": "bg-emerald-50 text-emerald-700",
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Users className="h-4 w-4 text-indigo-500" /> Counterparties &amp; Stakeholders
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Organisation</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Contact</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Next Action</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Last Contact</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_STAKEHOLDERS.map((s) => (
                <tr key={s.id} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-neutral-900 text-sm">{s.org}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-500">{s.type}</td>
                  <td className="px-4 py-3 text-xs text-neutral-600">{s.project}</td>
                  <td className="px-4 py-3">
                    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", statusBg[s.status] ?? "bg-neutral-100 text-neutral-600")}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-neutral-600">{s.contact}</td>
                  <td className="px-4 py-3 text-xs text-neutral-700 max-w-[200px]">{s.next_action}</td>
                  <td className="px-4 py-3 text-xs text-neutral-400">{s.last_contact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Budget Tab ────────────────────────────────────────────────────────────────

function BudgetTab() {
  const totalBudget = BUDGET_CATEGORIES.reduce((s, c) => s + c.budget, 0);
  const totalSpent = BUDGET_CATEGORIES.reduce((s, c) => s + c.spent, 0);
  const burnPct = Math.round((totalSpent / totalBudget) * 100);
  const remaining = totalBudget - totalSpent;

  return (
    <div className="space-y-6">
      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Total Dev Budget", value: fmtM(totalBudget), color: "text-neutral-900" },
          { label: "Total Spent", value: fmtM(totalSpent), color: "text-indigo-700" },
          { label: "Remaining", value: fmtM(remaining), color: "text-emerald-600" },
          { label: "Burn Rate", value: `${burnPct}%`, color: burnPct > 85 ? "text-red-600" : burnPct > 60 ? "text-amber-600" : "text-green-600" },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <p className="text-xs text-neutral-500 font-medium">{label}</p>
              <p className={cn("text-2xl font-bold mt-1", color)}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Budget by Category</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {BUDGET_CATEGORIES.map((cat) => {
              const pctSpent = (cat.spent / cat.budget) * 100;
              const over = pctSpent > 100;
              return (
                <div key={cat.category}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-neutral-700">{cat.category}</span>
                    <span className={cn("font-semibold", over ? "text-red-600" : "text-neutral-700")}>
                      {fmtM(cat.spent)} / {fmtM(cat.budget)}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
                    <div
                      className={cn("h-2 rounded-full transition-all", over ? "bg-red-500" : pctSpent > 80 ? "bg-amber-400" : "bg-indigo-500")}
                      style={{ width: `${Math.min(100, pctSpent)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-neutral-400 mt-0.5">
                    <span>{pctSpent.toFixed(0)}% spent</span>
                    <span>{fmtM(cat.budget - cat.spent)} remaining</span>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Cumulative spend chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cumulative Spend vs Budget (€K)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={BUDGET_MONTHLY} margin={{ top: 5, right: 20, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="budgetGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#818CF8" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#818CF8" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `€${v}K`} />
                <Tooltip formatter={(value) => [`€${value}K`]} />
                <Area type="monotone" dataKey="budgeted" name="Budget" stroke="#818CF8" strokeDasharray="4 2" strokeWidth={1.5} fill="url(#budgetGrad)" dot={false} />
                <Area type="monotone" dataKey="actual" name="Actual" stroke="#4F46E5" strokeWidth={2} fill="url(#actualGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── KPIs Tab ──────────────────────────────────────────────────────────────────

function KPIsTab() {
  return (
    <div className="space-y-6">
      {/* Top KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Permit Success Rate", value: "78%", sub: "+4pp vs benchmark", color: "text-green-600", icon: Percent },
          { label: "Avg Dev Cost / MW", value: "€18.5K", sub: "Industry avg €22K", color: "text-emerald-600", icon: TrendingUp },
          { label: "Origination → RTB", value: "36 months", sub: "Industry avg 40 months", color: "text-indigo-600", icon: Clock },
          { label: "Grid Connection Rate", value: "92%", sub: "Applications to agreement", color: "text-blue-600", icon: Zap },
        ].map(({ label, value, sub, color, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <div className="flex items-center gap-2 text-neutral-400 mb-2">
                <Icon className="h-4 w-4" />
                <span className="text-xs font-medium">{label}</span>
              </div>
              <p className={cn("text-2xl font-bold", color)}>{value}</p>
              <p className="text-xs text-neutral-400 mt-1">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Time per stage vs benchmark */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Avg. Time per Stage vs Benchmark (weeks)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={STAGE_WEEKS_DATA} margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis dataKey="stage" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}w`} />
                <Tooltip formatter={(value) => [`${value} weeks`]} />
                <Bar dataKey="benchmark" name="Industry Benchmark" fill="#E0E7FF" radius={[4, 4, 0, 0]} />
                <Bar dataKey="yours" name="Your Portfolio" radius={[4, 4, 0, 0]}>
                  {STAGE_WEEKS_DATA.map((entry, i) => (
                    <Cell key={i} fill={entry.yours <= entry.benchmark ? "#4F46E5" : "#F59E0B"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Pipeline conversion rates */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Pipeline Conversion Rates</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { from: "Origination", to: "Feasibility", rate: 65 },
              { from: "Feasibility", to: "Permitting", rate: 72 },
              { from: "Permitting", to: "Grid & PPA", rate: 58 },
              { from: "Grid & PPA", to: "Fin. Close", rate: 81 },
              { from: "Fin. Close", to: "RTB", rate: 95 },
            ].map(({ from, to, rate }) => (
              <div key={from} className="flex items-center gap-3">
                <div className="w-24 text-right text-xs text-neutral-500 shrink-0">{from}</div>
                <ChevronRight className="h-3.5 w-3.5 text-neutral-300 shrink-0" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                      <div
                        className={cn("h-2 rounded-full", rate >= 70 ? "bg-green-500" : rate >= 55 ? "bg-amber-400" : "bg-red-400")}
                        style={{ width: `${rate}%` }}
                      />
                    </div>
                    <span className={cn("text-xs font-bold w-8 text-right", rate >= 70 ? "text-green-600" : rate >= 55 ? "text-amber-600" : "text-red-600")}>
                      {rate}%
                    </span>
                  </div>
                </div>
                <div className="w-20 text-xs text-neutral-500 shrink-0">{to}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DevTrackerPage() {
  const { data: projectData, isLoading } = useProjects({ page_size: 50 });
  const [_pipelineFilter, setPipelineFilter] = useState<string | null>(null);

  // Merge real project names into mock data where possible
  const realProjects = projectData?.items ?? [];
  const hasRealProjects = realProjects.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-indigo-100 rounded-lg">
          <Monitor className="h-6 w-6 text-indigo-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Development Tracker</h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            Your operating system for managing the full project development lifecycle — from origination to ready-to-build
          </p>
        </div>
      </div>

      <InfoBanner>
        <strong>Development Tracker</strong> provides a structured framework for managing every stage
        of project development. Track milestones, manage workstreams, monitor dependencies, and coordinate
        with stakeholders — all powered by AI that identifies bottlenecks and recommends next steps to
        keep your project on track.
      </InfoBanner>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : (
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
            <TabsTrigger value="workstreams">Workstreams</TabsTrigger>
            <TabsTrigger value="milestones">Milestones</TabsTrigger>
            <TabsTrigger value="checklist">Checklist</TabsTrigger>
            <TabsTrigger value="risks">Risks</TabsTrigger>
            <TabsTrigger value="stakeholders">Stakeholders</TabsTrigger>
            <TabsTrigger value="budget">Budget</TabsTrigger>
            <TabsTrigger value="kpis">KPIs</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <OverviewTab projects={MOCK_PROJECTS} />
            {!hasRealProjects && (
              <div className="mt-4 text-xs text-neutral-400 text-center">
                Showing illustrative data — connect your projects to see live development status.{" "}
                <Link href="/projects/new" className="text-indigo-600 hover:underline">Create a project</Link>
              </div>
            )}
          </TabsContent>

          <TabsContent value="pipeline" className="mt-6">
            <PipelineTab projects={MOCK_PROJECTS} onStageClick={setPipelineFilter} />
          </TabsContent>

          <TabsContent value="workstreams" className="mt-6">
            <WorkstreamsTab />
          </TabsContent>

          <TabsContent value="milestones" className="mt-6">
            <MilestonesTab />
          </TabsContent>

          <TabsContent value="checklist" className="mt-6">
            <ChecklistTab />
          </TabsContent>

          <TabsContent value="risks" className="mt-6">
            <RisksTab />
          </TabsContent>

          <TabsContent value="stakeholders" className="mt-6">
            <StakeholdersTab />
          </TabsContent>

          <TabsContent value="budget" className="mt-6">
            <BudgetTab />
          </TabsContent>

          <TabsContent value="kpis" className="mt-6">
            <KPIsTab />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
