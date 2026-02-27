"use client";

import { useState } from "react";
import {
  Leaf,
  TrendingUp,
  Users,
  Zap,
  Plus,
  CheckCircle2,
  AlertCircle,
  Info,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  DataTable,
  EmptyState,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
} from "@scr/ui";
import {
  usePortfolioImpact,
  useCarbonCredits,
  useCreateCarbonCredit,
  useUpdateCarbonCredit,
  additionalityBadge,
  additionalityColor,
  carbonStatusVariant,
  formatNumber,
  SDG_METADATA,
  CARBON_STATUS_LABELS,
  type CarbonCreditResponse,
  type CarbonVerificationStatus,
  type ProjectImpactResponse,
  type SDGGoal,
} from "@/lib/impact";
import { useProjects } from "@/lib/projects";

// ── Stat card ─────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  unit,
  color = "text-neutral-900",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 bg-neutral-50 rounded-lg text-neutral-500">
            {icon}
          </div>
          <p className="text-xs font-medium text-neutral-500">{label}</p>
        </div>
        <div className="flex items-baseline gap-1">
          <span className={`text-2xl font-bold ${color}`}>{value}</span>
          {unit && <span className="text-sm text-neutral-400">{unit}</span>}
        </div>
      </CardContent>
    </Card>
  );
}

// ── SDG badge ─────────────────────────────────────────────────────────────

function SDGBadge({ goal }: { goal: SDGGoal }) {
  const meta = SDG_METADATA[goal.number];
  return (
    <div
      className="flex flex-col items-center text-center gap-1 p-2 rounded-lg"
      style={{ backgroundColor: meta?.color + "15" }}
      title={`SDG ${goal.number}: ${goal.label}\nContribution: ${goal.contribution_level}`}
    >
      <div
        className="h-8 w-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
        style={{ backgroundColor: meta?.color }}
      >
        {goal.number}
      </div>
      <p className="text-xs text-neutral-600 leading-tight font-medium" style={{ fontSize: "10px" }}>
        {goal.label}
      </p>
      <span
        className="text-xs px-1 rounded capitalize"
        style={{ color: meta?.color, fontSize: "9px", fontWeight: 600 }}
      >
        {goal.contribution_level === "co-benefit" ? "co-benefit" : goal.contribution_level}
      </span>
    </div>
  );
}

// ── SDG coverage grid ─────────────────────────────────────────────────────

function SDGCoverageGrid({
  covered,
  goals,
}: {
  covered: number[];
  goals?: SDGGoal[];
}) {
  const coveredSet = new Set(covered);
  const goalMap = new Map(goals?.map((g) => [g.number, g]) ?? []);

  return (
    <div className="grid grid-cols-9 gap-1.5">
      {Array.from({ length: 17 }, (_, i) => i + 1).map((n) => {
        const meta = SDG_METADATA[n];
        const isCovered = coveredSet.has(n);
        const goal = goalMap.get(n);
        return (
          <div
            key={n}
            className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
              isCovered ? "text-white" : "bg-neutral-100 text-neutral-300"
            }`}
            style={isCovered ? { backgroundColor: meta?.color } : undefined}
            title={
              isCovered
                ? `SDG ${n}: ${meta?.label}${goal ? ` (${goal.contribution_level})` : ""}`
                : `SDG ${n}: ${meta?.label} — not covered`
            }
          >
            {n}
          </div>
        );
      })}
    </div>
  );
}

// ── Project impact row ────────────────────────────────────────────────────

function ProjectImpactRow({ project }: { project: ProjectImpactResponse }) {
  const kpiMap = Object.fromEntries(
    project.kpis.map((k) => [k.key, k.value])
  );
  const rating = project.additionality_score >= 70 ? "high" : project.additionality_score >= 45 ? "medium" : "low";

  return (
    <div className="border border-neutral-200 rounded-xl p-4 hover:border-neutral-300 transition-colors">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h3 className="font-semibold text-sm text-neutral-900">
            {project.project_name}
          </h3>
          <p className="text-xs text-neutral-500">
            {project.geography_country} · {project.project_type.replace("_", " ")}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="text-center">
            <p className="text-xs text-neutral-400 mb-1">Additionality</p>
            <Badge variant={additionalityBadge(rating)}>
              {project.additionality_score}/100
            </Badge>
          </div>
        </div>
      </div>

      {/* KPI chips */}
      <div className="flex flex-wrap gap-2 mb-3">
        {kpiMap.capacity_mw != null && (
          <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium">
            {kpiMap.capacity_mw} MW
          </span>
        )}
        {kpiMap.co2_reduction_tco2e != null && (
          <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full font-medium">
            {formatNumber(kpiMap.co2_reduction_tco2e as number)} tCO₂e
          </span>
        )}
        {kpiMap.jobs_created_direct != null && (
          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
            {formatNumber(kpiMap.jobs_created_direct as number)} jobs
          </span>
        )}
        {kpiMap.households_served != null && (
          <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full font-medium">
            {formatNumber(kpiMap.households_served as number)} HH
          </span>
        )}
      </div>

      {/* SDG goals */}
      {project.sdg_goals.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {project.sdg_goals.map((g) => (
            <SDGBadge key={g.number} goal={g} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Dashboard tab ─────────────────────────────────────────────────────────

function DashboardTab() {
  const { data, isLoading } = usePortfolioImpact();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Top stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          icon={<Zap className="h-4 w-4" />}
          label="Total Capacity"
          value={formatNumber(data.total_capacity_mw, 1)}
          unit="MW"
          color="text-amber-600"
        />
        <StatCard
          icon={<Leaf className="h-4 w-4" />}
          label="CO₂ Reduced"
          value={formatNumber(data.total_co2_reduction_tco2e)}
          unit="tCO₂e"
          color="text-green-600"
        />
        <StatCard
          icon={<Users className="h-4 w-4" />}
          label="Jobs Created"
          value={formatNumber(data.total_jobs_created)}
          color="text-blue-600"
        />
        <StatCard
          icon={<TrendingUp className="h-4 w-4" />}
          label="Households Served"
          value={formatNumber(data.total_households_served)}
          color="text-purple-600"
        />
        <StatCard
          icon={<Leaf className="h-4 w-4" />}
          label="Carbon Credits"
          value={formatNumber(data.total_carbon_credit_tons)}
          unit="tCO₂e"
          color="text-teal-600"
        />
        <StatCard
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="SDGs Covered"
          value={String(data.sdg_coverage.length)}
          unit="/ 17"
          color="text-neutral-800"
        />
      </div>

      {/* SDG coverage */}
      <Card>
        <CardContent className="p-5">
          <h2 className="font-semibold text-neutral-800 mb-4">
            SDG Portfolio Coverage
          </h2>
          <SDGCoverageGrid covered={data.sdg_coverage} />
          <p className="text-xs text-neutral-400 mt-3">
            {data.sdg_coverage.length} of 17 SDGs covered across {data.total_projects} project
            {data.total_projects !== 1 ? "s" : ""}
          </p>
        </CardContent>
      </Card>

      {/* Per-project list */}
      <div>
        <h2 className="font-semibold text-neutral-800 mb-4">
          Project Impact
        </h2>
        {data.projects.length === 0 ? (
          <EmptyState
            icon={<Leaf className="h-8 w-8" />}
            title="No projects yet"
            description="Create projects and add impact KPIs to track your portfolio impact."
          />
        ) : (
          <div className="space-y-3">
            {data.projects.map((p) => (
              <ProjectImpactRow key={p.project_id} project={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Carbon Credits tab ────────────────────────────────────────────────────

function AddCreditModal({
  projectOptions,
  onClose,
}: {
  projectOptions: { id: string; name: string }[];
  onClose: () => void;
}) {
  const create = useCreateCarbonCredit();
  const [form, setForm] = useState({
    project_id: projectOptions[0]?.id ?? "",
    registry: "",
    methodology: "",
    vintage_year: new Date().getFullYear(),
    quantity_tons: "",
    price_per_ton: "",
    currency: "USD",
    verification_status: "estimated" as CarbonVerificationStatus,
    verification_body: "",
    serial_number: "",
  });

  function update(key: string, val: string | number) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  function submit() {
    create.mutate(
      {
        project_id: form.project_id,
        registry: form.registry,
        methodology: form.methodology,
        vintage_year: Number(form.vintage_year),
        quantity_tons: Number(form.quantity_tons),
        price_per_ton: form.price_per_ton ? Number(form.price_per_ton) : undefined,
        currency: form.currency,
        verification_status: form.verification_status,
        verification_body: form.verification_body || undefined,
        serial_number: form.serial_number || undefined,
      },
      { onSuccess: () => onClose() }
    );
  }

  const fields: Array<{
    key: string;
    label: string;
    type?: string;
    options?: string[];
  }> = [
    { key: "registry",            label: "Registry",            type: "text" },
    { key: "methodology",         label: "Methodology",         type: "text" },
    { key: "vintage_year",        label: "Vintage Year",        type: "number" },
    { key: "quantity_tons",       label: "Quantity (tCO₂e)",    type: "number" },
    { key: "price_per_ton",       label: "Price / ton (opt.)",  type: "number" },
    { key: "serial_number",       label: "Serial Number (opt.)", type: "text" },
    { key: "verification_body",   label: "Verifier (opt.)",     type: "text" },
    {
      key: "verification_status",
      label: "Status",
      options: ["estimated", "submitted", "verified", "issued", "retired"],
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-neutral-100">
          <h2 className="text-lg font-bold text-neutral-900">Add Carbon Credit</h2>
        </div>
        <div className="p-6 space-y-4">
          {/* Project */}
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Project
            </label>
            <select
              className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              value={form.project_id}
              onChange={(e) => update("project_id", e.target.value)}
            >
              {projectOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {fields.map((f) => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-neutral-600 mb-1">
                {f.label}
              </label>
              {f.options ? (
                <select
                  className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={(form as Record<string, string | number>)[f.key] as string}
                  onChange={(e) => update(f.key, e.target.value)}
                >
                  {f.options.map((o) => (
                    <option key={o} value={o}>
                      {CARBON_STATUS_LABELS[o as CarbonVerificationStatus]}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.type ?? "text"}
                  className="w-full text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={(form as Record<string, string | number>)[f.key]}
                  onChange={(e) => update(f.key, e.target.value)}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-3 p-6 border-t border-neutral-100">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={submit}
            disabled={
              !form.project_id ||
              !form.registry ||
              !form.methodology ||
              !form.quantity_tons ||
              create.isPending
            }
          >
            {create.isPending ? "Adding…" : "Add Credit"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function CarbonCreditsTab() {
  const { data, isLoading } = useCarbonCredits();
  const updateCredit = useUpdateCarbonCredit();
  const { data: projectsData } = useProjects();
  const [showAdd, setShowAdd] = useState(false);

  const projectOptions = projectsData?.items.map((p) => ({
    id: p.id,
    name: p.name,
  })) ?? [];

  const columns: ColumnDef<CarbonCreditResponse>[] = [
    {
      accessorKey: "registry",
      header: "Registry / Serial",
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-sm">{row.original.registry}</p>
          <p className="text-xs text-neutral-400 font-mono">
            {row.original.serial_number ?? "—"}
          </p>
        </div>
      ),
    },
    {
      accessorKey: "methodology",
      header: "Methodology",
      cell: ({ row }) => (
        <span className="text-sm truncate max-w-[160px] block">
          {row.original.methodology}
        </span>
      ),
    },
    {
      accessorKey: "vintage_year",
      header: "Vintage",
    },
    {
      accessorKey: "quantity_tons",
      header: "Quantity (tCO₂e)",
      cell: ({ row }) => (
        <span className="font-semibold">
          {Number(row.original.quantity_tons).toLocaleString()}
        </span>
      ),
    },
    {
      accessorKey: "verification_status",
      header: "Status",
      cell: ({ row }) => (
        <select
          className="text-xs border border-neutral-200 rounded px-2 h-7 bg-white"
          value={row.original.verification_status}
          onChange={(e) =>
            updateCredit.mutate({
              creditId: row.original.id,
              verification_status: e.target.value as CarbonVerificationStatus,
            })
          }
        >
          {Object.entries(CARBON_STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      ),
    },
    {
      accessorKey: "price_per_ton",
      header: "Price/ton",
      cell: ({ row }) =>
        row.original.price_per_ton
          ? `$${Number(row.original.price_per_ton).toFixed(2)}`
          : "—",
    },
  ];

  return (
    <div>
      {/* Summary stats */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          {[
            { label: "Estimated", value: data.total_estimated, color: "text-amber-600" },
            { label: "Verified",  value: data.total_verified,  color: "text-green-600" },
            { label: "Issued",    value: data.total_issued,    color: "text-blue-600" },
            { label: "Retired",   value: data.total_retired,   color: "text-neutral-500" },
          ].map(({ label, value, color }) => (
            <Card key={label}>
              <CardContent className="p-4">
                <p className="text-xs text-neutral-500 mb-1">{label}</p>
                <p className={`text-xl font-bold ${color}`}>
                  {formatNumber(value)}{" "}
                  <span className="text-xs font-normal text-neutral-400">
                    tCO₂e
                  </span>
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mb-5">
        <h2 className="font-semibold text-neutral-800">Carbon Credits</h2>
        <Button size="sm" onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          Add Credit
        </Button>
      </div>

      {isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Leaf className="h-8 w-8" />}
          title="No carbon credits"
          description="Register carbon credits to track your climate impact pipeline."
        />
      ) : (
        <DataTable columns={columns} data={data.items} />
      )}

      {showAdd && (
        <AddCreditModal
          projectOptions={projectOptions}
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  );
}

// ── SDG Tracker tab ───────────────────────────────────────────────────────

function SDGTrackerTab() {
  const { data, isLoading } = usePortfolioImpact();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!data) return null;

  // Build SDG → projects mapping
  const sdgMap: Record<number, string[]> = {};
  for (const proj of data.projects) {
    for (const g of proj.sdg_goals) {
      if (!sdgMap[g.number]) sdgMap[g.number] = [];
      sdgMap[g.number].push(proj.project_name);
    }
  }

  return (
    <div className="space-y-6">
      {/* Coverage summary */}
      <Card>
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-neutral-800">SDG Coverage Map</h2>
            <Badge variant="info">
              {data.sdg_coverage.length} / 17 goals covered
            </Badge>
          </div>
          <SDGCoverageGrid covered={data.sdg_coverage} />
        </CardContent>
      </Card>

      {/* SDG detail grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(SDG_METADATA).map(([numStr, meta]) => {
          const n = Number(numStr);
          const projectNames = sdgMap[n] ?? [];
          const isCovered = projectNames.length > 0;
          return (
            <div
              key={n}
              className={`border rounded-xl p-4 transition-colors ${
                isCovered
                  ? "border-neutral-200 bg-white"
                  : "border-dashed border-neutral-200 bg-neutral-50"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="h-9 w-9 rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0"
                  style={{ backgroundColor: isCovered ? meta.color : "#d1d5db" }}
                >
                  {n}
                </div>
                <div className="min-w-0">
                  <p
                    className={`text-sm font-semibold ${
                      isCovered ? "text-neutral-900" : "text-neutral-400"
                    }`}
                  >
                    {meta.label}
                  </p>
                  <p className="text-xs text-neutral-400">SDG {n}</p>
                </div>
                {isCovered ? (
                  <CheckCircle2
                    className="h-4 w-4 text-green-500 shrink-0 ml-auto"
                  />
                ) : (
                  <AlertCircle
                    className="h-4 w-4 text-neutral-300 shrink-0 ml-auto"
                  />
                )}
              </div>
              {isCovered ? (
                <div className="flex flex-wrap gap-1 mt-2">
                  {projectNames.map((name) => (
                    <span
                      key={name}
                      className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600 truncate max-w-full"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-neutral-400 mt-1">No projects mapped</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function ImpactPage() {
  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">
          Impact Measurement
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Track environmental, social, and governance impact across your project portfolio.
        </p>
      </div>

      <Tabs defaultValue="dashboard">
        <TabsList className="mb-6">
          <TabsTrigger value="dashboard">
            <TrendingUp className="h-4 w-4 mr-1.5" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="carbon">
            <Leaf className="h-4 w-4 mr-1.5" />
            Carbon Credits
          </TabsTrigger>
          <TabsTrigger value="sdg">
            SDG Tracker
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard">
          <DashboardTab />
        </TabsContent>

        <TabsContent value="carbon">
          <CarbonCreditsTab />
        </TabsContent>

        <TabsContent value="sdg">
          <SDGTrackerTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
