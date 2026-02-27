"use client";

import { useState } from "react";
import {
  Calculator,
  Plus,
  TrendingUp,
  Users,
  DollarSign,
  BarChart3,
  ArrowRightLeft,
  ChevronDown,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import {
  useEquityScenarios,
  useCreateScenario,
  useCompareScenarios,
  securityTypeLabel,
  formatCurrency,
  moicColor,
  type CreateScenarioRequest,
  type EquityScenario,
} from "@/lib/equity-calculator";

// ── New Scenario Form ─────────────────────────────────────────────────────

interface ScenarioFormProps {
  onSubmit: (data: CreateScenarioRequest) => void;
  isLoading: boolean;
  onCancel: () => void;
}

function ScenarioForm({ onSubmit, isLoading, onCancel }: ScenarioFormProps) {
  const [form, setForm] = useState<CreateScenarioRequest>({
    scenario_name: "",
    pre_money_valuation: 5_000_000,
    investment_amount: 1_000_000,
    security_type: "common_equity",
    shares_outstanding_before: 1_000_000,
    anti_dilution_type: "none",
  });

  const set = (key: keyof CreateScenarioRequest, value: unknown) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Scenario Name *
        </label>
        <input
          type="text"
          required
          value={form.scenario_name}
          onChange={(e) => set("scenario_name", e.target.value)}
          placeholder="e.g. Series A — Base Case"
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Pre-money Valuation ($)
          </label>
          <input
            type="number"
            required
            min={1}
            value={form.pre_money_valuation}
            onChange={(e) => set("pre_money_valuation", Number(e.target.value))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Investment Amount ($)
          </label>
          <input
            type="number"
            required
            min={1}
            value={form.investment_amount}
            onChange={(e) => set("investment_amount", Number(e.target.value))}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Security Type
        </label>
        <select
          value={form.security_type}
          onChange={(e) => set("security_type", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="common_equity">Common Equity</option>
          <option value="preferred_equity">Preferred Equity</option>
          <option value="convertible_note">Convertible Note</option>
          <option value="safe">SAFE</option>
          <option value="revenue_share">Revenue Share</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Shares Outstanding Before Investment
        </label>
        <input
          type="number"
          required
          min={1}
          value={form.shares_outstanding_before}
          onChange={(e) =>
            set("shares_outstanding_before", Number(e.target.value))
          }
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {form.security_type === "preferred_equity" && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Liquidation Preference ($)
            </label>
            <input
              type="number"
              min={0}
              value={form.liquidation_preference ?? ""}
              onChange={(e) =>
                set(
                  "liquidation_preference",
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              placeholder="Optional"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Participation Cap ($)
            </label>
            <input
              type="number"
              min={0}
              value={form.participation_cap ?? ""}
              onChange={(e) =>
                set(
                  "participation_cap",
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              placeholder="Optional"
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Anti-dilution Protection
        </label>
        <select
          value={form.anti_dilution_type}
          onChange={(e) => set("anti_dilution_type", e.target.value)}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="none">None</option>
          <option value="broad_based">Broad-Based Weighted Average</option>
          <option value="narrow_based">Narrow-Based Weighted Average</option>
          <option value="full_ratchet">Full Ratchet</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description (optional)
        </label>
        <textarea
          value={form.description ?? ""}
          onChange={(e) =>
            set("description", e.target.value || undefined)
          }
          rows={2}
          placeholder="Notes about this scenario..."
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div className="flex gap-2 pt-2">
        <Button type="submit" disabled={isLoading} className="flex-1">
          {isLoading ? "Calculating..." : "Calculate Scenario"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isLoading}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ── Scenario Results Panel ────────────────────────────────────────────────

function ScenarioResults({ scenario }: { scenario: EquityScenario }) {
  return (
    <div className="space-y-6">
      {/* KPI chips */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="text-xs text-blue-600 font-medium mb-1">
            Equity %
          </div>
          <div className="text-2xl font-bold text-blue-700">
            {scenario.equity_percentage.toFixed(2)}%
          </div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="text-xs text-green-600 font-medium mb-1">
            Post-money Valuation
          </div>
          <div className="text-xl font-bold text-green-700">
            {formatCurrency(scenario.post_money_valuation)}
          </div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
          <div className="text-xs text-purple-600 font-medium mb-1">
            Price per Share
          </div>
          <div className="text-xl font-bold text-purple-700">
            ${scenario.price_per_share.toFixed(4)}
          </div>
        </div>
      </div>

      {/* Cap Table */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <Users className="h-4 w-4" />
          Cap Table
        </h3>
        <div className="space-y-2">
          {scenario.cap_table.map((entry) => (
            <div key={entry.name} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-gray-700">{entry.name}</span>
                <span className="text-gray-500">
                  {entry.percentage.toFixed(2)}%
                  {entry.investment != null && (
                    <span className="ml-2 text-gray-400">
                      ({formatCurrency(entry.investment)})
                    </span>
                  )}
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-100">
                <div
                  className={`h-2 rounded-full ${
                    entry.name === "New Investor"
                      ? "bg-blue-500"
                      : "bg-gray-400"
                  }`}
                  style={{ width: `${entry.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-2 text-xs text-gray-500">
          Total shares issued: {scenario.new_shares_issued.toLocaleString()} /{" "}
          {(
            scenario.shares_outstanding_before + scenario.new_shares_issued
          ).toLocaleString()}{" "}
          total
        </div>
      </div>

      {/* Waterfall Table */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" />
          Exit Waterfall
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-3 text-gray-500 font-medium">
                  Multiple
                </th>
                <th className="text-right py-2 px-3 text-gray-500 font-medium">
                  Exit Value
                </th>
                <th className="text-right py-2 px-3 text-gray-500 font-medium">
                  Investor Proceeds
                </th>
                <th className="text-right py-2 pl-3 text-gray-500 font-medium">
                  MOIC
                </th>
              </tr>
            </thead>
            <tbody>
              {scenario.waterfall.map((row) => (
                <tr
                  key={row.multiple}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="py-2 pr-3 font-medium text-gray-700">
                    {row.multiple}x
                  </td>
                  <td className="py-2 px-3 text-right text-gray-600">
                    {formatCurrency(row.exit_value)}
                  </td>
                  <td className="py-2 px-3 text-right text-gray-600">
                    {formatCurrency(row.investor_proceeds)}
                  </td>
                  <td
                    className={`py-2 pl-3 text-right font-semibold ${moicColor(
                      row.investor_moic
                    )}`}
                  >
                    {row.investor_moic.toFixed(2)}x
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Saved Scenarios List ──────────────────────────────────────────────────

function ScenarioCard({
  scenario,
  selected,
  onToggleSelect,
  onClick,
}: {
  scenario: EquityScenario;
  selected: boolean;
  onToggleSelect: (id: string) => void;
  onClick: (s: EquityScenario) => void;
}) {
  return (
    <div
      className={`rounded-lg border p-4 cursor-pointer transition-colors ${
        selected
          ? "border-blue-500 bg-blue-50"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
      onClick={() => onClick(scenario)}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => {
                e.stopPropagation();
                onToggleSelect(scenario.id);
              }}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
              onClick={(e) => e.stopPropagation()}
            />
            <span className="font-medium text-gray-900 text-sm">
              {scenario.scenario_name}
            </span>
          </div>
          <div className="mt-1 ml-6 flex flex-wrap gap-2 text-xs text-gray-500">
            <span>{securityTypeLabel(scenario.security_type)}</span>
            <span>·</span>
            <span>{formatCurrency(scenario.pre_money_valuation)} pre-money</span>
            <span>·</span>
            <span>{formatCurrency(scenario.investment_amount)} invested</span>
          </div>
        </div>
        <div className="text-right ml-4">
          <div className="text-lg font-bold text-blue-700">
            {scenario.equity_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-400">equity</div>
        </div>
      </div>
    </div>
  );
}

// ── Compare Panel ─────────────────────────────────────────────────────────

function ComparePanel({
  scenarios,
  selectedIds,
}: {
  scenarios: EquityScenario[];
  selectedIds: string[];
}) {
  const selected = scenarios.filter((s) => selectedIds.includes(s.id));
  const { mutate: compare, data: compareData, isPending } = useCompareScenarios();

  if (selected.length < 2) {
    return (
      <div className="text-sm text-gray-500 text-center py-4">
        Select 2–5 scenarios to compare
      </div>
    );
  }

  const handleCompare = () => {
    compare({ scenario_ids: selectedIds });
  };

  return (
    <div className="space-y-4">
      <Button
        onClick={handleCompare}
        disabled={isPending}
        variant="outline"
        className="w-full"
      >
        <ArrowRightLeft className="h-4 w-4 mr-2" />
        {isPending ? "Comparing..." : `Compare ${selected.length} Scenarios`}
      </Button>

      {compareData && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-3 text-gray-500 font-medium">
                  Dimension
                </th>
                {compareData.scenarios.map((s) => (
                  <th
                    key={String(s.id)}
                    className="text-right py-2 px-2 text-gray-500 font-medium"
                  >
                    {String(s.scenario_name)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {compareData.dimensions.map((dim) => (
                <tr key={dim} className="border-b border-gray-100">
                  <td className="py-2 pr-3 text-gray-600 font-medium">{dim}</td>
                  {compareData.scenarios.map((s) => {
                    const val = s[dim];
                    const numVal = typeof val === "number" ? val : null;
                    return (
                      <td
                        key={String(s.id)}
                        className="py-2 px-2 text-right text-gray-700"
                      >
                        {numVal != null
                          ? dim.includes("%")
                            ? `${numVal.toFixed(2)}%`
                            : dim.includes("Proceeds") ||
                              dim.includes("Valuation") ||
                              dim.includes("Amount")
                            ? formatCurrency(numVal)
                            : dim.includes("Share")
                            ? `$${numVal.toFixed(4)}`
                            : `${numVal.toFixed(2)}%`
                          : String(val ?? "—")}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function EquityCalculatorPage() {
  const [showForm, setShowForm] = useState(false);
  const [activeScenario, setActiveScenario] = useState<EquityScenario | null>(
    null
  );
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: scenarios, isLoading: scenariosLoading } = useEquityScenarios();
  const { mutate: createScenario, isPending: creating } = useCreateScenario();

  const handleCreate = (data: CreateScenarioRequest) => {
    createScenario(data, {
      onSuccess: (result) => {
        setActiveScenario(result);
        setShowForm(false);
      },
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id].slice(0, 5)
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Calculator className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Equity Calculator
            </h1>
            <p className="text-sm text-gray-500">
              Model equity scenarios with real-time dilution and waterfall
              analysis
            </p>
          </div>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Scenario
          </Button>
        )}
      </div>

      {/* Main content: form + results */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Form */}
        {showForm && (
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">New Scenario</CardTitle>
              </CardHeader>
              <CardContent>
                <ScenarioForm
                  onSubmit={handleCreate}
                  isLoading={creating}
                  onCancel={() => setShowForm(false)}
                />
              </CardContent>
            </Card>
          </div>
        )}

        {/* Right: Results */}
        {activeScenario && (
          <div className={showForm ? "lg:col-span-3" : "lg:col-span-5"}>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-blue-600" />
                    {activeScenario.scenario_name}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="neutral">
                      {securityTypeLabel(activeScenario.security_type)}
                    </Badge>
                    {activeScenario.anti_dilution_type &&
                      activeScenario.anti_dilution_type !== "none" && (
                        <Badge variant="info">Anti-dilution</Badge>
                      )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ScenarioResults scenario={activeScenario} />
              </CardContent>
            </Card>
          </div>
        )}

        {/* Empty state when no form and no active scenario */}
        {!showForm && !activeScenario && (
          <div className="lg:col-span-5">
            <EmptyState
              icon={<Calculator className="h-8 w-8 text-gray-400" />}
              title="No scenario selected"
              description="Create a new scenario or select one from your saved scenarios below."
              action={
                <Button onClick={() => setShowForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  New Scenario
                </Button>
              }
            />
          </div>
        )}
      </div>

      {/* Saved Scenarios + Compare */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            Saved Scenarios
          </h2>
          {selectedIds.length >= 2 && (
            <Badge variant="neutral">
              {selectedIds.length} selected
            </Badge>
          )}
        </div>

        {scenariosLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 rounded-lg bg-gray-100 animate-pulse"
              />
            ))}
          </div>
        ) : !scenarios || scenarios.length === 0 ? (
          <div className="text-sm text-gray-500 py-4">
            No saved scenarios yet. Create your first scenario above.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {scenarios.map((s) => (
              <ScenarioCard
                key={s.id}
                scenario={s}
                selected={selectedIds.includes(s.id)}
                onToggleSelect={toggleSelect}
                onClick={setActiveScenario}
              />
            ))}
          </div>
        )}

        {/* Compare Panel */}
        {selectedIds.length >= 2 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <ArrowRightLeft className="h-4 w-4" />
                Scenario Comparison
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ComparePanel
                scenarios={scenarios ?? []}
                selectedIds={selectedIds}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
