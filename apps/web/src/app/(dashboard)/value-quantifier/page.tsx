"use client";

import { useState } from "react";
import {
  BarChart3,
  ChevronDown,
  ChevronUp,
  Loader2,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState } from "@scr/ui";

import { InfoBanner } from "@/components/info-banner";
import {
  formatCurrency,
  kpiQualityBg,
  kpiQualityColor,
  useCalculateValue,
  useValueQuantifier,
  type ValueKPI,
  type ValueQuantifierRequest,
} from "@/lib/value-quantifier";

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_VALUE_DATA = {
  project_name: "Alpine Hydro Partners",
  total_investment: 52_000_000,
  jobs_created: 142,
  kpis: [
    { label: "Net IRR", value: "17.6%", quality: "excellent", description: "Net internal rate of return over 7-year hold period" },
    { label: "NPV", value: "€13.4M", quality: "excellent", description: "Net present value at 10% discount rate" },
    { label: "TVPI", value: "1.56x", quality: "excellent", description: "Total value to paid-in capital" },
    { label: "DPI", value: "0.00x", quality: "neutral", description: "Distributions to paid-in (no distributions yet — hold period)" },
    { label: "DSCR", value: "1.42", description: "Debt service coverage ratio (target ≥ 1.25)", quality: "good" },
    { label: "LCOE", value: "€34/MWh", description: "Levelised cost of energy — competitive vs market €58/MWh", quality: "excellent" },
    { label: "CO₂ Avoided", value: "48,200 t/yr", description: "Annual CO₂ equivalent avoided vs gas benchmark", quality: "excellent" },
    { label: "Payback Period", value: "5.8 years", description: "Simple payback on equity investment", quality: "good" },
  ] as ValueKPI[],
  assumptions: {
    discount_rate: "10.0%",
    electricity_price_kwh: "€0.078",
    project_lifetime_years: 30,
    debt_ratio: "65%",
    interest_rate: "4.5%",
    capacity_mw: 48,
    annual_yield_gwh: 187,
  },
};

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ kpi }: { kpi: ValueKPI }) {
  return (
    <div
      className={`rounded-lg border p-4 flex flex-col gap-1 ${kpiQualityBg(kpi.quality)}`}
    >
      <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
        {kpi.label}
      </p>
      <p className={`text-2xl font-bold ${kpiQualityColor(kpi.quality)}`}>
        {kpi.value}
      </p>
      <p className="text-xs text-neutral-500 leading-snug">{kpi.description}</p>
    </div>
  );
}

// ── Assumptions Section ───────────────────────────────────────────────────────

function AssumptionsPanel({
  assumptions,
}: {
  assumptions: Record<string, number | string>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-neutral-200 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-neutral-50 text-sm font-medium text-neutral-700 hover:bg-neutral-100 transition-colors"
      >
        <span>Model Assumptions</span>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {open && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 px-4 py-3 text-sm">
          {Object.entries(assumptions).map(([key, val]) => (
            <div key={key} className="flex justify-between">
              <span className="text-neutral-500 capitalize">
                {key.replace(/_/g, " ")}
              </span>
              <span className="font-medium text-neutral-800">{String(val)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function ValueQuantifierPage() {
  const [projectId, setProjectId] = useState("");
  const [activeProjectId, setActiveProjectId] = useState<string | undefined>();
  const [overrides, setOverrides] = useState<Partial<ValueQuantifierRequest>>(
    {},
  );
  const [showOverrides, setShowOverrides] = useState(false);

  // Fetch with defaults (GET)
  const defaultQuery = useValueQuantifier(activeProjectId);

  // POST calculate with overrides
  const calculateMutation = useCalculateValue();

  const apiData =
    calculateMutation.data ??
    (calculateMutation.isIdle ? defaultQuery.data : undefined);
  // Show mock data when no project has been selected yet
  const data = apiData ?? (!activeProjectId ? MOCK_VALUE_DATA : undefined);
  const isLoading =
    defaultQuery.isLoading ||
    calculateMutation.isPending;
  const isError = defaultQuery.isError || calculateMutation.isError;

  function handleCalculate() {
    if (!projectId.trim()) return;
    if (
      Object.keys(overrides).some(
        (k) => overrides[k as keyof typeof overrides] !== undefined,
      )
    ) {
      calculateMutation.mutate({ project_id: projectId, ...overrides });
    } else {
      setActiveProjectId(projectId.trim());
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary-100">
          <TrendingUp size={22} className="text-primary-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Value Quantifier
          </h1>
          <p className="text-sm text-neutral-500">
            Deterministic financial KPIs — IRR, NPV, DSCR, LCOE & more
          </p>
        </div>
      </div>

      <InfoBanner>
        The <strong>Value Quantifier</strong> models the financial and impact value of your projects
        using deterministic calculations — IRR, NPV, DSCR, LCOE, and more. Enter a project ID to
        run the model with default assumptions, or override key parameters to run scenario analysis.
      </InfoBanner>

      {/* Input card */}
      <Card>
        <CardContent className="pt-5 space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Project ID
              </label>
              <input
                type="text"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="Enter project UUID…"
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end gap-2">
              <Button
                onClick={handleCalculate}
                disabled={!projectId.trim() || isLoading}
                className="shrink-0"
              >
                {isLoading && (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                )}
                Calculate
              </Button>
              <Button
                variant="outline"
                onClick={() => setShowOverrides((v) => !v)}
                className="shrink-0"
              >
                {showOverrides ? "Hide" : "Override"} Assumptions
              </Button>
            </div>
          </div>

          {/* Overrides panel */}
          {showOverrides && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 border-t border-neutral-100">
              {(
                [
                  { key: "discount_rate", label: "Discount Rate", placeholder: "0.10" },
                  { key: "electricity_price_kwh", label: "Electricity $/kWh", placeholder: "0.08" },
                  { key: "project_lifetime_years", label: "Lifetime (yrs)", placeholder: "25" },
                  { key: "debt_ratio", label: "Debt Ratio", placeholder: "0.70" },
                  { key: "interest_rate", label: "Interest Rate", placeholder: "0.05" },
                  { key: "capex_usd", label: "CAPEX (USD)", placeholder: "auto" },
                ] as const
              ).map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-neutral-500 mb-1">
                    {label}
                  </label>
                  <input
                    type="number"
                    step="any"
                    placeholder={placeholder}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      setOverrides((prev) => ({
                        ...prev,
                        [key]: isNaN(v) ? undefined : v,
                      }));
                    }}
                    className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-blue-600" />
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Failed to calculate. Check the project ID and try again.
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !data && !isError && (
        <EmptyState
          icon={<BarChart3 size={40} className="text-neutral-400" />}
          title="No project selected"
          description="Enter a project ID above and click Calculate to see financial KPIs."
        />
      )}

      {/* Results */}
      {data && !isLoading && (
        <div className="space-y-6">
          {/* Project header */}
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold text-neutral-900">
              {data.project_name}
            </h2>
            {data.total_investment !== null && (
              <Badge variant="neutral">
                <Zap size={12} className="mr-1" />
                Total Investment: {formatCurrency(data.total_investment)}
              </Badge>
            )}
            {data.jobs_created !== null && (
              <Badge variant="neutral">
                {data.jobs_created.toLocaleString()} jobs created
              </Badge>
            )}
          </div>

          {/* KPI grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {data.kpis.map((kpi) => (
              <KpiCard key={kpi.label} kpi={kpi} />
            ))}
          </div>

          {/* Assumptions */}
          <AssumptionsPanel assumptions={data.assumptions} />
        </div>
      )}
    </div>
  );
}
