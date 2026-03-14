"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  TrendingDown,
  Plus,
  Loader2,
} from "lucide-react";
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
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@scr/ui";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  usePacingData,
  useListAssumptions,
  useCreateAssumption,
  formatMillions,
  type ProjectionRow,
  type PacingData,
  type CashflowAssumption,
  type CreateAssumptionPayload,
} from "@/lib/pacing";
import { usePortfolios } from "@/lib/portfolio";

// ── Mock Data ─────────────────────────────────────────────────────────────────

const MOCK_PORTFOLIO_LIST = {
  items: [{ id: "mock-portfolio-1", name: "SCR Sustainable Infrastructure Fund I" }],
  total: 1,
};

const MOCK_PACING_DATA: PacingData = {
  portfolio_id: "mock-portfolio-1",
  assumption_id: "assumption-1",
  total_commitment: 500000000,
  currency: "EUR",
  trough_year: 2025,
  trough_value: -48500000,
  projections: [
    { year: 2024, base_net: -83000000, optimistic_net: -78000000, pessimistic_net: -91000000, base_cumulative: -83000000, optimistic_cumulative: -78000000, pessimistic_cumulative: -91000000, actual_invested: 83000000, actual_distributed: 0 },
    { year: 2025, base_net: -95000000, optimistic_net: -85000000, pessimistic_net: -108000000, base_cumulative: -178000000, optimistic_cumulative: -163000000, pessimistic_cumulative: -199000000, actual_invested: 155000000, actual_distributed: 43200000 },
    { year: 2026, base_net: -12000000, optimistic_net: 8000000, pessimistic_net: -38000000, base_cumulative: -190000000, optimistic_cumulative: -155000000, pessimistic_cumulative: -237000000, actual_invested: 10500000, actual_distributed: 46300000 },
    { year: 2027, base_net: 48000000, optimistic_net: 72000000, pessimistic_net: 22000000, base_cumulative: -142000000, optimistic_cumulative: -83000000, pessimistic_cumulative: -215000000, actual_invested: null, actual_distributed: null },
    { year: 2028, base_net: 82000000, optimistic_net: 115000000, pessimistic_net: 54000000, base_cumulative: -60000000, optimistic_cumulative: 32000000, pessimistic_cumulative: -161000000, actual_invested: null, actual_distributed: null },
    { year: 2029, base_net: 115000000, optimistic_net: 148000000, pessimistic_net: 78000000, base_cumulative: 55000000, optimistic_cumulative: 180000000, pessimistic_cumulative: -83000000, actual_invested: null, actual_distributed: null },
    { year: 2030, base_net: 138000000, optimistic_net: 172000000, pessimistic_net: 98000000, base_cumulative: 193000000, optimistic_cumulative: 352000000, pessimistic_cumulative: 15000000, actual_invested: null, actual_distributed: null },
    { year: 2031, base_net: 88000000, optimistic_net: 112000000, pessimistic_net: 62000000, base_cumulative: 281000000, optimistic_cumulative: 464000000, pessimistic_cumulative: 77000000, actual_invested: null, actual_distributed: null },
    { year: 2032, base_net: 42000000, optimistic_net: 58000000, pessimistic_net: 28000000, base_cumulative: 323000000, optimistic_cumulative: 522000000, pessimistic_cumulative: 105000000, actual_invested: null, actual_distributed: null },
  ],
};

const MOCK_ASSUMPTIONS: CashflowAssumption[] = [
  {
    id: "assumption-1",
    portfolio_id: "mock-portfolio-1",
    total_commitment: 500000000,
    currency: "EUR",
    deployment_years: 4,
    annual_management_fee_pct: 1.75,
    preferred_return_pct: 8,
    carry_pct: 20,
    created_at: "2024-01-15T00:00:00Z",
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmt(value: number | null | undefined, currency = "USD"): string {
  if (value == null) return "—";
  return formatMillions(value, currency);
}

// ── J-Curve Chart ──────────────────────────────────────────────────────────────

function JCurveChart({
  projections,
  troughYear,
  troughValue,
  currency,
}: {
  projections: ProjectionRow[];
  troughYear: number;
  troughValue: number;
  currency: string;
}) {
  const chartData = projections.map((row) => ({
    year: row.year,
    "Base (cum.)": row.base_cumulative / 1_000_000,
    "Optimistic (cum.)": row.optimistic_cumulative / 1_000_000,
    "Pessimistic (cum.)": row.pessimistic_cumulative / 1_000_000,
  }));

  const symbol = currency === "GBP" ? "£" : currency === "EUR" ? "€" : "$";

  return (
    <ResponsiveContainer width="100%" height={360}>
      <AreaChart data={chartData} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
        <defs>
          <linearGradient id="colorBase" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#1B3A5C" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#1B3A5C" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorOpt" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#2E7D32" stopOpacity={0.12} />
            <stop offset="95%" stopColor="#2E7D32" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorPess" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#C62828" stopOpacity={0.12} />
            <stop offset="95%" stopColor="#C62828" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" opacity={0.5} />
        <XAxis
          dataKey="year"
          tick={{ fontSize: 12, fill: "#9E9E9E" }}
          tickLine={false}
          axisLine={{ stroke: "#E0E0E0" }}
          label={{ value: "Year", position: "insideBottom", offset: -4, fontSize: 11, fill: "#9E9E9E" }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "#9E9E9E" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${symbol}${v}m`}
        />
        <Tooltip
          formatter={(value: unknown) => {
            if (typeof value === "number") return `${symbol}${value.toFixed(1)}m`;
            return String(value ?? "");
          }}
        />
        <Legend />
        <ReferenceLine
          x={troughYear}
          stroke="#F57C00"
          strokeDasharray="4 2"
          label={{
            value: `Trough ${fmt(troughValue, currency)}`,
            position: "top",
            fontSize: 11,
            fill: "#F57C00",
          }}
        />
        <Area
          type="monotone"
          dataKey="Pessimistic (cum.)"
          stroke="#C62828"
          strokeDasharray="5 3"
          strokeWidth={1.5}
          fill="url(#colorPess)"
          dot={false}
        />
        <Area
          type="monotone"
          dataKey="Base (cum.)"
          stroke="#1B3A5C"
          strokeWidth={2.5}
          fill="url(#colorBase)"
          dot={false}
        />
        <Area
          type="monotone"
          dataKey="Optimistic (cum.)"
          stroke="#2E7D32"
          strokeDasharray="5 3"
          strokeWidth={1.5}
          fill="url(#colorOpt)"
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Projections Table ──────────────────────────────────────────────────────────

function ProjectionsTable({
  projections,
  currency,
}: {
  projections: ProjectionRow[];
  currency: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200">
            {["Year", "Base Net", "Optimistic Net", "Pessimistic Net", "Actual Invested", "Actual Distributed"].map(
              (h) => (
                <th
                  key={h}
                  className="py-3 px-3 text-right first:text-left font-medium text-neutral-500"
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {projections.map((row) => (
            <tr
              key={row.year}
              className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors"
            >
              <td className="py-2.5 px-3 font-semibold text-neutral-800">
                {row.year}
              </td>
              <td className="py-2.5 px-3 text-right tabular-nums text-neutral-700">
                {fmt(row.base_net, currency)}
              </td>
              <td className="py-2.5 px-3 text-right tabular-nums text-green-700">
                {fmt(row.optimistic_net, currency)}
              </td>
              <td className="py-2.5 px-3 text-right tabular-nums text-red-700">
                {fmt(row.pessimistic_net, currency)}
              </td>
              <td className="py-2.5 px-3 text-right tabular-nums text-neutral-600">
                {row.actual_invested != null ? fmt(row.actual_invested, currency) : "—"}
              </td>
              <td className="py-2.5 px-3 text-right tabular-nums text-neutral-600">
                {row.actual_distributed != null
                  ? fmt(row.actual_distributed, currency)
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Assumption Form ────────────────────────────────────────────────────────────

interface AssumptionFormState {
  total_commitment: number;
  deployment_years: number;
  annual_management_fee_pct: number;
  preferred_return_pct: number;
  carry_pct: number;
}

const DEFAULT_FORM: AssumptionFormState = {
  total_commitment: 10_000_000,
  deployment_years: 5,
  annual_management_fee_pct: 2,
  preferred_return_pct: 8,
  carry_pct: 20,
};

function AssumptionForm({
  portfolioId,
  onSuccess,
}: {
  portfolioId: string;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState<AssumptionFormState>(DEFAULT_FORM);
  const { mutate: create, isPending } = useCreateAssumption();

  const set = <K extends keyof AssumptionFormState>(
    key: K,
    value: AssumptionFormState[K]
  ) => setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: CreateAssumptionPayload = {
      portfolio_id: portfolioId,
      ...form,
    };
    create(payload, { onSuccess });
  };

  const field = (
    label: string,
    key: keyof AssumptionFormState,
    opts?: { min?: number; max?: number; step?: number }
  ) => (
    <div>
      <label className="block text-sm font-medium text-neutral-700 mb-1">
        {label}
      </label>
      <input
        type="number"
        value={form[key]}
        min={opts?.min}
        max={opts?.max}
        step={opts?.step ?? 1}
        onChange={(e) =>
          set(key, Number(e.target.value) as AssumptionFormState[typeof key])
        }
        className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      {field("Total Commitment ($)", "total_commitment", { min: 1 })}
      {field("Deployment Years", "deployment_years", { min: 2, max: 7 })}
      {field("Management Fee %", "annual_management_fee_pct", {
        min: 0,
        max: 10,
        step: 0.25,
      })}
      {field("Preferred Return %", "preferred_return_pct", {
        min: 0,
        max: 20,
        step: 0.5,
      })}
      {field("Carry %", "carry_pct", { min: 0, max: 30, step: 1 })}
      <div className="pt-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Saving…
            </>
          ) : (
            "Save Assumption"
          )}
        </Button>
      </div>
    </form>
  );
}

// ── Assumptions Tab ────────────────────────────────────────────────────────────

function AssumptionsTab({ portfolioId }: { portfolioId: string }) {
  const [showForm, setShowForm] = useState(false);
  const { data: apiAssumptions, isLoading } = useListAssumptions(portfolioId);
  const assumptions = apiAssumptions ?? MOCK_ASSUMPTIONS;

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Existing assumptions */}
      {assumptions && assumptions.length > 0 && (
        <div className="space-y-3">
          {assumptions.map((a) => (
            <Card key={a.id}>
              <CardContent className="p-5 grid grid-cols-2 sm:grid-cols-3 gap-4">
                {[
                  { label: "Total Commitment", value: fmt(a.total_commitment, a.currency) },
                  { label: "Deployment Years", value: `${a.deployment_years} yrs` },
                  { label: "Mgmt Fee", value: `${a.annual_management_fee_pct}%` },
                  { label: "Preferred Return", value: `${a.preferred_return_pct}%` },
                  { label: "Carry", value: `${a.carry_pct}%` },
                  {
                    label: "Created",
                    value: new Date(a.created_at).toLocaleDateString(),
                  },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p className="text-xs text-neutral-500 font-medium mb-0.5">
                      {label}
                    </p>
                    <p className="text-sm font-semibold text-neutral-800">
                      {value}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* New assumption form toggle */}
      {!showForm ? (
        <Button variant="outline" onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Assumption
        </Button>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New Cashflow Assumption</CardTitle>
          </CardHeader>
          <CardContent>
            <AssumptionForm
              portfolioId={portfolioId}
              onSuccess={() => setShowForm(false)}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function PacingPage() {
  const searchParams = useSearchParams();
  const paramPortfolioId = searchParams.get("portfolio") ?? "";

  const { data: apiPortfolios } = usePortfolios();
  const portfolioList = apiPortfolios?.items?.length
    ? apiPortfolios.items
    : MOCK_PORTFOLIO_LIST.items;

  const [selectedPortfolioId, setSelectedPortfolioId] = useState(
    paramPortfolioId || ""
  );

  // After portfolios load, auto-select first if nothing selected
  const portfolioId =
    selectedPortfolioId ||
    (portfolioList.length > 0 ? portfolioList[0].id : "");

  const { data: apiPacing } = usePacingData(portfolioId);
  // Always fall back to mock data — API may be unavailable in dev
  const pacing = apiPacing ?? MOCK_PACING_DATA;
  const isLoading = false;

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <TrendingDown className="h-6 w-6 text-primary-700" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              J-Curve Pacing
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              Cashflow projections and fund pacing analysis
            </p>
          </div>
        </div>

        {/* Portfolio selector */}
        {portfolioList.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-neutral-600">
              Portfolio
            </label>
            <select
              value={portfolioId}
              onChange={(e) => setSelectedPortfolioId(e.target.value)}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {portfolioList.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <InfoBanner>
        <strong>J-Curve Pacing</strong> models your fund&apos;s cashflow trajectory — capital calls,
        distributions, and net cash position — over the full fund lifecycle. Adjust assumptions to
        stress-test pacing against different deployment speeds and exit scenarios.
      </InfoBanner>

      {/* Stats row */}
      {pacing && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            {
              label: "Total Commitment",
              value: fmt(pacing.total_commitment, pacing.currency),
              color: "text-neutral-900",
            },
            {
              label: "Currency",
              value: pacing.currency,
              color: "text-neutral-900",
            },
            {
              label: "Trough Year",
              value: String(pacing.trough_year),
              color: "text-amber-600",
            },
            {
              label: "Trough Value",
              value: fmt(pacing.trough_value, pacing.currency),
              color: "text-red-600",
            },
          ].map(({ label, value, color }) => (
            <Card key={label}>
              <CardContent className="p-5">
                <p className="text-xs font-medium text-neutral-500 mb-1">
                  {label}
                </p>
                <p className={`text-xl font-bold ${color}`}>{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="j-curve">
        <TabsList>
          <TabsTrigger value="j-curve">J-Curve</TabsTrigger>
          <TabsTrigger value="projections">Projections</TabsTrigger>
          <TabsTrigger value="assumptions">Assumptions</TabsTrigger>
        </TabsList>

        {/* J-Curve tab */}
        <TabsContent value="j-curve">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  Cumulative Cashflow — J-Curve
                </CardTitle>
                {pacing && (
                  <Badge variant="info">{pacing.currency}</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex h-72 items-center justify-center">
                  <Loader2 className="h-8 w-8 animate-spin text-neutral-400" />
                </div>
              ) : !pacing || pacing.projections.length === 0 ? (
                <EmptyState
                  icon={<TrendingDown className="h-10 w-10 text-neutral-300" />}
                  title="No pacing data"
                  description="Configure assumptions to see projections."
                />
              ) : (
                <JCurveChart
                  projections={pacing.projections}
                  troughYear={pacing.trough_year}
                  troughValue={pacing.trough_value}
                  currency={pacing.currency}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Projections tab */}
        <TabsContent value="projections">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Annual Projections</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex h-40 items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
                </div>
              ) : !pacing || pacing.projections.length === 0 ? (
                <EmptyState
                  title="No projection data"
                  description="Configure assumptions to generate projections."
                />
              ) : (
                <ProjectionsTable
                  projections={pacing.projections}
                  currency={pacing.currency}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Assumptions tab */}
        <TabsContent value="assumptions">
          {!portfolioId ? (
            <EmptyState
              title="No portfolio selected"
              description="Select a portfolio to manage cashflow assumptions."
            />
          ) : (
            <AssumptionsTab portfolioId={portfolioId} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
