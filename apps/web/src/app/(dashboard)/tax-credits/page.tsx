"use client";

import { useState } from "react";
import {
  Award,
  CheckCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  Plus,
  Receipt,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Upload,
  Zap,
  AlertCircle,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  cn,
} from "@scr/ui";
import {
  useIdentifyCredits,
  formatCreditValue,
  type IdentificationResponse,
} from "@/lib/tax-credits";
import { useProjects } from "@/lib/projects";
import { InfoBanner } from "@/components/info-banner";

// ── Mock application data ──────────────────────────────────────────────────────

type AppStatus = "draft" | "submitted" | "under_review" | "certified" | "rejected";

const MOCK_APPLICATIONS = [
  {
    id: "app-001",
    project: "Solvatten Solar 80MW",
    credit: "ITC §48 — Investment Tax Credit",
    program: "US Federal",
    status: "certified" as AppStatus,
    value: 4_200_000,
    submitted: "Jan 15, 2025",
    certified: "Feb 28, 2025",
    score_impact: "+4.2 pts",
    docs_required: 4,
    docs_submitted: 4,
  },
  {
    id: "app-002",
    project: "BioCircle W2E",
    credit: "§45Q — Carbon Oxide Sequestration Credit",
    program: "US Federal",
    status: "under_review" as AppStatus,
    value: 890_000,
    submitted: "Feb 8, 2025",
    certified: null,
    score_impact: "+2.1 pts",
    docs_required: 5,
    docs_submitted: 5,
  },
  {
    id: "app-003",
    project: "Coastal Biogas",
    credit: "USDA REAP — Rural Energy for America",
    program: "US Federal",
    status: "submitted" as AppStatus,
    value: 500_000,
    submitted: "Mar 2, 2025",
    certified: null,
    score_impact: "+1.8 pts",
    docs_required: 3,
    docs_submitted: 3,
  },
  {
    id: "app-004",
    project: "Väst Wind 120MW",
    credit: "PTC §45 — Production Tax Credit",
    program: "US Federal",
    status: "draft" as AppStatus,
    value: 3_100_000,
    submitted: null,
    certified: null,
    score_impact: "+5.1 pts",
    docs_required: 5,
    docs_submitted: 2,
  },
  {
    id: "app-005",
    project: "Nordic Hydro Rehab",
    credit: "ITC §48 — Investment Tax Credit",
    program: "US Federal",
    status: "draft" as AppStatus,
    value: 1_150_000,
    submitted: null,
    certified: null,
    score_impact: "+2.8 pts",
    docs_required: 4,
    docs_submitted: 1,
  },
];

const CREDIT_PROGRAMS = [
  {
    id: "itc-48",
    name: "ITC §48 — Investment Tax Credit",
    category: "Solar / Renewables",
    jurisdiction: "US Federal",
    rate: "30% of qualified investment",
    max_value: null,
    eligible_types: ["Solar PV", "Wind", "Geothermal", "Fuel Cell", "Small Wind"],
    description:
      "30% credit on the cost of qualified clean energy property placed in service. Bonus credits available for domestic content (+10%) and energy communities (+10%).",
    eligibility: ["Project must be placed in service in the US", "Equipment meets IRS §48 definition", "Construction begins before 2033"],
    time_to_certify: "4–6 weeks",
    signal_score_boost: "Up to +5 pts",
  },
  {
    id: "ptc-45",
    name: "PTC §45 — Production Tax Credit",
    category: "Wind / Hydro",
    jurisdiction: "US Federal",
    rate: "2.75¢ / kWh (10 years)",
    max_value: null,
    eligible_types: ["Wind", "Hydro", "Geothermal", "Biomass"],
    description:
      "Per-kWh credit on electricity produced from qualified renewable sources over a 10-year period. Mutually exclusive with ITC on the same project.",
    eligibility: ["Commercial operation date documented", "Electricity sold to third parties", "Facility in the US or US territories"],
    time_to_certify: "6–8 weeks",
    signal_score_boost: "Up to +5 pts",
  },
  {
    id: "45q",
    name: "§45Q — Carbon Oxide Sequestration",
    category: "Carbon Capture",
    jurisdiction: "US Federal",
    rate: "$85 / tonne CO₂ sequestered",
    max_value: null,
    eligible_types: ["Biogas", "Waste-to-Energy", "Industrial CCS"],
    description:
      "Tax credit for capturing and sequestering CO₂. Inflation Reduction Act increased rates and broadened eligibility to include direct air capture.",
    eligibility: ["Minimum 12,500 tonne CO₂ capture threshold", "Qualified carbon capture equipment", "Geological sequestration or industrial utilisation"],
    time_to_certify: "8–10 weeks",
    signal_score_boost: "Up to +3 pts",
  },
  {
    id: "reap",
    name: "USDA REAP — Rural Energy for America",
    category: "Rural Renewables",
    jurisdiction: "US Federal (USDA)",
    rate: "Up to 50% of eligible costs",
    max_value: 1_000_000,
    eligible_types: ["Solar PV", "Wind", "Biogas", "Small Hydro"],
    description:
      "Grants and guaranteed loans for agricultural producers and rural small businesses. Combines well with ITC to maximise overall incentive stack.",
    eligibility: ["Located in rural area (population < 50,000)", "Agricultural producer or small business", "Project is technically viable"],
    time_to_certify: "3–4 weeks",
    signal_score_boost: "Up to +2 pts",
  },
  {
    id: "nmtc",
    name: "NMTC — New Markets Tax Credit",
    category: "Community Development",
    jurisdiction: "US Federal (CDFI)",
    rate: "39% credit over 7 years",
    max_value: null,
    eligible_types: ["Infrastructure", "Mixed-use", "Community Energy"],
    description:
      "Credits for investments in low-income community businesses. Structured through a Community Development Entity (CDE). Complex but high-value.",
    eligibility: ["Project located in low-income census tract", "Investment made through qualified CDE", "Substantial nexus to low-income community"],
    time_to_certify: "10–12 weeks",
    signal_score_boost: "Up to +3 pts",
  },
];

// ── Status helpers ─────────────────────────────────────────────────────────────

function statusConfig(status: AppStatus) {
  switch (status) {
    case "certified":
      return { label: "Certified", variant: "success" as const, icon: ShieldCheck, color: "text-green-600" };
    case "under_review":
      return { label: "Under Review", variant: "info" as const, icon: Clock, color: "text-blue-600" };
    case "submitted":
      return { label: "Submitted", variant: "warning" as const, icon: Upload, color: "text-amber-600" };
    case "draft":
      return { label: "Draft", variant: "neutral" as const, icon: FileText, color: "text-neutral-500" };
    case "rejected":
      return { label: "Rejected", variant: "error" as const, icon: AlertCircle, color: "text-red-600" };
  }
}

function fmtValue(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

// ── Overview tab ───────────────────────────────────────────────────────────────

function OverviewTab({ onStartApplication }: { onStartApplication: () => void }) {
  const certified = MOCK_APPLICATIONS.filter((a) => a.status === "certified");
  const inFlight = MOCK_APPLICATIONS.filter((a) => ["submitted", "under_review"].includes(a.status));
  const drafts = MOCK_APPLICATIONS.filter((a) => a.status === "draft");

  const totalCertified = certified.reduce((s, a) => s + a.value, 0);
  const totalPending = inFlight.reduce((s, a) => s + a.value, 0);
  const totalDraft = drafts.reduce((s, a) => s + a.value, 0);

  const STATUS_PIPELINE = [
    { label: "Draft", count: drafts.length, color: "bg-neutral-300", textColor: "text-neutral-600" },
    { label: "Submitted", count: MOCK_APPLICATIONS.filter((a) => a.status === "submitted").length, color: "bg-amber-400", textColor: "text-amber-700" },
    { label: "Under Review", count: MOCK_APPLICATIONS.filter((a) => a.status === "under_review").length, color: "bg-blue-500", textColor: "text-blue-700" },
    { label: "Certified", count: certified.length, color: "bg-green-500", textColor: "text-green-700" },
  ];

  return (
    <div className="space-y-6">
      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-neutral-500 font-medium">Certified Value</p>
            <p className="text-2xl font-bold text-neutral-900 mt-1">{fmtValue(totalCertified)}</p>
            <p className="text-xs text-neutral-400 mt-0.5">{certified.length} credit{certified.length !== 1 ? "s" : ""} certified</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-neutral-500 font-medium">Pending Review</p>
            <p className="text-2xl font-bold text-neutral-900 mt-1">{fmtValue(totalPending)}</p>
            <p className="text-xs text-neutral-400 mt-0.5">{inFlight.length} application{inFlight.length !== 1 ? "s" : ""} in progress</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-neutral-500 font-medium">Draft Potential</p>
            <p className="text-2xl font-bold text-neutral-700 mt-1">{fmtValue(totalDraft)}</p>
            <p className="text-xs text-neutral-400 mt-0.5">{drafts.length} draft{drafts.length !== 1 ? "s" : ""} not submitted</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs text-neutral-500 font-medium">Signal Score Impact</p>
            <p className="text-2xl font-bold text-neutral-900 mt-1">+13.2 pts</p>
            <p className="text-xs text-neutral-400 mt-0.5">from all certified credits</p>
          </CardContent>
        </Card>
      </div>

      {/* Application pipeline */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">Application Pipeline</CardTitle>
            <Button size="sm" onClick={onStartApplication}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              New Application
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-3 mb-6">
            {STATUS_PIPELINE.map((s) => (
              <div key={s.label} className="text-center">
                <div className={cn("h-2 rounded-full mb-2", s.color)} />
                <p className={cn("text-xs font-semibold", s.textColor)}>{s.label}</p>
                <p className="text-2xl font-bold text-neutral-900 mt-1">{s.count}</p>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {MOCK_APPLICATIONS.map((app) => {
              const sc = statusConfig(app.status);
              const Icon = sc.icon;
              return (
                <div
                  key={app.id}
                  className="flex items-center gap-3 rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3"
                >
                  <Icon className={cn("h-4 w-4 shrink-0", sc.color)} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-neutral-900 truncate">{app.credit}</p>
                    <p className="text-xs text-neutral-500">{app.project}</p>
                  </div>
                  <span className="text-xs font-semibold text-neutral-700 shrink-0">{fmtValue(app.value)}</span>
                  <span className="text-xs text-purple-600 font-medium shrink-0">{app.score_impact}</span>
                  <Badge variant={sc.variant} className="text-xs shrink-0">{sc.label}</Badge>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Signal Score Impact callout */}
      <Card className="border-purple-200 bg-purple-50">
        <CardContent className="pt-5">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-purple-100 rounded-lg shrink-0">
              <Sparkles className="h-5 w-5 text-purple-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-purple-900 mb-1">
                How tax credit certification improves your Signal Score
              </h3>
              <p className="text-sm text-purple-800 mb-4">
                Platform-certified credits demonstrate financial engineering capability and unlock the
                <strong> ESG</strong> and <strong>Financial Planning</strong> dimensions of your Signal Score.
                Investors actively filter for certified projects — certification typically increases investor
                match rates by 20–35%.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { label: "ESG Score dimension", impact: "+3–5 pts", icon: ShieldCheck },
                  { label: "Financial Planning dimension", impact: "+2–4 pts", icon: TrendingUp },
                  { label: "Investor match rate increase", impact: "20–35%", icon: Zap },
                ].map(({ label, impact, icon: Icon }) => (
                  <div key={label} className="rounded-lg bg-white border border-purple-200 px-3 py-2.5 flex items-center gap-2">
                    <Icon className="h-4 w-4 text-purple-500 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs text-purple-700 font-medium">{label}</p>
                      <p className="text-sm font-bold text-purple-900">{impact}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Discover tab ───────────────────────────────────────────────────────────────

function DiscoverTab({ onApply }: { onApply: (programId: string) => void }) {
  const identify = useIdentifyCredits();
  const [projectId, setProjectId] = useState("");
  const [result, setResult] = useState<IdentificationResponse | null>(null);
  const { data: projectList } = useProjects({ page_size: 100 });
  const [search, setSearch] = useState("");

  async function handleScan() {
    if (!projectId.trim()) return;
    const res = await identify.mutateAsync(projectId.trim());
    setResult(res);
  }

  const filtered = CREDIT_PROGRAMS.filter(
    (p) =>
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.category.toLowerCase().includes(search.toLowerCase()) ||
      p.eligible_types.some((t) => t.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Scan for my project */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="h-4 w-4 text-blue-500" />
            Scan My Project for Eligible Credits
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-600 mb-4">
            Select a project to automatically identify which tax credit programs it qualifies for,
            based on project type, geography, and development stage.
          </p>
          <div className="flex items-center gap-3">
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="rounded-md border border-neutral-300 px-3 py-2 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a project…</option>
              {(projectList?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <Button onClick={handleScan} disabled={!projectId.trim() || identify.isPending}>
              {identify.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Search className="h-4 w-4 mr-2" />
              )}
              Scan for Credits
            </Button>
          </div>

          {result && (
            <div className="mt-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-neutral-900">{result.project_name}</p>
                  <p className="text-sm text-neutral-500">
                    {result.identified.length} eligible program
                    {result.identified.length !== 1 ? "s" : ""} found ·{" "}
                    <span className="text-blue-700 font-medium">
                      {formatCreditValue(result.total_estimated_value, result.currency)} potential value
                    </span>
                  </p>
                </div>
              </div>
              {result.identified.map((credit, i) => (
                <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-semibold text-sm text-neutral-900">{credit.credit_type}</span>
                        <Badge variant={credit.qualification === "qualified" ? "success" : "warning"}>
                          {credit.qualification === "qualified" ? "Eligible" : "Partially Eligible"}
                        </Badge>
                      </div>
                      <p className="text-xs text-neutral-500">{credit.program_name}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-sm font-bold text-neutral-900">
                        {formatCreditValue(credit.estimated_value, result.currency)}
                      </p>
                      <p className="text-xs text-neutral-400">estimated value</p>
                    </div>
                  </div>
                  {credit.criteria_met.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-green-700 mb-1">Requirements met</p>
                      <ul className="space-y-0.5">
                        {credit.criteria_met.map((c, j) => (
                          <li key={j} className="flex items-center gap-1.5 text-xs text-neutral-600">
                            <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {credit.criteria_missing.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-medium text-amber-700 mb-1">Outstanding requirements</p>
                      <ul className="space-y-0.5">
                        {credit.criteria_missing.map((c, j) => (
                          <li key={j} className="flex items-center gap-1.5 text-xs text-neutral-500">
                            <AlertCircle className="h-3 w-3 text-amber-500 shrink-0" />
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <Button size="sm" onClick={() => onApply(credit.credit_type)} className="mt-1">
                    Start Application <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Program catalogue */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-neutral-900">Available Credit Programs</h3>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search programs…"
              className="pl-8 pr-3 py-1.5 rounded-md border border-neutral-200 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filtered.map((prog) => (
            <Card key={prog.id} className="hover:border-blue-200 transition-colors">
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-sm text-neutral-900 leading-tight">{prog.name}</p>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <Badge variant="info" className="text-[10px]">{prog.category}</Badge>
                      <Badge variant="neutral" className="text-[10px]">{prog.jurisdiction}</Badge>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs font-semibold text-blue-700">{prog.rate}</p>
                    <p className="text-[10px] text-purple-600 mt-0.5">{prog.signal_score_boost}</p>
                  </div>
                </div>
                <p className="text-xs text-neutral-600 mb-3 leading-relaxed">{prog.description}</p>
                <div className="mb-3">
                  <p className="text-xs font-medium text-neutral-500 mb-1">Eligible project types</p>
                  <div className="flex flex-wrap gap-1">
                    {prog.eligible_types.map((t) => (
                      <span key={t} className="text-[10px] bg-neutral-100 text-neutral-600 rounded-full px-2 py-0.5">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-[10px] text-neutral-400 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Cert. timeline: {prog.time_to_certify}
                  </p>
                  <Button size="sm" variant="outline" onClick={() => onApply(prog.id)}>
                    Apply <ChevronRight className="h-3.5 w-3.5 ml-1" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Applications tab ───────────────────────────────────────────────────────────

function ApplicationsTab() {
  const certifiedTotal = MOCK_APPLICATIONS.filter((a) => a.status === "certified").reduce((s, a) => s + a.value, 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Certified", value: fmtValue(certifiedTotal), color: "text-green-700", count: MOCK_APPLICATIONS.filter((a) => a.status === "certified").length },
          { label: "Under Review", value: `${MOCK_APPLICATIONS.filter((a) => a.status === "under_review").length} apps`, color: "text-blue-700", count: null },
          { label: "Submitted", value: `${MOCK_APPLICATIONS.filter((a) => a.status === "submitted").length} apps`, color: "text-amber-700", count: null },
          { label: "Draft", value: `${MOCK_APPLICATIONS.filter((a) => a.status === "draft").length} apps`, color: "text-neutral-600", count: null },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-neutral-500 mb-1">{label}</p>
              <p className={cn("text-xl font-bold", color)}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">My Applications</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-100 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Project</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Credit Program</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-neutral-500">Est. Value</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-neutral-500">Documents</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Submitted</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-neutral-500">Score Impact</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_APPLICATIONS.map((app) => {
                const sc = statusConfig(app.status);
                return (
                  <tr key={app.id} className="border-b border-neutral-50 hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-neutral-900">{app.project}</td>
                    <td className="px-4 py-3 text-xs text-neutral-600 max-w-[200px]">
                      <p className="truncate">{app.credit}</p>
                      <p className="text-neutral-400">{app.program}</p>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-neutral-800">
                      {fmtValue(app.value)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={cn(
                          "text-xs font-semibold",
                          app.docs_submitted === app.docs_required ? "text-green-600" : "text-amber-600"
                        )}
                      >
                        {app.docs_submitted}/{app.docs_required}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-500">
                      {app.submitted ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-xs font-semibold text-purple-700">{app.score_impact}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={sc.variant} className="text-xs">{sc.label}</Badge>
                    </td>
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

// ── Certification tab ──────────────────────────────────────────────────────────

function CertificationTab() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [form, setForm] = useState({
    project: "",
    credit_program: "",
    placement_date: "",
    total_investment: "",
    technology_type: "",
    jurisdiction: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const { data: projectList } = useProjects({ page_size: 100 });

  async function handleSubmit() {
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 1800));
    setSubmitting(false);
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="max-w-lg space-y-6">
        <div className="rounded-xl bg-green-50 border border-green-200 p-6 text-center">
          <div className="flex justify-center mb-3">
            <div className="p-3 bg-green-100 rounded-full">
              <CheckCircle2 className="h-8 w-8 text-green-600" />
            </div>
          </div>
          <h3 className="text-lg font-bold text-green-900 mb-1">Certification Application Submitted</h3>
          <p className="text-sm text-green-700 mb-4">
            Your application is now under platform review. You will be notified when certification
            is complete — typically within 4–8 weeks depending on the credit program.
          </p>
          <div className="rounded-lg bg-white border border-green-200 p-3 text-left mb-4">
            <p className="text-xs font-semibold text-neutral-500 mb-2">What happens next</p>
            {[
              "Platform team reviews your submitted documentation",
              "Any clarifications are requested via the platform",
              "Certification badge added to your project profile",
              "Signal Score automatically updated — investors notified",
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-2 mb-1.5 last:mb-0">
                <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-green-100 text-[10px] font-bold text-green-700">
                  {i + 1}
                </span>
                <p className="text-xs text-neutral-700">{step}</p>
              </div>
            ))}
          </div>
          <Button
            variant="outline"
            onClick={() => {
              setSubmitted(false);
              setStep(1);
              setForm({ project: "", credit_program: "", placement_date: "", total_investment: "", technology_type: "", jurisdiction: "" });
            }}
          >
            Submit Another Application
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
        <p className="text-sm text-blue-800">
          <strong>Platform Certification</strong> validates that your project meets the requirements
          for a specific tax credit program. Certified projects receive a verified badge visible to
          all investors on the platform, directly boosting your Signal Score and investor
          match rate.
        </p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-0">
        {[
          { n: 1 as const, label: "Project Details" },
          { n: 2 as const, label: "Credit Program" },
          { n: 3 as const, label: "Documents & Submit" },
        ].map(({ n, label }, i) => (
          <div key={n} className="flex items-center">
            {i > 0 && <div className={cn("h-px w-8 sm:w-16", step > i ? "bg-blue-500" : "bg-neutral-200")} />}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                  step === n ? "bg-blue-600 text-white" : step > n ? "bg-green-500 text-white" : "bg-neutral-200 text-neutral-500"
                )}
              >
                {step > n ? <CheckCircle2 className="h-4 w-4" /> : n}
              </div>
              <p className="text-[10px] text-neutral-500 mt-1 whitespace-nowrap">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Step 1 — Project Details */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Step 1 — Select Project</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Project</label>
              <select
                value={form.project}
                onChange={(e) => setForm({ ...form, project: e.target.value })}
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a project…</option>
                {(projectList?.items ?? []).map((p) => (
                  <option key={p.id} value={p.name}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">Project Type</label>
                <select
                  value={form.technology_type}
                  onChange={(e) => setForm({ ...form, technology_type: e.target.value })}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select type…</option>
                  {["Solar PV", "Wind", "Hydro", "Biogas", "Waste-to-Energy", "Geothermal", "Battery Storage"].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Jurisdiction</label>
                <select
                  value={form.jurisdiction}
                  onChange={(e) => setForm({ ...form, jurisdiction: e.target.value })}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select jurisdiction…</option>
                  {["United States", "European Union", "United Kingdom", "Canada", "Australia"].map((j) => (
                    <option key={j} value={j}>{j}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">Expected COD / Placement Date</label>
                <input
                  type="date"
                  value={form.placement_date}
                  onChange={(e) => setForm({ ...form, placement_date: e.target.value })}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Total Project Investment (USD)</label>
                <input
                  type="number"
                  value={form.total_investment}
                  onChange={(e) => setForm({ ...form, total_investment: e.target.value })}
                  placeholder="e.g. 45000000"
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                onClick={() => setStep(2)}
                disabled={!form.project || !form.technology_type || !form.jurisdiction}
              >
                Next — Select Credit Program
                <ChevronRight className="h-4 w-4 ml-1.5" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2 — Credit Program */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Step 2 — Select Credit Program</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-neutral-600 mb-2">
              Select the credit program you wish to apply for. You can submit separate applications
              for multiple programs on the same project.
            </p>
            {CREDIT_PROGRAMS.map((prog) => (
              <div
                key={prog.id}
                onClick={() => setForm({ ...form, credit_program: prog.id })}
                className={cn(
                  "cursor-pointer rounded-lg border-2 p-4 transition-all",
                  form.credit_program === prog.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-neutral-200 hover:border-neutral-300"
                )}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "mt-0.5 h-4 w-4 shrink-0 rounded-full border-2 flex items-center justify-center",
                      form.credit_program === prog.id ? "border-blue-500" : "border-neutral-300"
                    )}
                  >
                    {form.credit_program === prog.id && (
                      <div className="h-2 w-2 rounded-full bg-blue-500" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-sm text-neutral-900">{prog.name}</p>
                    <p className="text-xs text-neutral-500 mt-0.5">{prog.rate} · {prog.time_to_certify} to certify</p>
                  </div>
                  <span className="text-xs font-semibold text-purple-700 shrink-0">{prog.signal_score_boost}</span>
                </div>
              </div>
            ))}
            <div className="flex justify-between pt-2">
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button onClick={() => setStep(3)} disabled={!form.credit_program}>
                Next — Documents & Submit
                <ChevronRight className="h-4 w-4 ml-1.5" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3 — Documents & Submit */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Step 3 — Supporting Documents & Submit</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <p className="text-sm text-neutral-600">
              Upload the required documents to support your certification application. All documents
              are reviewed by the platform team and kept confidential.
            </p>

            {[
              { label: "Project Technical Specification", required: true, hint: "Engineering report, capacity specs, technology description" },
              { label: "Financial Model (Base Case)", required: true, hint: "Excel or PDF with capital costs and revenue projections" },
              { label: "Development / Construction Timeline", required: true, hint: "Gantt chart or milestone schedule with COD date" },
              { label: "Site / Property Documentation", required: false, hint: "Land title, lease agreement, or grid connection permit" },
            ].map((doc) => (
              <div key={doc.label} className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 flex items-center gap-1.5">
                    {doc.label}
                    {doc.required && <span className="text-red-500 text-xs">*</span>}
                  </p>
                  <p className="text-xs text-neutral-400 mt-0.5">{doc.hint}</p>
                </div>
                <Button size="sm" variant="outline" className="shrink-0">
                  <Upload className="h-3.5 w-3.5 mr-1.5" />
                  Upload
                </Button>
              </div>
            ))}

            <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-3 text-xs text-neutral-500">
              Documents already uploaded to your <strong>Data Room</strong> can be linked directly
              without re-uploading — the platform team will request access automatically.
            </div>

            <div className="flex justify-between pt-1">
              <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
              <Button onClick={handleSubmit} disabled={submitting}>
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Award className="h-4 w-4 mr-2" />
                )}
                Submit for Certification
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TaxCreditsPage() {
  const [activeTab, setActiveTab] = useState("overview");

  function handleStartApplication() {
    setActiveTab("certify");
  }

  function handleApply(_programId: string) {
    setActiveTab("certify");
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 rounded-lg shrink-0">
          <Receipt className="h-6 w-6 text-primary-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Tax Credit Programs</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Discover available incentives for your projects, get platform-certified, and strengthen
            your investor profile
          </p>
        </div>
      </div>

      <InfoBanner>
        <strong>Tax Credit Certification</strong> lets you register your projects for applicable
        government incentive programs (ITC, PTC, REAP, §45Q and more), submit supporting
        documentation, and receive a verified platform badge. Certified credits are visible to all
        investors on SCR, directly improving your <strong>Signal Score</strong> and increasing
        investor match rates by 20–35%.
      </InfoBanner>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">
            <TrendingUp className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="discover">
            <Search className="h-4 w-4 mr-2" />
            Discover Credits
          </TabsTrigger>
          <TabsTrigger value="applications">
            <Receipt className="h-4 w-4 mr-2" />
            My Applications
          </TabsTrigger>
          <TabsTrigger value="certify">
            <Award className="h-4 w-4 mr-2" />
            Get Certified
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab onStartApplication={handleStartApplication} />
        </TabsContent>
        <TabsContent value="discover" className="mt-6">
          <DiscoverTab onApply={handleApply} />
        </TabsContent>
        <TabsContent value="applications" className="mt-6">
          <ApplicationsTab />
        </TabsContent>
        <TabsContent value="certify" className="mt-6">
          <CertificationTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
