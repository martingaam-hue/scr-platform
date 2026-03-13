"use client";

import { useState } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Scale,
  Leaf,
  DollarSign,
  Sparkles,
  ChevronRight,
  ChevronDown,
  X,
  Building2,
  Calendar,
  Clock,
  Award,
  BarChart3,
  RefreshCw,
  Download,
  GitCompare,
  QrCode,
  ExternalLink,
  type LucideIcon,
} from "lucide-react";
import {
  Button,
  Card,
  CardContent,
} from "@scr/ui";
import { InfoBanner } from "@/components/info-banner";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";

// ── Types ────────────────────────────────────────────────────────────────────

type CertTier = "IRC-A" | "IRC-B" | "IRC-C" | "Uncertified";

interface PillarStatus {
  score: number | string;
  passed: boolean;       // passes IRC-A threshold
  conditional: boolean;  // passes IRC-B threshold only
  label?: string;
}

interface ProjectCert {
  id: string;
  name: string;
  sector: string;
  geography: string;
  tier: CertTier;
  readiness: number;
  pillars: {
    signal: PillarStatus;
    risk: PillarStatus;
    docs: PillarStatus;
    legal: PillarStatus;
    esg: PillarStatus;
    financial: PillarStatus;
  };
  certificationId?: string;
  certifiedDate?: string;
  expiryDate?: string;
  coValidator?: string;
  gapCount?: number;
  estTimeToNext?: string;
}

interface Gap {
  pillar: string;
  issue: string;
  effort: "Low" | "Medium" | "High";
  action: string;
}

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_PROJECTS: ProjectCert[] = [
  {
    id: "proj-001",
    name: "Alpine Hydro Partners",
    sector: "Hydropower",
    geography: "Switzerland",
    tier: "IRC-A",
    readiness: 97,
    certificationId: "IRC-2026-ALP-001",
    certifiedDate: "15-Jan-2026",
    expiryDate: "15-Jan-2027",
    coValidator: "PricewaterhouseCoopers AG",
    pillars: {
      signal:    { score: 91, passed: true,  conditional: true  },
      risk:      { score: 91, passed: true,  conditional: true  },
      docs:      { score: "98%", passed: true,  conditional: true, label: "47/48 docs" },
      legal:     { score: "Complete", passed: true,  conditional: true  },
      esg:       { score: "Full", passed: true,  conditional: true  },
      financial: { score: "Complete", passed: true,  conditional: true  },
    },
  },
  {
    id: "proj-002",
    name: "Helios Solar Portfolio Iberia",
    sector: "Solar PV",
    geography: "Spain",
    tier: "IRC-A",
    readiness: 93,
    certificationId: "IRC-2026-HEL-002",
    certifiedDate: "22-Feb-2026",
    expiryDate: "22-Feb-2027",
    coValidator: "Deloitte Spain",
    pillars: {
      signal:    { score: 87, passed: true,  conditional: true  },
      risk:      { score: 82, passed: true,  conditional: true  },
      docs:      { score: "96%", passed: true,  conditional: true, label: "46/48 docs" },
      legal:     { score: "Complete", passed: true,  conditional: true  },
      esg:       { score: "Full", passed: true,  conditional: true  },
      financial: { score: "Complete", passed: true,  conditional: true  },
    },
  },
  {
    id: "proj-003",
    name: "Adriatic Infrastructure Holdings",
    sector: "Multi-asset",
    geography: "Croatia",
    tier: "IRC-B",
    readiness: 82,
    certificationId: "IRC-2026-ADR-003",
    certifiedDate: "01-Mar-2026",
    expiryDate: "01-Sep-2026",
    pillars: {
      signal:    { score: 82, passed: true,  conditional: true  },
      risk:      { score: 85, passed: true,  conditional: true  },
      docs:      { score: "88%", passed: false, conditional: true, label: "42/48 docs" },
      legal:     { score: "Complete", passed: true,  conditional: true  },
      esg:       { score: "Partial", passed: false, conditional: true  },
      financial: { score: "Complete", passed: true,  conditional: true  },
    },
    gapCount: 6,
  },
  {
    id: "proj-004",
    name: "Thames Clean Energy",
    sector: "Tidal/Marine",
    geography: "UK",
    tier: "IRC-B",
    readiness: 78,
    certificationId: "IRC-2026-TCE-004",
    certifiedDate: "05-Mar-2026",
    expiryDate: "05-Sep-2026",
    pillars: {
      signal:    { score: 78, passed: false, conditional: true  },
      risk:      { score: 77, passed: false, conditional: true  },
      docs:      { score: "82%", passed: false, conditional: true, label: "39/48 docs" },
      legal:     { score: "Complete", passed: true,  conditional: true  },
      esg:       { score: "Partial", passed: false, conditional: true  },
      financial: { score: "Complete", passed: true,  conditional: true  },
    },
    gapCount: 8,
  },
  {
    id: "proj-005",
    name: "Nordvik Wind Cluster",
    sector: "Onshore Wind",
    geography: "Norway",
    tier: "IRC-C",
    readiness: 68,
    pillars: {
      signal:    { score: 74, passed: false, conditional: true  },
      risk:      { score: 68, passed: false, conditional: true  },
      docs:      { score: "71%", passed: false, conditional: true, label: "34/48 docs" },
      legal:     { score: "Partial", passed: false, conditional: true  },
      esg:       { score: "Partial", passed: false, conditional: true  },
      financial: { score: "Partial", passed: false, conditional: true  },
    },
    gapCount: 11,
    estTimeToNext: "2-3 months",
  },
  {
    id: "proj-006",
    name: "Nordic Biomass Solutions",
    sector: "Biomass",
    geography: "Sweden",
    tier: "IRC-C",
    readiness: 65,
    pillars: {
      signal:    { score: 71, passed: false, conditional: true  },
      risk:      { score: 73, passed: false, conditional: true  },
      docs:      { score: "64%", passed: false, conditional: false, label: "31/48 docs" },
      legal:     { score: "Partial", passed: false, conditional: true  },
      esg:       { score: "Partial", passed: false, conditional: true  },
      financial: { score: "Partial", passed: false, conditional: true  },
    },
    gapCount: 13,
    estTimeToNext: "3-4 months",
  },
  {
    id: "proj-007",
    name: "Baltic BESS Grid Storage",
    sector: "Battery Storage",
    geography: "Estonia",
    tier: "IRC-C",
    readiness: 55,
    pillars: {
      signal:    { score: 65, passed: false, conditional: true  },
      risk:      { score: 54, passed: false, conditional: false },
      docs:      { score: "62%", passed: false, conditional: false, label: "30/48 docs" },
      legal:     { score: "Partial", passed: false, conditional: true  },
      esg:       { score: "Partial", passed: false, conditional: true  },
      financial: { score: "Basic", passed: false, conditional: true  },
    },
    gapCount: 14,
    estTimeToNext: "3-4 months",
  },
  {
    id: "proj-008",
    name: "Sahara CSP Development",
    sector: "Concentrated Solar",
    geography: "Morocco",
    tier: "Uncertified",
    readiness: 38,
    pillars: {
      signal:    { score: 58, passed: false, conditional: false },
      risk:      { score: 47, passed: false, conditional: false },
      docs:      { score: "35%", passed: false, conditional: false, label: "17/48 docs" },
      legal:     { score: "Incomplete", passed: false, conditional: false },
      esg:       { score: "Not started", passed: false, conditional: false },
      financial: { score: "Preliminary", passed: false, conditional: false },
    },
    gapCount: 28,
    estTimeToNext: "4-6 months to IRC-C",
  },
];

const ALPINE_GAPS: Gap[] = [
  { pillar: "Documentation", issue: "1 document requires minor update (EIA revision)", effort: "Low", action: "Upload updated EIA to Data Room" },
];

const ADRIATIC_GAPS: Gap[] = [
  { pillar: "Documentation", issue: "6 documents missing (O&M contract, warranty docs)", effort: "Medium", action: "Complete and upload outstanding documents" },
  { pillar: "ESG", issue: "EU Taxonomy alignment at 72% — needs full assessment", effort: "Medium", action: "Run full EU Taxonomy screening via ESG Dashboard" },
];

const BALTIC_GAPS: Gap[] = [
  { pillar: "Risk", issue: "3 critical risks unmitigated (grid connection delay, permitting, supply chain)", effort: "High", action: "Document mitigation strategies in Risk Dashboard" },
  { pillar: "Documentation", issue: "18 documents missing or incomplete", effort: "High", action: "Prioritise financial model, permits, and technical spec" },
  { pillar: "ESG", issue: "Carbon impact not yet quantified", effort: "Medium", action: "Complete carbon baseline assessment" },
  { pillar: "Legal", issue: "EPC contract not executed; shareholder agreement draft only", effort: "High", action: "Finalise and execute key contracts" },
];

const CERT_RATE_TREND = [
  { month: "Oct", rate: 18 },
  { month: "Nov", rate: 22 },
  { month: "Dec", rate: 28 },
  { month: "Jan", rate: 32 },
  { month: "Feb", rate: 38 },
  { month: "Mar", rate: 43 },
];

const PILLAR_AVG = [
  { name: "Signal", avg: 74 },
  { name: "Risk", avg: 71 },
  { name: "Docs", avg: 68 },
  { name: "Legal", avg: 73 },
  { name: "ESG", avg: 66 },
  { name: "Financial", avg: 76 },
];

// ── Tier config ───────────────────────────────────────────────────────────────

const TIER_CONFIG: Record<CertTier, {
  label: string;
  color: string;
  bg: string;
  border: string;
  badgeBg: string;
  textColor: string;
  description: string;
  validity: string;
}> = {
  "IRC-A": {
    label: "IRC-A",
    color: "#15803d",
    bg: "bg-green-50",
    border: "border-green-200",
    badgeBg: "bg-green-700",
    textColor: "text-green-700",
    description: "Investment Certified",
    validity: "Valid 12 months",
  },
  "IRC-B": {
    label: "IRC-B",
    color: "#1d4ed8",
    bg: "bg-blue-50",
    border: "border-blue-200",
    badgeBg: "bg-blue-700",
    textColor: "text-blue-700",
    description: "Conditionally Ready",
    validity: "Valid 6 months",
  },
  "IRC-C": {
    label: "IRC-C",
    color: "#78716c",
    bg: "bg-stone-50",
    border: "border-stone-200",
    badgeBg: "bg-stone-500",
    textColor: "text-stone-600",
    description: "In Preparation",
    validity: "Provisional",
  },
  "Uncertified": {
    label: "—",
    color: "#9ca3af",
    bg: "bg-neutral-50",
    border: "border-neutral-200",
    badgeBg: "bg-neutral-400",
    textColor: "text-neutral-500",
    description: "Not Certified",
    validity: "—",
  },
};

// ── Pillar config ─────────────────────────────────────────────────────────────

interface PillarDef {
  key: keyof ProjectCert["pillars"];
  label: string;
  icon: LucideIcon;
  iconColor: string;
  thresholdA: string;
  thresholdB: string;
  source: string;
}

const PILLARS: PillarDef[] = [
  { key: "signal",    label: "Signal Score",        icon: Sparkles,   iconColor: "text-violet-600", thresholdA: "80+",   thresholdB: "60+",  source: "Signal Score Engine" },
  { key: "risk",      label: "Risk Management",     icon: ShieldAlert, iconColor: "text-red-600",   thresholdA: "80+",   thresholdB: "60+",  source: "Risk Dashboard" },
  { key: "docs",      label: "Documentation",       icon: FileText,    iconColor: "text-blue-600",  thresholdA: "95%+",  thresholdB: "80%+", source: "Data Room" },
  { key: "legal",     label: "Legal & Compliance",  icon: Scale,       iconColor: "text-amber-600", thresholdA: "Complete", thresholdB: "Core complete", source: "Legal Module" },
  { key: "esg",       label: "ESG Alignment",       icon: Leaf,        iconColor: "text-green-600", thresholdA: "Full",  thresholdB: "Partial OK", source: "ESG Dashboard" },
  { key: "financial", label: "Financial Robustness", icon: DollarSign, iconColor: "text-emerald-600", thresholdA: "Complete", thresholdB: "Core model", source: "Financial Module" },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function TierBadge({ tier, size = "md" }: { tier: CertTier; size?: "sm" | "md" | "lg" }) {
  const cfg = TIER_CONFIG[tier];
  const sizeClasses = {
    sm: "text-[10px] px-1.5 py-0.5",
    md: "text-xs px-2 py-0.5",
    lg: "text-sm px-3 py-1",
  };
  if (tier === "Uncertified") {
    return <span className={`inline-flex items-center gap-1 rounded font-semibold bg-neutral-100 text-neutral-500 ${sizeClasses[size]}`}>—</span>;
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded font-bold text-white ${cfg.badgeBg} ${sizeClasses[size]}`}>
      <ShieldCheck className={size === "lg" ? "h-4 w-4" : "h-3 w-3"} />
      {cfg.label}
    </span>
  );
}

function PillarCell({ pillar }: { pillar: PillarStatus }) {
  if (pillar.passed) {
    return (
      <div className="flex items-center gap-1.5">
        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
        <span className="text-xs text-neutral-700">{String(pillar.score)}</span>
      </div>
    );
  }
  if (pillar.conditional) {
    return (
      <div className="flex items-center gap-1.5">
        <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
        <span className="text-xs text-neutral-700">{String(pillar.score)}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5">
      <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
      <span className="text-xs text-neutral-700">{String(pillar.score)}</span>
    </div>
  );
}

function PillarCard({ pillar, project }: { pillar: PillarDef; project: ProjectCert }) {
  const status = project.pillars[pillar.key];
  const isPassed = status.passed;
  const isConditional = !isPassed && status.conditional;

  const cardBorder = isPassed
    ? "border-green-200 bg-green-50/40"
    : isConditional
    ? "border-amber-200 bg-amber-50/40"
    : "border-red-200 bg-red-50/40";

  const statusBadge = isPassed ? (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-green-700 bg-green-100 rounded px-1.5 py-0.5">
      <CheckCircle2 className="h-3 w-3" /> IRC-A Pass
    </span>
  ) : isConditional ? (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-100 rounded px-1.5 py-0.5">
      <AlertTriangle className="h-3 w-3" /> IRC-B Only
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-red-700 bg-red-100 rounded px-1.5 py-0.5">
      <XCircle className="h-3 w-3" /> Below Threshold
    </span>
  );

  // Compute numeric progress (0-100) for bar
  const rawScore = status.score;
  let progress = 50;
  if (typeof rawScore === "number") {
    progress = rawScore;
  } else if (typeof rawScore === "string") {
    const match = rawScore.match(/(\d+)/);
    if (match) progress = parseInt(match[1]);
    if (rawScore === "Complete" || rawScore === "Full") progress = 100;
    if (rawScore === "Partial") progress = 65;
    if (rawScore === "Basic" || rawScore === "Preliminary") progress = 40;
    if (rawScore === "Not started" || rawScore === "Incomplete") progress = 10;
  }

  return (
    <div className={`rounded-xl border p-4 flex flex-col gap-3 ${cardBorder}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-white flex items-center justify-center shadow-sm">
            <pillar.icon className={`h-4 w-4 ${pillar.iconColor}`} />
          </div>
          <div>
            <p className="text-xs font-semibold text-neutral-800">{pillar.label}</p>
            <p className="text-[10px] text-neutral-500">{pillar.source}</p>
          </div>
        </div>
        {statusBadge}
      </div>
      <div>
        <p className="text-xl font-bold text-neutral-900">{String(status.score)}</p>
        {status.label && <p className="text-[11px] text-neutral-500">{status.label}</p>}
      </div>
      <div className="space-y-1">
        <div className="flex justify-between text-[10px] text-neutral-500">
          <span>IRC-B: {pillar.thresholdB}</span>
          <span>IRC-A: {pillar.thresholdA}</span>
        </div>
        <div className="h-1.5 bg-neutral-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isPassed ? "bg-green-500" : isConditional ? "bg-amber-400" : "bg-red-400"}`}
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>
      <Button size="sm" variant="outline" className="text-[11px] h-7 mt-auto">
        View Evidence
      </Button>
    </div>
  );
}

function ProjectDetailModal({
  project,
  onClose,
}: {
  project: ProjectCert;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"pillars" | "gaps" | "history" | "audit">("pillars");
  const cfg = TIER_CONFIG[project.tier];

  const gaps: Gap[] =
    project.id === "proj-001"
      ? ALPINE_GAPS
      : project.id === "proj-003"
      ? ADRIATIC_GAPS
      : BALTIC_GAPS;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className={`${cfg.bg} border-b ${cfg.border} rounded-t-2xl p-6`}>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className={`h-14 w-14 rounded-xl ${cfg.badgeBg} flex items-center justify-center shadow`}>
                <ShieldCheck className="h-7 w-7 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="text-lg font-bold text-neutral-900">{project.name}</h2>
                  <TierBadge tier={project.tier} size="md" />
                </div>
                <p className="text-sm text-neutral-600">{project.sector} · {project.geography}</p>
                {project.certificationId && (
                  <p className="text-xs text-neutral-500 mt-0.5 font-mono">{project.certificationId}</p>
                )}
              </div>
            </div>
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-neutral-100 text-neutral-500">
              <X className="h-5 w-5" />
            </button>
          </div>

          {project.tier !== "Uncertified" && (
            <div className="mt-4 flex flex-wrap gap-4 text-sm">
              {project.certifiedDate && (
                <div className="flex items-center gap-1.5 text-neutral-600">
                  <Calendar className="h-3.5 w-3.5" />
                  Certified: <span className="font-medium">{project.certifiedDate}</span>
                </div>
              )}
              {project.expiryDate && (
                <div className="flex items-center gap-1.5 text-neutral-600">
                  <Clock className="h-3.5 w-3.5" />
                  Expires: <span className="font-medium">{project.expiryDate}</span>
                </div>
              )}
              {project.coValidator && (
                <div className="flex items-center gap-1.5 text-neutral-600">
                  <Building2 className="h-3.5 w-3.5" />
                  Co-validated by: <span className="font-medium">{project.coValidator}</span>
                </div>
              )}
              {project.certificationId && (
                <div className="flex items-center gap-1.5 text-blue-600 cursor-pointer hover:underline">
                  <ExternalLink className="h-3.5 w-3.5" />
                  verify.scrplatform.com/{project.certificationId}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="border-b border-neutral-200 flex gap-0">
          {(["pillars", "gaps", "history", "audit"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-3 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? "border-b-2 border-primary-600 text-primary-600"
                  : "text-neutral-500 hover:text-neutral-800"
              }`}
            >
              {tab === "gaps" ? "Gap Analysis" : tab === "audit" ? "Audit Trail" : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        <div className="p-6">
          {activeTab === "pillars" && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {PILLARS.map((p) => (
                <PillarCard key={p.key} pillar={p} project={project} />
              ))}
            </div>
          )}

          {activeTab === "gaps" && (
            <div className="space-y-4">
              {project.tier === "IRC-A" && gaps.length === 0 ? (
                <div className="text-center py-8 text-neutral-500">
                  <CheckCircle2 className="h-12 w-12 text-green-400 mx-auto mb-3" />
                  <p className="font-medium">No material gaps identified</p>
                  <p className="text-sm">This project meets all IRC-A requirements.</p>
                </div>
              ) : (
                <>
                  {project.estTimeToNext && (
                    <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-700">
                      <span className="font-semibold">Estimated time to next tier:</span> {project.estTimeToNext}
                    </div>
                  )}
                  <div className="space-y-3">
                    {gaps.map((gap, i) => (
                      <div key={i} className="rounded-xl border border-neutral-200 p-4 flex items-start gap-4">
                        <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 text-white text-xs font-bold ${
                          gap.effort === "High" ? "bg-red-500" : gap.effort === "Medium" ? "bg-amber-500" : "bg-green-500"
                        }`}>
                          {gap.effort[0]}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <p className="text-xs font-semibold text-neutral-800">{gap.pillar}</p>
                            <span className={`text-[10px] rounded px-1.5 py-0.5 font-medium ${
                              gap.effort === "High" ? "bg-red-100 text-red-700"
                              : gap.effort === "Medium" ? "bg-amber-100 text-amber-700"
                              : "bg-green-100 text-green-700"
                            }`}>{gap.effort} effort</span>
                          </div>
                          <p className="text-sm text-neutral-700">{gap.issue}</p>
                          <p className="text-xs text-neutral-500 mt-1">→ {gap.action}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                  <Button variant="outline" className="w-full gap-2">
                    <Sparkles className="h-4 w-4 text-violet-500" />
                    Generate AI Certification Roadmap
                  </Button>
                </>
              )}
            </div>
          )}

          {activeTab === "history" && (
            <div className="space-y-3">
              {[
                { date: project.certifiedDate ?? "15-Jan-2026", event: `Certification granted — ${project.tier}`, type: "success" },
                { date: "10 days prior", event: "Final audit completed — all pillars verified", type: "info" },
                { date: "3 weeks prior", event: "Documentation completeness reached 95%+", type: "info" },
                { date: "5 weeks prior", event: "Risk mitigation strategies filed for all critical risks", type: "info" },
                { date: "8 weeks prior", event: "Certification assessment initiated", type: "neutral" },
              ].map((ev, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className={`h-2.5 w-2.5 rounded-full mt-1.5 shrink-0 ${
                    ev.type === "success" ? "bg-green-500" : ev.type === "info" ? "bg-blue-400" : "bg-neutral-300"
                  }`} />
                  <div>
                    <p className="text-xs text-neutral-500">{ev.date}</p>
                    <p className="text-sm text-neutral-800">{ev.event}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "audit" && (
            <div className="space-y-3">
              <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-700">
                <span className="font-semibold">Immutable audit trail.</span> All evidence snapshots are locked at time of certification and cannot be modified.
              </div>
              {PILLARS.map((p) => (
                <div key={p.key} className="flex items-center justify-between py-2.5 border-b border-neutral-100 last:border-0">
                  <div className="flex items-center gap-2">
                    <p.icon className={`h-4 w-4 ${p.iconColor}`} />
                    <span className="text-sm text-neutral-800">{p.label}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-neutral-500 font-mono">
                      {project.certifiedDate ?? "—"} · {p.source}
                    </span>
                    <Button size="sm" variant="outline" className="text-[11px] h-6">
                      View
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal footer */}
        <div className="border-t border-neutral-200 p-4 flex items-center justify-between gap-3 bg-neutral-50 rounded-b-2xl">
          <div className="flex items-center gap-2">
            <QrCode className="h-4 w-4 text-neutral-400" />
            <span className="text-xs text-neutral-500">Verification: verify.scrplatform.com/{project.certificationId ?? "—"}</span>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Download className="h-3.5 w-3.5" /> Export Report
            </Button>
            <Button size="sm" className="gap-1.5">
              <RefreshCw className="h-3.5 w-3.5" /> Run Assessment
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CertificationPage() {
  const [selectedProject, setSelectedProject] = useState<ProjectCert | null>(null);
  const [filterTier, setFilterTier] = useState<CertTier | "All">("All");
  const [sortBy, setSortBy] = useState<"readiness" | "name" | "tier">("readiness");
  const [showAnalytics, setShowAnalytics] = useState(false);

  const certified      = MOCK_PROJECTS.filter((p) => p.tier === "IRC-A" || p.tier === "IRC-B");
  const certifiedA     = MOCK_PROJECTS.filter((p) => p.tier === "IRC-A");
  const inProgress     = MOCK_PROJECTS.filter((p) => p.tier === "IRC-C");
  const notStarted     = MOCK_PROJECTS.filter((p) => p.tier === "Uncertified");
  const certRate       = Math.round((certified.length / MOCK_PROJECTS.length) * 100);

  const filtered = MOCK_PROJECTS
    .filter((p) => filterTier === "All" || p.tier === filterTier)
    .sort((a, b) => {
      if (sortBy === "readiness") return b.readiness - a.readiness;
      if (sortBy === "name") return a.name.localeCompare(b.name);
      const tierOrder: Record<CertTier, number> = { "IRC-A": 0, "IRC-B": 1, "IRC-C": 2, "Uncertified": 3 };
      return tierOrder[a.tier] - tierOrder[b.tier];
    });

  const ringColor = certRate > 60 ? "#15803d" : certRate >= 30 ? "#d97706" : "#dc2626";

  return (
    <div className="space-y-6 p-6 max-w-screen-2xl mx-auto">

      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <ShieldCheck className="h-6 w-6 text-primary-600" />
          <h1 className="text-2xl font-bold text-neutral-900">Investment Readiness Certification</h1>
          <span className="inline-flex items-center gap-1 text-xs font-semibold bg-primary-50 text-primary-700 border border-primary-200 rounded-full px-2.5 py-0.5">
            IRC Platform
          </span>
        </div>
        <p className="text-sm text-neutral-500">
          Institutional-grade certification for investment-ready projects — verified by platform intelligence, validated by third-party audit
        </p>
      </div>

      <InfoBanner
        icon={<Award className="h-4 w-4" />}
        message="The Investment Readiness Certification (IRC) is the platform's highest assurance level, confirming that a project meets all criteria for institutional investment. Certification requires passing six verification pillars: Signal Score, Risk Management, Documentation, Legal & Compliance, ESG Alignment, and Financial Robustness. Certified projects carry an auditable, timestamped credential that can be independently verified by investors, auditors, and regulatory bodies."
      />

      {/* ── Hero Section ── */}
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6 text-white shadow-xl">
        <div className="flex items-center gap-2 mb-5">
          <ShieldCheck className="h-5 w-5 text-secondary-400" />
          <h2 className="text-base font-semibold">Certification Portfolio Overview</h2>
        </div>

        <div className="flex flex-col lg:flex-row gap-6">
          {/* Large box — circular progress */}
          <div className="flex flex-col items-center justify-center bg-white/10 rounded-xl p-6 min-w-[200px]">
            <div className="relative flex items-center justify-center mb-3">
              <svg width="120" height="120" className="-rotate-90">
                <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="10" />
                <circle
                  cx="60" cy="60" r="50"
                  fill="none"
                  stroke={ringColor}
                  strokeWidth="10"
                  strokeDasharray={`${2 * Math.PI * 50}`}
                  strokeDashoffset={`${2 * Math.PI * 50 * (1 - certRate / 100)}`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute text-center">
                <p className="text-3xl font-bold text-white">{certRate}%</p>
              </div>
            </div>
            <p className="text-xs text-white/60 font-medium uppercase tracking-wide">Portfolio Certification Rate</p>
          </div>

          {/* 2×2 grid */}
          <div className="grid grid-cols-2 gap-3 flex-1">
            <div className="bg-white/10 rounded-xl p-4">
              <p className="text-xs text-white/50 mb-1">Total Projects</p>
              <p className="text-3xl font-bold text-white">{MOCK_PROJECTS.length}</p>
            </div>
            <div className="bg-white/10 rounded-xl p-4">
              <p className="text-xs text-white/50 mb-1">Certified (A + B)</p>
              <p className="text-3xl font-bold text-green-400">{certified.length}</p>
              <p className="text-[10px] text-green-300/70">{certifiedA.length} IRC-A · {certified.length - certifiedA.length} IRC-B</p>
            </div>
            <div className="bg-white/10 rounded-xl p-4">
              <p className="text-xs text-white/50 mb-1">In Progress (IRC-C)</p>
              <p className="text-3xl font-bold text-blue-400">{inProgress.length}</p>
            </div>
            <div className="bg-white/10 rounded-xl p-4">
              <p className="text-xs text-white/50 mb-1">Not Started</p>
              <p className="text-3xl font-bold text-neutral-400">{notStarted.length}</p>
            </div>
          </div>

          {/* Quick actions */}
          <div className="flex flex-col gap-2 justify-center min-w-[180px]">
            <Button variant="outline" size="sm" className="bg-white/10 border-white/20 text-white hover:bg-white/20 gap-1.5 justify-start">
              <RefreshCw className="h-3.5 w-3.5" /> Run Assessment
            </Button>
            <Button variant="outline" size="sm" className="bg-white/10 border-white/20 text-white hover:bg-white/20 gap-1.5 justify-start">
              <Sparkles className="h-3.5 w-3.5 text-violet-300" /> Generate Roadmap
            </Button>
            <Button variant="outline" size="sm" className="bg-white/10 border-white/20 text-white hover:bg-white/20 gap-1.5 justify-start">
              <Download className="h-3.5 w-3.5" /> Export Report
            </Button>
            <Button variant="outline" size="sm" className="bg-white/10 border-white/20 text-white hover:bg-white/20 gap-1.5 justify-start">
              <GitCompare className="h-3.5 w-3.5" /> Compare Peers
            </Button>
          </div>
        </div>
      </div>

      {/* ── Tier Definitions ── */}
      <div>
        <h2 className="text-base font-semibold text-neutral-800 mb-3">Certification Tiers</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(["IRC-A", "IRC-B", "IRC-C"] as const).map((tier) => {
            const cfg = TIER_CONFIG[tier];
            const count = MOCK_PROJECTS.filter((p) => p.tier === tier).length;
            return (
              <div key={tier} className={`rounded-xl border-2 ${cfg.border} ${cfg.bg} p-4`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`h-10 w-10 rounded-xl ${cfg.badgeBg} flex items-center justify-center shadow`}>
                      <ShieldCheck className="h-5 w-5 text-white" />
                    </div>
                    <div>
                      <p className={`text-base font-bold ${cfg.textColor}`}>{tier}</p>
                      <p className="text-xs text-neutral-500">{cfg.description}</p>
                    </div>
                  </div>
                  <span className={`text-2xl font-bold ${cfg.textColor}`}>{count}</span>
                </div>
                <p className="text-[11px] text-neutral-600 leading-relaxed">
                  {tier === "IRC-A" && "All six pillars ≥80. Full documentation verified. Third-party audit completed and signed. Valid for 12 months."}
                  {tier === "IRC-B" && "At least four pillars ≥80, remaining ≥60. Core documentation complete, minor gaps identified. Valid for 6 months."}
                  {tier === "IRC-C" && "At least three pillars ≥60. Active improvement plan in place. Documentation in progress."}
                </p>
                <p className={`text-[10px] font-semibold mt-2 ${cfg.textColor}`}>{cfg.validity}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Project Certification Table ── */}
      <div>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-3">
          <h2 className="text-base font-semibold text-neutral-800">Project Certification Status</h2>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-neutral-500">Filter:</span>
            {(["All", "IRC-A", "IRC-B", "IRC-C", "Uncertified"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setFilterTier(t)}
                className={`text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${
                  filterTier === t
                    ? "bg-primary-600 text-white"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                }`}
              >
                {t}
              </button>
            ))}
            <span className="text-xs text-neutral-500 ml-2">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="text-xs border border-neutral-200 rounded-md px-2 py-1 bg-white text-neutral-700"
            >
              <option value="readiness">Readiness</option>
              <option value="tier">Tier</option>
              <option value="name">Name</option>
            </select>
          </div>
        </div>

        <div className="rounded-xl border border-neutral-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-neutral-100 bg-neutral-50">
                  <th className="text-left px-4 py-3 font-semibold text-neutral-600">Project</th>
                  <th className="text-left px-3 py-3 font-semibold text-neutral-600">Tier</th>
                  <th className="text-left px-3 py-3 font-semibold text-neutral-600">Readiness</th>
                  <th className="text-center px-2 py-3 font-semibold text-neutral-600">Signal</th>
                  <th className="text-center px-2 py-3 font-semibold text-neutral-600">Risk</th>
                  <th className="text-center px-2 py-3 font-semibold text-neutral-600">Docs</th>
                  <th className="text-center px-2 py-3 font-semibold text-neutral-600">Legal</th>
                  <th className="text-center px-2 py-3 font-semibold text-neutral-600">ESG</th>
                  <th className="text-center px-2 py-3 font-semibold text-neutral-600">Financial</th>
                  <th className="text-left px-3 py-3 font-semibold text-neutral-600">Certified</th>
                  <th className="text-left px-3 py-3 font-semibold text-neutral-600">Expires</th>
                  <th className="px-3 py-3" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((project) => (
                  <tr key={project.id} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-neutral-900 whitespace-nowrap">{project.name}</p>
                      <p className="text-neutral-500">{project.sector} · {project.geography}</p>
                    </td>
                    <td className="px-3 py-3">
                      <TierBadge tier={project.tier} size="sm" />
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 bg-neutral-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${project.readiness >= 80 ? "bg-green-500" : project.readiness >= 60 ? "bg-amber-400" : "bg-red-400"}`}
                            style={{ width: `${project.readiness}%` }}
                          />
                        </div>
                        <span className="font-semibold text-neutral-700">{project.readiness}%</span>
                      </div>
                    </td>
                    {(["signal", "risk", "docs", "legal", "esg", "financial"] as const).map((pk) => (
                      <td key={pk} className="px-2 py-3 text-center">
                        <PillarCell pillar={project.pillars[pk]} />
                      </td>
                    ))}
                    <td className="px-3 py-3 text-neutral-600 whitespace-nowrap">{project.certifiedDate ?? "—"}</td>
                    <td className="px-3 py-3 text-neutral-600 whitespace-nowrap">{project.expiryDate ?? "—"}</td>
                    <td className="px-3 py-3">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-[11px] h-7 gap-1 whitespace-nowrap"
                        onClick={() => setSelectedProject(project)}
                      >
                        {project.tier === "Uncertified" ? "Start Certification" : "View Details"}
                        <ChevronRight className="h-3 w-3" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Six Pillars Reference ── */}
      <div>
        <h2 className="text-base font-semibold text-neutral-800 mb-3">The Six Certification Pillars</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {PILLARS.map((pillar) => (
            <div key={pillar.key} className="rounded-xl border border-neutral-200 bg-white p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-center gap-3 mb-3">
                <div className="h-9 w-9 rounded-lg bg-neutral-50 border border-neutral-100 flex items-center justify-center">
                  <pillar.icon className={`h-4.5 w-4.5 ${pillar.iconColor}`} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-neutral-800">{pillar.label}</p>
                  <p className="text-[10px] text-neutral-500">Source: {pillar.source}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <div className="flex-1 rounded-lg bg-green-50 border border-green-100 p-2 text-center">
                  <p className="text-[9px] font-semibold text-green-600 uppercase tracking-wide mb-0.5">IRC-A</p>
                  <p className="text-xs font-bold text-green-700">{pillar.thresholdA}</p>
                </div>
                <div className="flex-1 rounded-lg bg-blue-50 border border-blue-100 p-2 text-center">
                  <p className="text-[9px] font-semibold text-blue-600 uppercase tracking-wide mb-0.5">IRC-B</p>
                  <p className="text-xs font-bold text-blue-700">{pillar.thresholdB}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Third-Party Validation ── */}
      <div className="rounded-xl border border-neutral-200 bg-white p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-neutral-800">Certification Co-Validation</h2>
            <p className="text-xs text-neutral-500 mt-0.5">
              IRC certifications can be co-validated by approved third-party firms to provide independent assurance
            </p>
          </div>
          <Button variant="outline" size="sm" className="gap-1.5 shrink-0">
            <Building2 className="h-3.5 w-3.5" /> Request Validation
          </Button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { category: "Audit Firms", description: "Big 4 and regional audit firms", example: "PwC, Deloitte, EY, KPMG", color: "text-violet-700", bg: "bg-violet-50", border: "border-violet-200" },
            { category: "Law Firms", description: "International project finance specialists", example: "Linklaters, A&O, Clifford Chance", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200" },
            { category: "Financial Advisors", description: "Transaction advisory specialists", example: "Rothschild, Lazard, Greenhill", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
            { category: "Technical Advisors", description: "Independent engineers & consultants", example: "WSP, AECOM, Atkins", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
          ].map((partner) => (
            <div key={partner.category} className={`rounded-lg border ${partner.border} ${partner.bg} p-3`}>
              <p className={`text-xs font-semibold ${partner.color} mb-1`}>{partner.category}</p>
              <p className="text-[11px] text-neutral-600 mb-1">{partner.description}</p>
              <p className="text-[10px] text-neutral-400 italic">{partner.example}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg bg-neutral-50 border border-neutral-200 p-3 flex items-center gap-3">
          <QrCode className="h-8 w-8 text-neutral-400 shrink-0" />
          <div>
            <p className="text-xs font-semibold text-neutral-700">Verification Portal</p>
            <p className="text-[11px] text-neutral-500">
              Each certification has a unique verification URL. External parties can verify status at{" "}
              <span className="font-medium text-blue-600">verify.scrplatform.com/[CertificationID]</span> — no login required.
            </p>
          </div>
        </div>
      </div>

      {/* ── Analytics ── */}
      <div>
        <button
          onClick={() => setShowAnalytics((s) => !s)}
          className="flex items-center gap-2 text-sm font-semibold text-neutral-700 hover:text-neutral-900 mb-3"
        >
          <BarChart3 className="h-4 w-4 text-primary-600" />
          Certification Analytics
          <ChevronDown className={`h-4 w-4 transition-transform ${showAnalytics ? "rotate-180" : ""}`} />
        </button>
        {showAnalytics && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-4">
                <h3 className="text-sm font-semibold text-neutral-700 mb-3">Certification Rate Trend</h3>
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart data={CERT_RATE_TREND}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} domain={[0, 60]} />
                    <Tooltip formatter={(v) => [`${v}%`, "Cert Rate"]} />
                    <Line type="monotone" dataKey="rate" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <h3 className="text-sm font-semibold text-neutral-700 mb-3">Average Pillar Score Distribution</h3>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={PILLAR_AVG} barSize={30}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="avg" radius={[4, 4, 0, 0]}>
                      {PILLAR_AVG.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={entry.avg >= 80 ? "#22c55e" : entry.avg >= 60 ? "#f59e0b" : "#ef4444"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardContent className="p-4">
                <h3 className="text-sm font-semibold text-neutral-700 mb-3">Upcoming Certification Renewals</h3>
                <div className="space-y-2">
                  {MOCK_PROJECTS.filter((p) => p.expiryDate).map((p) => (
                    <div key={p.id} className="flex items-center justify-between py-2 border-b border-neutral-50 last:border-0">
                      <div className="flex items-center gap-3">
                        <TierBadge tier={p.tier} size="sm" />
                        <span className="text-sm font-medium text-neutral-800">{p.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-neutral-500">Expires {p.expiryDate}</span>
                        <Button size="sm" variant="outline" className="text-[11px] h-7">Renew</Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Project Detail Modal */}
      {selectedProject && (
        <ProjectDetailModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
        />
      )}
    </div>
  );
}
