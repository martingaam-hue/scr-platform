"use client";

import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Loader2,
  Play,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  cn,
} from "@scr/ui";
import {
  useStressTestScenarios,
  useStressTests,
  useRunStressTest,
  formatCurrency,
  type StressTestResult,
  type ScenarioResponse,
} from "@/lib/stress-test";
import { usePortfolios } from "@/lib/portfolio";
import { InfoBanner } from "@/components/info-banner";

// ── Mock Data ─────────────────────────────────────────────────────────────────

const MOCK_SCENARIOS: ScenarioResponse[] = [
  {
    key: "base_case",
    name: "Base Case",
    description: "Expected market conditions with moderate energy price growth and stable interest rates. Portfolio IRR impact: neutral.",
  },
  {
    key: "combined_downturn",
    name: "Combined Downturn",
    description: "Simultaneous energy price decline of 25%, GDP contraction of 2%, and credit spread widening of 150bps.",
  },
  {
    key: "interest_rate_shock",
    name: "Interest Rate Shock +300bps",
    description: "Central bank emergency rate hike of 300bps driven by persistent inflation, increasing refinancing costs across the portfolio.",
  },
  {
    key: "energy_price_collapse",
    name: "Energy Price Collapse",
    description: "Renewable energy capture prices fall 40% due to grid saturation and subsidy removal across EU markets.",
  },
];

const MOCK_PORTFOLIO_LIST = {
  items: [{ id: "mock-portfolio-1", name: "SCR Sustainable Infrastructure Fund I" }],
  total: 1,
};

const MOCK_RESULT: StressTestResult = {
  id: "mock-result-1",
  scenario_name: "Combined Downturn",
  base_nav: 276000000,
  mean_nav: 241700000,
  var_95: 218400000,
  p5_nav: 208900000,
  p95_nav: 261200000,
  probability_of_loss: 0.12,
  max_loss_pct: 28.4,
  simulations_count: 10000,
  created_at: new Date().toISOString(),
  histogram: [12, 28, 65, 148, 312, 486, 621, 789, 932, 1048, 1124, 1087, 984, 823, 651, 498, 312, 198, 121, 74, 42, 21, 9, 4],
  histogram_edges: Array.from({ length: 24 }, (_, i) => 185000000 + i * 4000000),
  project_sensitivities: [
    { project_id: "h4", project_name: "Baltic BESS Grid Storage", stressed_value: 13800000, change_pct: -19.8 },
    { project_id: "h6", project_name: "Nordic Biomass Energy", stressed_value: 10200000, change_pct: -14.6 },
    { project_id: "h2", project_name: "Nordvik Wind Farm II", stressed_value: 31200000, change_pct: -11.2 },
    { project_id: "h7", project_name: "Thames Clean Energy Hub", stressed_value: 42400000, change_pct: -9.2 },
    { project_id: "h3", project_name: "Adriatic Infrastructure Holdings", stressed_value: 40600000, change_pct: -7.9 },
    { project_id: "h1", project_name: "Helios Solar Portfolio Iberia", stressed_value: 50800000, change_pct: -6.3 },
    { project_id: "h5", project_name: "Alpine Hydro Partners", stressed_value: 62400000, change_pct: -4.6 },
  ],
};

// ── Scenario Card ────────────────────────────────────────────────────────────

function ScenarioCard({
  scenario,
  selected,
  onSelect,
}: {
  scenario: ScenarioResponse;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        "text-left p-4 rounded-lg border-2 transition-all",
        selected
          ? "border-indigo-500 bg-indigo-50"
          : "border-gray-200 hover:border-gray-300 bg-white"
      )}
    >
      <p className={cn("font-medium text-sm", selected ? "text-indigo-700" : "text-gray-900")}>
        {scenario.name}
      </p>
      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{scenario.description}</p>
    </button>
  );
}

// ── Results Panel ─────────────────────────────────────────────────────────────

function ResultsPanel({ result }: { result: StressTestResult }) {
  const lossPct = ((result.mean_nav - result.base_nav) / result.base_nav) * 100;
  const isLoss = lossPct < 0;

  // Build a simple ASCII-style histogram from the binned data
  const maxBin = Math.max(...result.histogram);

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Base NAV", value: formatCurrency(result.base_nav) },
          { label: "Mean Stressed NAV", value: formatCurrency(result.mean_nav) },
          {
            label: "Mean Change",
            value: `${lossPct >= 0 ? "+" : ""}${lossPct.toFixed(1)}%`,
            color: isLoss ? "text-red-600" : "text-green-600",
          },
          {
            label: "VaR (95%)",
            value: formatCurrency(result.var_95),
            color: "text-orange-600",
          },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <CardContent className="p-4">
              <p className="text-xs text-gray-500">{label}</p>
              <p className={cn("text-lg font-semibold mt-0.5", color ?? "text-gray-900")}>
                {value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Additional stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
        {[
          { label: "5th Percentile NAV", value: formatCurrency(result.p5_nav) },
          { label: "95th Percentile NAV", value: formatCurrency(result.p95_nav) },
          { label: "Probability of Loss", value: `${(result.probability_of_loss * 100).toFixed(1)}%` },
          { label: "Max Loss", value: `${result.max_loss_pct.toFixed(1)}%` },
          { label: "Simulations", value: result.simulations_count.toLocaleString() },
          { label: "Scenario", value: result.scenario_name },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between items-center border rounded-lg p-3">
            <span className="text-gray-500">{label}</span>
            <span className="font-medium text-gray-900">{value}</span>
          </div>
        ))}
      </div>

      {/* Histogram */}
      {result.histogram.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">NAV Distribution (Monte Carlo)</p>
            <div className="flex items-end gap-px h-24">
              {result.histogram.map((count, i) => {
                const heightPct = maxBin > 0 ? (count / maxBin) * 100 : 0;
                const edgeMid = result.histogram_edges[i] ?? 0;
                const isVaR = edgeMid < result.p5_nav;
                return (
                  <div
                    key={i}
                    className={cn(
                      "flex-1 rounded-t-sm transition-all",
                      isVaR ? "bg-red-400" : "bg-indigo-400"
                    )}
                    style={{ height: `${heightPct}%` }}
                    title={`${formatCurrency(edgeMid)}: ${count} simulations`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>{formatCurrency(result.histogram_edges[0] ?? 0)}</span>
              <span className="text-red-500">← VaR region</span>
              <span>{formatCurrency(result.histogram_edges[result.histogram_edges.length - 1] ?? 0)}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Project sensitivities */}
      {result.project_sensitivities.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-medium text-gray-700 mb-3">Project Sensitivities</p>
            <div className="space-y-2">
              {result.project_sensitivities
                .sort((a, b) => a.change_pct - b.change_pct)
                .slice(0, 8)
                .map((p) => (
                  <div key={p.project_id} className="flex items-center gap-3 text-sm">
                    <span className="flex-1 truncate text-gray-700">{p.project_name}</span>
                    <span className="tabular-nums text-gray-500 w-24 text-right">
                      {formatCurrency(p.stressed_value)}
                    </span>
                    <span
                      className={cn(
                        "tabular-nums font-medium w-16 text-right",
                        p.change_pct < 0 ? "text-red-600" : "text-green-600"
                      )}
                    >
                      {p.change_pct >= 0 ? "+" : ""}
                      {p.change_pct.toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function StressTestPage() {
  const [selectedScenario, setSelectedScenario] = useState<string>("combined_downturn");
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>("");
  const [activeResult, setActiveResult] = useState<StressTestResult | null>(null);

  const { data: apiScenarios, isLoading: loadingScenarios } = useStressTestScenarios();
  const { data: apiPortfolios } = usePortfolios();
  const { data: history } = useStressTests(selectedPortfolio);
  const { mutate: runTest, isPending: running } = useRunStressTest();

  const scenarios = apiScenarios ?? MOCK_SCENARIOS;
  const portfolios = { items: apiPortfolios?.items?.length ? apiPortfolios.items : MOCK_PORTFOLIO_LIST.items };

  const portfolioList = portfolios.items ?? [];

  const handleRun = () => {
    if (!selectedPortfolio) return;
    runTest(
      { portfolio_id: selectedPortfolio, scenario_key: selectedScenario },
      { onSuccess: (result) => setActiveResult(result) }
    );
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Portfolio Stress Test</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Monte Carlo simulation — {(10000).toLocaleString()} scenarios per run
          </p>
        </div>
        {activeResult && (
          <Badge variant="info">
            Last run: {new Date(activeResult.created_at).toLocaleTimeString()}
          </Badge>
        )}
      </div>

      <InfoBanner>
        <strong>Portfolio Stress Test</strong> runs Monte Carlo simulations across 10,000 scenarios to model
        how your portfolio performs under adverse market conditions. Adjust input parameters, select stress
        scenarios, and analyse NAV, IRR, and loss distributions under tail-risk events.
      </InfoBanner>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="space-y-4">
          {/* Portfolio selector */}
          <Card>
            <CardContent className="p-4 space-y-3">
              <p className="text-sm font-medium text-gray-700">Portfolio</p>
              {portfolioList.length === 0 ? (
                <p className="text-sm text-gray-400">No portfolios found</p>
              ) : (
                <select
                  value={selectedPortfolio}
                  onChange={(e) => setSelectedPortfolio(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Select portfolio…</option>
                  {portfolioList.map((p: { id: string; name: string }) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              )}
            </CardContent>
          </Card>

          {/* Scenario selector */}
          <Card>
            <CardContent className="p-4 space-y-3">
              <p className="text-sm font-medium text-gray-700">Scenario</p>
              {loadingScenarios ? (
                <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
              ) : (
                <div className="grid grid-cols-1 gap-2">
                  {(scenarios ?? []).map((s) => (
                    <ScenarioCard
                      key={s.key}
                      scenario={s}
                      selected={selectedScenario === s.key}
                      onSelect={() => setSelectedScenario(s.key)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Button
            className="w-full"
            onClick={handleRun}
            disabled={running || !selectedPortfolio}
          >
            {running ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Running…
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Stress Test
              </>
            )}
          </Button>

          {!selectedPortfolio && (
            <p className="text-xs text-amber-600 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Select a portfolio to run
            </p>
          )}
        </div>

        {/* Results */}
        <div className="lg:col-span-2">
          {running && (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <Activity className="h-8 w-8 text-indigo-400 animate-pulse" />
              <p className="text-sm text-gray-500">Running Monte Carlo simulation…</p>
            </div>
          )}
          {!running && (activeResult ?? MOCK_RESULT) && <ResultsPanel result={activeResult ?? MOCK_RESULT} />}
          {!running && false && (
            <div className="space-y-4">
              <EmptyState
                title="No result yet"
                description="Select a portfolio and scenario, then click Run Stress Test."
              />
              {(history?.items?.length ?? 0) > 0 && (
                <Card>
                  <CardContent className="p-4">
                    <p className="text-sm font-medium text-gray-700 mb-3">Recent Runs</p>
                    <div className="space-y-2">
                      {history!.items.slice(0, 5).map((r) => (
                        <button
                          key={r.id}
                          onClick={() => setActiveResult(r)}
                          className="w-full text-left flex items-center justify-between text-sm hover:bg-gray-50 p-2 rounded"
                        >
                          <span className="text-gray-700">{r.scenario_name}</span>
                          <span className="text-gray-400 text-xs">
                            {new Date(r.created_at).toLocaleDateString()}
                          </span>
                        </button>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
