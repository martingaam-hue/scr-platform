"use client";

import { useState } from "react";
import {
  Calculator,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  BarChart3,
  Plus,
  Download,
  CheckCircle,
  Loader2,
  Lightbulb,
  ArrowRightLeft,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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
  useValuations,
  useCreateValuation,
  useRunSensitivity,
  useTriggerReport,
  useSuggestAssumptions,
  useCompareValuations,
  statusVariant,
  methodLabel,
  formatEV,
  sensitivityCellColor,
  type ValuationResponse,
  type ValuationMethod,
  type DCFParams,
  type ComparableParams,
  type ReplacementCostParams,
  type SensitivityMatrix,
  type AssumptionSuggestion,
} from "@/lib/valuation";
import { AIFeedback } from "@/components/ai-feedback";
import { CitationBadges } from "@/components/citations/citation-badges";
import { LineagePanel } from "@/components/lineage/lineage-panel";
import { useSimilarComps } from "@/lib/comps";

// ── Wizard steps ─────────────────────────────────────────────────────────────

const METHODS: Array<{
  key: ValuationMethod;
  label: string;
  description: string;
}> = [
  {
    key: "dcf",
    label: "Discounted Cash Flow",
    description:
      "Project future cash flows and discount to present value using WACC. Best for operational projects with predictable cash flows.",
  },
  {
    key: "comparables",
    label: "Comparable Transactions",
    description:
      "Apply market multiples (EV/EBITDA, EV/MW) from comparable deals. Best when market data is available.",
  },
  {
    key: "replacement_cost",
    label: "Replacement Cost",
    description:
      "Estimate cost to replicate the asset from scratch less depreciation. Best for early-stage or asset-heavy projects.",
  },
  {
    key: "blended",
    label: "Blended / Weighted",
    description:
      "Weighted average of multiple pre-computed valuations. Best for presenting a range to LPs.",
  },
];

// ── Step 1: Method selection ─────────────────────────────────────────────────

function MethodSelector({
  selected,
  onChange,
}: {
  selected: ValuationMethod | null;
  onChange: (m: ValuationMethod) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {METHODS.map((m) => (
        <button
          key={m.key}
          onClick={() => onChange(m.key)}
          className={`text-left rounded-lg border-2 p-4 transition-all ${
            selected === m.key
              ? "border-blue-600 bg-blue-50"
              : "border-neutral-200 bg-white hover:border-blue-300"
          }`}
        >
          <div className="font-semibold text-sm text-neutral-900 mb-1">
            {m.label}
          </div>
          <p className="text-xs text-neutral-500 leading-relaxed">
            {m.description}
          </p>
        </button>
      ))}
    </div>
  );
}

// ── Step 2: Input forms ───────────────────────────────────────────────────────

function DCFForm({
  params,
  onChange,
  suggestion,
  onSuggest,
  isSuggesting,
}: {
  params: DCFParams;
  onChange: (p: DCFParams) => void;
  suggestion: AssumptionSuggestion | null;
  onSuggest: () => void;
  isSuggesting: boolean;
}) {
  const cashFlowStr = params.cash_flows.join(", ");

  function applyFromSuggestion() {
    if (!suggestion) return;
    onChange({
      ...params,
      discount_rate: suggestion.discount_rate,
      terminal_growth_rate: suggestion.terminal_growth_rate,
      terminal_method: suggestion.terminal_method as "gordon" | "exit_multiple",
    });
  }

  return (
    <div className="space-y-4">
      {suggestion && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 flex items-start gap-3">
          <Lightbulb className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
          <div className="flex-1 text-sm text-amber-800">
            <span className="font-medium">AI suggestion:</span> Discount rate{" "}
            {(suggestion.discount_rate * 100).toFixed(1)}%, terminal growth{" "}
            {(suggestion.terminal_growth_rate * 100).toFixed(1)}% —{" "}
            {suggestion.reasoning.discount_rate}
          </div>
          <Button size="sm" variant="outline" onClick={applyFromSuggestion}>
            Apply
          </Button>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Discount Rate (WACC)
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              step="0.001"
              min="0.01"
              max="0.5"
              value={params.discount_rate}
              onChange={(e) =>
                onChange({ ...params, discount_rate: parseFloat(e.target.value) || 0 })
              }
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={onSuggest}
              disabled={isSuggesting}
            >
              {isSuggesting ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Lightbulb className="h-3 w-3" />
              )}
            </Button>
          </div>
          <p className="text-xs text-neutral-400 mt-1">
            Enter as decimal (e.g. 0.10 = 10%)
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Terminal Growth Rate
          </label>
          <input
            type="number"
            step="0.001"
            min="0"
            max="0.1"
            value={params.terminal_growth_rate ?? 0.02}
            onChange={(e) =>
              onChange({
                ...params,
                terminal_growth_rate: parseFloat(e.target.value) || 0,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Terminal Method
          </label>
          <select
            value={params.terminal_method ?? "gordon"}
            onChange={(e) =>
              onChange({
                ...params,
                terminal_method: e.target.value as "gordon" | "exit_multiple",
              })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="gordon">Gordon Growth Model</option>
            <option value="exit_multiple">Exit Multiple</option>
          </select>
        </div>

        {params.terminal_method === "exit_multiple" && (
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Exit Multiple
            </label>
            <input
              type="number"
              step="0.5"
              min="1"
              value={params.exit_multiple ?? 10}
              onChange={(e) =>
                onChange({
                  ...params,
                  exit_multiple: parseFloat(e.target.value) || 10,
                })
              }
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Net Debt
          </label>
          <input
            type="number"
            step="1000"
            value={params.net_debt ?? 0}
            onChange={(e) =>
              onChange({ ...params, net_debt: parseFloat(e.target.value) || 0 })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Annual Cash Flows (comma-separated)
        </label>
        <textarea
          rows={3}
          value={cashFlowStr}
          onChange={(e) => {
            const cfs = e.target.value
              .split(",")
              .map((s) => parseFloat(s.trim()))
              .filter((n) => !isNaN(n));
            onChange({ ...params, cash_flows: cfs });
          }}
          placeholder="1000000, 1200000, 1400000, 1600000, 1800000"
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
        <p className="text-xs text-neutral-400 mt-1">
          Enter yearly amounts in valuation currency, Year 1 to Year N
        </p>
      </div>
    </div>
  );
}

function ComparableForm({
  params,
  onChange,
  projectId,
}: {
  params: ComparableParams;
  onChange: (p: ComparableParams) => void;
  projectId?: string | null;
}) {
  const similarComps = useSimilarComps(projectId);

  function importFromComps() {
    const items = similarComps.data?.items ?? [];
    if (!items.length) return;
    const imported = items.map((r) => ({
      name: r.comp.deal_name,
      ev_ebitda: r.comp.ebitda_multiple ?? null,
      ev_mw: r.comp.ev_per_mw ?? null,
      geography: r.comp.geography ?? null,
      notes: r.rationale,
    }));
    onChange({ ...params, comparables: [...params.comparables, ...imported] });
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Subject EBITDA
          </label>
          <input
            type="number"
            step="10000"
            value={params.subject_ebitda ?? ""}
            onChange={(e) =>
              onChange({
                ...params,
                subject_ebitda: e.target.value ? parseFloat(e.target.value) : null,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Subject Capacity (MW)
          </label>
          <input
            type="number"
            step="1"
            value={params.subject_capacity_mw ?? ""}
            onChange={(e) =>
              onChange({
                ...params,
                subject_capacity_mw: e.target.value
                  ? parseFloat(e.target.value)
                  : null,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Net Debt
          </label>
          <input
            type="number"
            step="1000"
            value={params.net_debt ?? 0}
            onChange={(e) =>
              onChange({ ...params, net_debt: parseFloat(e.target.value) || 0 })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-neutral-700">
            Comparable Companies
          </label>
          <div className="flex items-center gap-2">
            {projectId && (
              <Button
                size="sm"
                variant="outline"
                onClick={importFromComps}
                disabled={similarComps.isLoading || !similarComps.data?.items.length}
                title={
                  !similarComps.data?.items.length
                    ? "No similar comps found for this project"
                    : `Import ${similarComps.data.items.length} similar comps from library`
                }
              >
                {similarComps.isLoading ? (
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <ArrowRightLeft className="h-3 w-3 mr-1" />
                )}
                Import from Library
                {similarComps.data?.items.length ? (
                  <span className="ml-1 text-xs text-neutral-400">
                    ({similarComps.data.items.length})
                  </span>
                ) : null}
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                onChange({
                  ...params,
                  comparables: [
                    ...params.comparables,
                    { name: "", ev_ebitda: null, ev_mw: null },
                  ],
                })
              }
            >
              <Plus className="h-3 w-3 mr-1" />
              Add Row
            </Button>
          </div>
        </div>
        <div className="overflow-x-auto rounded-md border border-neutral-200">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50">
                <th className="text-left px-3 py-2 font-medium text-neutral-600">
                  Name
                </th>
                <th className="text-right px-3 py-2 font-medium text-neutral-600">
                  EV/EBITDA
                </th>
                <th className="text-right px-3 py-2 font-medium text-neutral-600">
                  EV/MW
                </th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {params.comparables.map((c, i) => (
                <tr key={i} className="border-t border-neutral-100">
                  <td className="px-3 py-2">
                    <input
                      value={c.name}
                      onChange={(e) => {
                        const updated = [...params.comparables];
                        updated[i] = { ...updated[i], name: e.target.value };
                        onChange({ ...params, comparables: updated });
                      }}
                      placeholder="Company / deal name"
                      className="w-full text-sm focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      step="0.5"
                      value={c.ev_ebitda ?? ""}
                      onChange={(e) => {
                        const updated = [...params.comparables];
                        updated[i] = {
                          ...updated[i],
                          ev_ebitda: e.target.value
                            ? parseFloat(e.target.value)
                            : null,
                        };
                        onChange({ ...params, comparables: updated });
                      }}
                      placeholder="—"
                      className="w-full text-sm text-right focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      step="10"
                      value={c.ev_mw ?? ""}
                      onChange={(e) => {
                        const updated = [...params.comparables];
                        updated[i] = {
                          ...updated[i],
                          ev_mw: e.target.value
                            ? parseFloat(e.target.value)
                            : null,
                        };
                        onChange({ ...params, comparables: updated });
                      }}
                      placeholder="—"
                      className="w-full text-sm text-right focus:outline-none"
                    />
                  </td>
                  <td className="px-3 py-2 text-center">
                    <button
                      onClick={() => {
                        const updated = params.comparables.filter(
                          (_, j) => j !== i
                        );
                        onChange({ ...params, comparables: updated });
                      }}
                      className="text-neutral-400 hover:text-red-500 text-xs"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
              {params.comparables.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-3 py-6 text-center text-sm text-neutral-400"
                  >
                    Add at least one comparable
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ReplacementCostFormInner({
  params,
  onChange,
}: {
  params: ReplacementCostParams;
  onChange: (p: ReplacementCostParams) => void;
}) {
  const componentEntries = Object.entries(params.component_costs);

  function updateComponent(key: string, value: number) {
    onChange({
      ...params,
      component_costs: { ...params.component_costs, [key]: value },
    });
  }

  function removeComponent(key: string) {
    const { [key]: _removed, ...rest } = params.component_costs;
    onChange({ ...params, component_costs: rest });
  }

  function addComponent() {
    const key = `Component ${componentEntries.length + 1}`;
    onChange({
      ...params,
      component_costs: { ...params.component_costs, [key]: 0 },
    });
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-neutral-700">
            Component Costs
          </label>
          <Button size="sm" variant="outline" onClick={addComponent}>
            <Plus className="h-3 w-3 mr-1" />
            Add Component
          </Button>
        </div>
        <div className="space-y-2">
          {componentEntries.map(([k, v]) => (
            <div key={k} className="flex items-center gap-2">
              <input
                value={k}
                onChange={(e) => {
                  const { [k]: oldVal, ...rest } = params.component_costs;
                  onChange({
                    ...params,
                    component_costs: { ...rest, [e.target.value]: oldVal },
                  });
                }}
                className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Component name"
              />
              <input
                type="number"
                step="10000"
                value={v}
                onChange={(e) =>
                  updateComponent(k, parseFloat(e.target.value) || 0)
                }
                className="w-36 rounded-md border border-neutral-300 px-3 py-2 text-sm text-right focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => removeComponent(k)}
                className="text-neutral-400 hover:text-red-500 text-sm px-1"
              >
                ✕
              </button>
            </div>
          ))}
          {componentEntries.length === 0 && (
            <p className="text-sm text-neutral-400 text-center py-4">
              Add at least one component
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Land Value
          </label>
          <input
            type="number"
            step="10000"
            value={params.land_value ?? 0}
            onChange={(e) =>
              onChange({ ...params, land_value: parseFloat(e.target.value) || 0 })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Development Costs
          </label>
          <input
            type="number"
            step="10000"
            value={params.development_costs ?? 0}
            onChange={(e) =>
              onChange({
                ...params,
                development_costs: parseFloat(e.target.value) || 0,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Depreciation (%)
          </label>
          <input
            type="number"
            step="1"
            min="0"
            max="100"
            value={params.depreciation_pct ?? 0}
            onChange={(e) =>
              onChange({
                ...params,
                depreciation_pct: parseFloat(e.target.value) || 0,
              })
            }
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </div>
  );
}

// ── Step 3: Results display ──────────────────────────────────────────────────

function SensitivityHeatmap({
  matrix,
}: {
  matrix: SensitivityMatrix;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="p-2 text-neutral-500 font-medium">
              r ↓ / g →
            </th>
            {matrix.col_values.map((cv) => (
              <th
                key={cv}
                className="p-2 text-neutral-600 font-medium text-right min-w-[80px]"
              >
                {(cv * 100).toFixed(1)}%
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.matrix.map((row, ri) => (
            <tr key={ri}>
              <th className="p-2 text-neutral-600 font-medium text-right pr-4">
                {(matrix.row_values[ri] * 100).toFixed(1)}%
              </th>
              {row.map((cell, ci) => (
                <td
                  key={ci}
                  className={`p-2 text-right rounded ${sensitivityCellColor(
                    cell,
                    matrix.base_value
                  )}`}
                >
                  {cell !== null
                    ? (cell / 1_000_000).toFixed(1) + "M"
                    : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-neutral-400 mt-2">
        Values in millions. Green = above base ({(matrix.base_value / 1_000_000).toFixed(1)}M),
        Red = below base.
      </p>
    </div>
  );
}

function ValuationResultCard({
  valuation,
  onRunSensitivity,
  onTriggerReport,
  sensitivity,
  isRunning,
  isTriggering,
}: {
  valuation: ValuationResponse;
  onRunSensitivity: () => void;
  onTriggerReport: () => void;
  sensitivity: SensitivityMatrix | null;
  isRunning: boolean;
  isTriggering: boolean;
}) {
  const assumptions = valuation.assumptions as Record<string, unknown>;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-neutral-500 uppercase tracking-wide mb-1">
              Enterprise Value
            </div>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold text-blue-700">
                {formatEV(valuation.enterprise_value, valuation.currency)}
              </div>
              <LineagePanel
                entityType="valuation"
                entityId={valuation.id}
                fieldName="enterprise_value"
                fieldLabel="Enterprise Value"
              />
            </div>
            {/* Add aiTaskLogId from AI task log when available */}
            <CitationBadges aiTaskLogId={undefined} className="mt-1" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-xs text-neutral-500 uppercase tracking-wide mb-1">
              Equity Value
            </div>
            <div className="text-2xl font-bold text-emerald-700">
              {formatEV(valuation.equity_value, valuation.currency)}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Key Assumptions</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {Object.entries(assumptions)
              .filter(([k]) => k !== "method")
              .map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <dt className="text-neutral-500 capitalize">
                    {k.replace(/_/g, " ")}
                  </dt>
                  <dd className="font-medium text-neutral-900">
                    {typeof v === "number"
                      ? v < 1
                        ? `${(v * 100).toFixed(1)}%`
                        : v.toLocaleString()
                      : String(v)}
                  </dd>
                </div>
              ))}
          </dl>
        </CardContent>
      </Card>

      {valuation.method === "dcf" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Sensitivity Analysis</CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={onRunSensitivity}
                disabled={isRunning}
              >
                {isRunning ? (
                  <Loader2 className="h-3 w-3 animate-spin mr-1" />
                ) : (
                  <BarChart3 className="h-3 w-3 mr-1" />
                )}
                Run
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {sensitivity ? (
              <SensitivityHeatmap matrix={sensitivity} />
            ) : (
              <p className="text-sm text-neutral-400 text-center py-4">
                Click "Run" to generate discount rate × growth rate matrix
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex gap-3">
        <Button
          variant="outline"
          onClick={onTriggerReport}
          disabled={isTriggering}
        >
          {isTriggering ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Download className="h-4 w-4 mr-2" />
          )}
          Generate Report
        </Button>
      </div>
      <AIFeedback
        taskType="valuation"
        entityType="valuation"
        entityId={valuation.id}
        compact
        className="mt-2"
      />
    </div>
  );
}

// ── Builder tab ──────────────────────────────────────────────────────────────

const DEFAULT_DCF: DCFParams = {
  cash_flows: [1_000_000, 1_200_000, 1_400_000, 1_600_000, 1_800_000],
  discount_rate: 0.1,
  terminal_growth_rate: 0.02,
  terminal_method: "gordon",
  net_debt: 0,
};

const DEFAULT_COMP: ComparableParams = {
  comparables: [
    { name: "Comparable A", ev_ebitda: 12, ev_mw: 950 },
    { name: "Comparable B", ev_ebitda: 10, ev_mw: 1100 },
  ],
  subject_ebitda: null,
  subject_capacity_mw: null,
  net_debt: 0,
  multiple_types: ["ev_ebitda", "ev_mw"],
};

const DEFAULT_REPLACEMENT: ReplacementCostParams = {
  component_costs: { Equipment: 5_000_000, Installation: 2_000_000 },
  land_value: 500_000,
  development_costs: 300_000,
  depreciation_pct: 10,
  net_debt: 0,
};

function BuilderTab({ projectId }: { projectId: string | null }) {
  const [step, setStep] = useState(1);
  const [method, setMethod] = useState<ValuationMethod | null>(null);
  const [currency, setCurrency] = useState("USD");
  const [dcfParams, setDcfParams] = useState<DCFParams>(DEFAULT_DCF);
  const [compParams, setCompParams] = useState<ComparableParams>(DEFAULT_COMP);
  const [replParams, setReplParams] =
    useState<ReplacementCostParams>(DEFAULT_REPLACEMENT);
  const [createdValuation, setCreatedValuation] =
    useState<ValuationResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityMatrix | null>(null);
  const [suggestion, setSuggestion] = useState<AssumptionSuggestion | null>(null);

  const createValuation = useCreateValuation();
  const runSensitivity = useRunSensitivity();
  const triggerReport = useTriggerReport();
  const suggestAssumptions = useSuggestAssumptions();

  async function handleCreate() {
    if (!projectId || !method) return;
    const body = {
      project_id: projectId,
      method,
      currency,
      dcf_params: method === "dcf" ? dcfParams : null,
      comparable_params: method === "comparables" ? compParams : null,
      replacement_params: method === "replacement_cost" ? replParams : null,
    };
    const result = await createValuation.mutateAsync(body as Parameters<typeof createValuation.mutateAsync>[0]);
    setCreatedValuation(result);
    setStep(3);
  }

  async function handleSensitivity() {
    if (!createdValuation) return;
    const result = await runSensitivity.mutateAsync({
      valuationId: createdValuation.id,
      base_params: dcfParams,
      row_variable: "discount_rate",
      row_values: [0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13],
      col_variable: "terminal_growth_rate",
      col_values: [0.01, 0.015, 0.02, 0.025, 0.03],
    });
    setSensitivity(result);
  }

  async function handleSuggest() {
    const result = await suggestAssumptions.mutateAsync({
      project_type: "solar",
      geography: "Kenya",
      stage: "construction",
    });
    setSuggestion(result);
  }

  if (!projectId) {
    return (
      <EmptyState
        title="No project selected"
        description="Select a project from your portfolio to create a valuation."
        icon={<Calculator className="h-8 w-8 text-neutral-400" />}
      />
    );
  }

  return (
    <div className="max-w-2xl">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6">
        {[
          { n: 1, label: "Method" },
          { n: 2, label: "Inputs" },
          { n: 3, label: "Results" },
        ].map((s, i) => (
          <div key={s.n} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold ${
                step > s.n
                  ? "bg-green-600 text-white"
                  : step === s.n
                  ? "bg-blue-600 text-white"
                  : "bg-neutral-200 text-neutral-500"
              }`}
            >
              {step > s.n ? <CheckCircle className="h-4 w-4" /> : s.n}
            </div>
            <span
              className={`text-sm ${
                step === s.n ? "font-medium text-neutral-900" : "text-neutral-400"
              }`}
            >
              {s.label}
            </span>
            {i < 2 && (
              <ChevronRight className="h-4 w-4 text-neutral-300 mx-1" />
            )}
          </div>
        ))}
      </div>

      {/* Step 1 */}
      {step === 1 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-base font-semibold text-neutral-900 mb-1">
              Select Valuation Method
            </h2>
            <p className="text-sm text-neutral-500">
              Choose the methodology that best fits your project type and
              available data.
            </p>
          </div>
          <MethodSelector
            selected={method}
            onChange={setMethod}
          />
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-neutral-700">
              Currency
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {["USD", "EUR", "GBP", "KES", "NGN", "ZAR"].map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => setStep(2)}
              disabled={!method}
            >
              Next: Inputs
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* Step 2 */}
      {step === 2 && method && (
        <div className="space-y-6">
          <div>
            <h2 className="text-base font-semibold text-neutral-900 mb-1">
              {METHODS.find((m) => m.key === method)?.label} Inputs
            </h2>
            <p className="text-sm text-neutral-500">
              Enter the financial inputs for your valuation model.
            </p>
          </div>

          {method === "dcf" && (
            <DCFForm
              params={dcfParams}
              onChange={setDcfParams}
              suggestion={suggestion}
              onSuggest={handleSuggest}
              isSuggesting={suggestAssumptions.isPending}
            />
          )}
          {method === "comparables" && (
            <ComparableForm params={compParams} onChange={setCompParams} projectId={projectId} />
          )}
          {method === "replacement_cost" && (
            <ReplacementCostFormInner params={replParams} onChange={setReplParams} />
          )}

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
            <Button
              onClick={handleCreate}
              disabled={createValuation.isPending}
            >
              {createValuation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Calculator className="h-4 w-4 mr-2" />
              )}
              Calculate Valuation
            </Button>
          </div>
          {createValuation.isError && (
            <p className="text-sm text-red-600">
              Error: {(createValuation.error as Error).message}
            </p>
          )}
        </div>
      )}

      {/* Step 3 */}
      {step === 3 && createdValuation && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-neutral-900 mb-1">
                Valuation Results
              </h2>
              <p className="text-sm text-neutral-500">
                {methodLabel(createdValuation.method)} · v
                {createdValuation.version} ·{" "}
                <Badge variant={statusVariant(createdValuation.status)}>
                  {createdValuation.status}
                </Badge>
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setStep(1);
                setCreatedValuation(null);
                setSensitivity(null);
              }}
            >
              <Plus className="h-3 w-3 mr-1" />
              New Valuation
            </Button>
          </div>

          <ValuationResultCard
            valuation={createdValuation}
            onRunSensitivity={handleSensitivity}
            onTriggerReport={() =>
              triggerReport.mutateAsync(createdValuation.id)
            }
            sensitivity={sensitivity}
            isRunning={runSensitivity.isPending}
            isTriggering={triggerReport.isPending}
          />
        </div>
      )}
    </div>
  );
}

// ── History tab ──────────────────────────────────────────────────────────────

function HistoryTab({ projectId }: { projectId: string | null }) {
  const { data, isLoading } = useValuations(projectId ?? undefined);
  const triggerReport = useTriggerReport();

  const columns: ColumnDef<ValuationResponse>[] = [
    {
      accessorKey: "method",
      header: "Method",
      cell: ({ row }) => (
        <span className="font-medium">{methodLabel(row.original.method)}</span>
      ),
    },
    {
      accessorKey: "enterprise_value",
      header: "Enterprise Value",
      cell: ({ row }) =>
        formatEV(row.original.enterprise_value, row.original.currency),
    },
    {
      accessorKey: "equity_value",
      header: "Equity Value",
      cell: ({ row }) =>
        formatEV(row.original.equity_value, row.original.currency),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={statusVariant(row.original.status)}>
          {row.original.status}
        </Badge>
      ),
    },
    {
      accessorKey: "version",
      header: "Version",
      cell: ({ row }) => `v${row.original.version}`,
    },
    {
      accessorKey: "valued_at",
      header: "Valued At",
      cell: ({ row }) =>
        new Date(row.original.valued_at).toLocaleDateString(),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={() => triggerReport.mutateAsync(row.original.id)}
        >
          <Download className="h-3 w-3" />
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!data?.items?.length) {
    return (
      <EmptyState
        title="No valuations yet"
        description="Use the Builder tab to create your first valuation."
        icon={<TrendingUp className="h-8 w-8 text-neutral-400" />}
      />
    );
  }

  // Group by method for trend chart data
  const byMethod = data.items.reduce<Record<string, ValuationResponse[]>>(
    (acc, v) => {
      acc[v.method] = acc[v.method] ?? [];
      acc[v.method].push(v);
      return acc;
    },
    {}
  );

  return (
    <div className="space-y-6">
      {/* EV trend mini-cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        {(["dcf", "comparables", "replacement_cost", "blended"] as ValuationMethod[])
          .filter((m) => byMethod[m]?.length)
          .map((m) => {
            const latest = byMethod[m][0];
            const prev = byMethod[m][1];
            const ev = parseFloat(latest.enterprise_value);
            const prevEv = prev ? parseFloat(prev.enterprise_value) : null;
            const delta = prevEv
              ? ((ev - prevEv) / Math.abs(prevEv)) * 100
              : null;
            return (
              <Card key={m}>
                <CardContent className="pt-4 pb-4">
                  <div className="text-xs text-neutral-500 mb-1">
                    {methodLabel(m)}
                  </div>
                  <div className="text-lg font-bold text-neutral-900">
                    {formatEV(latest.enterprise_value, latest.currency)}
                  </div>
                  {delta !== null && (
                    <div
                      className={`text-xs mt-1 ${
                        delta >= 0 ? "text-green-600" : "text-red-500"
                      }`}
                    >
                      {delta >= 0 ? "+" : ""}
                      {delta.toFixed(1)}% vs prev
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
      </div>

      <DataTable
        data={data.items}
        columns={columns}
      />
    </div>
  );
}

// ── Comparison tab ────────────────────────────────────────────────────────────

function ComparisonTab() {
  const { data: all } = useValuations();
  const compare = useCompareValuations();
  const [selected, setSelected] = useState<string[]>([]);

  const items = all?.items ?? [];

  function toggleSelect(id: string) {
    setSelected((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : prev.length < 5
        ? [...prev, id]
        : prev
    );
  }

  async function handleCompare() {
    if (selected.length < 2) return;
    await compare.mutateAsync(selected);
  }

  const compared = compare.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-500">
          Select 2–5 valuations to compare side by side.
        </p>
        <Button
          onClick={handleCompare}
          disabled={selected.length < 2 || compare.isPending}
        >
          {compare.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <ArrowRightLeft className="h-4 w-4 mr-2" />
          )}
          Compare {selected.length > 0 ? `(${selected.length})` : ""}
        </Button>
      </div>

      {/* Selection list */}
      <div className="overflow-x-auto rounded-lg border border-neutral-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-neutral-50">
              <th className="w-10 px-3 py-2" />
              <th className="text-left px-3 py-2 font-medium text-neutral-600">
                Method
              </th>
              <th className="text-right px-3 py-2 font-medium text-neutral-600">
                Enterprise Value
              </th>
              <th className="text-right px-3 py-2 font-medium text-neutral-600">
                Equity Value
              </th>
              <th className="text-left px-3 py-2 font-medium text-neutral-600">
                Status
              </th>
              <th className="text-right px-3 py-2 font-medium text-neutral-600">
                Version
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((v) => (
              <tr
                key={v.id}
                className={`border-t border-neutral-100 cursor-pointer hover:bg-neutral-50 ${
                  selected.includes(v.id) ? "bg-blue-50" : ""
                }`}
                onClick={() => toggleSelect(v.id)}
              >
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selected.includes(v.id)}
                    onChange={() => toggleSelect(v.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="rounded"
                  />
                </td>
                <td className="px-3 py-2 font-medium">
                  {methodLabel(v.method)}
                </td>
                <td className="px-3 py-2 text-right">
                  {formatEV(v.enterprise_value, v.currency)}
                </td>
                <td className="px-3 py-2 text-right">
                  {formatEV(v.equity_value, v.currency)}
                </td>
                <td className="px-3 py-2">
                  <Badge variant={statusVariant(v.status)}>{v.status}</Badge>
                </td>
                <td className="px-3 py-2 text-right">v{v.version}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-3 py-8 text-center text-neutral-400"
                >
                  No valuations available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Comparison result */}
      {compared.length >= 2 && (
        <div>
          <h3 className="text-sm font-semibold text-neutral-900 mb-3">
            Side-by-Side Comparison
          </h3>
          <div className="overflow-x-auto rounded-lg border border-neutral-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-neutral-50">
                  <th className="text-left px-4 py-3 font-medium text-neutral-600">
                    Dimension
                  </th>
                  {compared.map((v) => (
                    <th
                      key={v.id}
                      className="text-right px-4 py-3 font-medium text-neutral-600"
                    >
                      {methodLabel(v.method)} v{v.version}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    label: "Enterprise Value",
                    render: (v: ValuationResponse) =>
                      formatEV(v.enterprise_value, v.currency),
                    isHighlighted: true,
                  },
                  {
                    label: "Equity Value",
                    render: (v: ValuationResponse) =>
                      formatEV(v.equity_value, v.currency),
                    isHighlighted: true,
                  },
                  {
                    label: "Status",
                    render: (v: ValuationResponse) => v.status,
                    isHighlighted: false,
                  },
                  {
                    label: "Currency",
                    render: (v: ValuationResponse) => v.currency,
                    isHighlighted: false,
                  },
                  {
                    label: "Valued At",
                    render: (v: ValuationResponse) =>
                      new Date(v.valued_at).toLocaleDateString(),
                    isHighlighted: false,
                  },
                ].map((row) => {
                  const values = compared.map((v) => row.render(v));
                  // Find best/worst for highlighted rows (parse currency values)
                  let bestIdx: number | null = null;
                  let worstIdx: number | null = null;
                  if (row.isHighlighted) {
                    const nums = compared.map((v) =>
                      parseFloat(
                        row.label === "Enterprise Value"
                          ? v.enterprise_value
                          : v.equity_value
                      )
                    );
                    bestIdx = nums.indexOf(Math.max(...nums));
                    worstIdx = nums.indexOf(Math.min(...nums));
                  }
                  return (
                    <tr key={row.label} className="border-t border-neutral-100">
                      <td className="px-4 py-3 font-medium text-neutral-700">
                        {row.label}
                      </td>
                      {values.map((val, i) => (
                        <td
                          key={i}
                          className={`px-4 py-3 text-right ${
                            bestIdx === i
                              ? "bg-green-50 text-green-800 font-semibold rounded"
                              : worstIdx === i && bestIdx !== worstIdx
                              ? "bg-red-50 text-red-700 rounded"
                              : "text-neutral-700"
                          }`}
                        >
                          {val}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ValuationsPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const { data: allValuations } = useValuations();

  // Collect unique project IDs from existing valuations for quick selection
  const knownProjectIds = [
    ...new Set(allValuations?.items.map((v) => v.project_id) ?? []),
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            Valuation Analysis
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            DCF, Comparables, Replacement Cost, and Blended valuation models
          </p>
        </div>

        {knownProjectIds.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-neutral-600">Project:</label>
            <select
              value={projectId ?? ""}
              onChange={(e) => setProjectId(e.target.value || null)}
              className="rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All projects</option>
              {knownProjectIds.map((id) => (
                <option key={id} value={id}>
                  {id.slice(0, 8)}…
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Stats bar */}
      {allValuations && allValuations.total > 0 && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-xs text-neutral-500 mb-1">
                Total Valuations
              </div>
              <div className="text-2xl font-bold">{allValuations.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-xs text-neutral-500 mb-1">Approved</div>
              <div className="text-2xl font-bold text-green-700">
                {
                  allValuations.items.filter((v) => v.status === "approved")
                    .length
                }
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-xs text-neutral-500 mb-1">In Draft</div>
              <div className="text-2xl font-bold text-amber-700">
                {
                  allValuations.items.filter((v) => v.status === "draft").length
                }
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <div className="text-xs text-neutral-500 mb-1">Projects Valued</div>
              <div className="text-2xl font-bold">
                {knownProjectIds.length}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="builder">
        <TabsList>
          <TabsTrigger value="builder">
            <Calculator className="h-4 w-4 mr-2" />
            Builder
          </TabsTrigger>
          <TabsTrigger value="history">
            <TrendingUp className="h-4 w-4 mr-2" />
            History
          </TabsTrigger>
          <TabsTrigger value="compare">
            <ArrowRightLeft className="h-4 w-4 mr-2" />
            Compare
          </TabsTrigger>
        </TabsList>

        <TabsContent value="builder" className="mt-6">
          <BuilderTab projectId={projectId} />
        </TabsContent>

        <TabsContent value="history" className="mt-6">
          <HistoryTab projectId={projectId} />
        </TabsContent>

        <TabsContent value="compare" className="mt-6">
          <ComparisonTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
