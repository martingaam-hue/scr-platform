"use client"

import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { formatCurrency, formatPct } from "@/lib/format"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from "recharts"
import { TrendingDown, AlertTriangle, Activity, Play, ChevronDown, Info } from "lucide-react"

interface Scenario {
  key: string
  name: string
  description: string
  params: Record<string, number>
}

interface StressResult {
  id: string
  scenario_key: string
  scenario_name: string
  parameters: Record<string, number>
  simulations_count: number
  base_nav: number
  mean_nav: number
  median_nav: number
  p5_nav: number
  p95_nav: number
  var_95: number
  max_loss_pct: number
  probability_of_loss: number
  histogram: number[]
  histogram_edges: number[]
  project_sensitivities: { project_id: string; project_name: string; base_value: number; stressed_value: number; change_pct: number }[]
}

export default function StressTestPage() {
  const [portfolioId, setPortfolioId] = useState("")
  const [selectedScenario, setSelectedScenario] = useState("combined_downturn")
  const [simulations, setSimulations] = useState(10000)
  const [result, setResult] = useState<StressResult | null>(null)

  const { data: scenariosData } = useQuery<Scenario[]>({
    queryKey: ["stress-scenarios"],
    queryFn: () => api.get("/stress-test/scenarios").then(r => r.data),
  })

  const runMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/stress-test/run", body).then(r => r.data),
    onSuccess: (data) => setResult(data),
  })

  const scenarios = scenariosData ?? []
  const activeScenario = scenarios.find(s => s.key === selectedScenario)

  // Build histogram data for recharts
  const histogramData = result?.histogram.map((count, i) => ({
    nav: result.histogram_edges[i],
    count,
    isLoss: result.histogram_edges[i] < result.base_nav,
  })) ?? []

  const lossChange = result ? ((result.mean_nav - result.base_nav) / result.base_nav * 100) : 0

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Portfolio Stress Testing</h1>
        <p className="text-sm text-gray-500 mt-1">Monte Carlo simulation · {simulations.toLocaleString()} simulations per run</p>
      </div>

      {/* Configuration panel */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-5">
        <h2 className="font-semibold text-gray-900">Configure Simulation</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Portfolio ID</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="Paste portfolio UUID…"
              value={portfolioId}
              onChange={e => setPortfolioId(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Simulations</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={simulations}
              onChange={e => setSimulations(Number(e.target.value))}
            >
              <option value={1000}>1,000 (fast)</option>
              <option value={10000}>10,000 (standard)</option>
              <option value={50000}>50,000 (precise)</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => runMutation.mutate({ portfolio_id: portfolioId, scenario_key: selectedScenario, simulations })}
              disabled={!portfolioId || runMutation.isPending}
              className="w-full flex items-center justify-center gap-2 bg-primary-600 text-white py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
            >
              <Play className="h-4 w-4" />
              {runMutation.isPending ? `Running ${simulations.toLocaleString()} simulations…` : "Run Simulation"}
            </button>
          </div>
        </div>

        {/* Scenario selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Scenario</label>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {scenarios.map(s => (
              <button
                key={s.key}
                onClick={() => setSelectedScenario(s.key)}
                className={`p-3 rounded-lg border text-left transition-colors ${selectedScenario === s.key ? "bg-primary-50 border-primary-300 text-primary-900" : "border-gray-200 text-gray-700 hover:bg-gray-50"}`}
              >
                <p className="text-xs font-semibold">{s.name}</p>
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{s.description}</p>
              </button>
            ))}
          </div>
          {activeScenario && (
            <div className="mt-2 flex gap-3 text-xs text-gray-500">
              <Info className="h-4 w-4 flex-shrink-0 text-blue-400 mt-0.5" />
              <span>{activeScenario.description}</span>
            </div>
          )}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* KPI cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Base NAV", value: formatCurrency(result.base_nav), color: "text-gray-900" },
              { label: "Stressed Mean NAV", value: formatCurrency(result.mean_nav), color: lossChange < 0 ? "text-red-600" : "text-green-600" },
              { label: "VaR (95%)", value: formatCurrency(result.var_95), color: "text-red-600" },
              { label: "Prob. of Loss", value: formatPct(result.probability_of_loss * 100, 1), color: "text-orange-600" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="text-xs text-gray-500">{label}</p>
                <p className={`text-2xl font-bold mt-0.5 ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* Range bar */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="font-semibold text-gray-900 mb-1">Outcome Range</h3>
            <p className="text-sm text-gray-500 mb-4">
              Scenario: <strong>{result.scenario_name}</strong> · {result.simulations_count.toLocaleString()} simulations
            </p>
            <div className="flex items-center gap-3 text-sm mb-2">
              <span className="text-gray-500">P5: {formatCurrency(result.p5_nav)}</span>
              <span className="text-gray-500 flex-1 text-center">Median: {formatCurrency(result.median_nav)}</span>
              <span className="text-gray-500">P95: {formatCurrency(result.p95_nav)}</span>
            </div>
            <div className="relative h-8 bg-gray-100 rounded-full overflow-hidden">
              {/* Loss zone */}
              <div className="absolute inset-y-0 left-0 bg-red-200" style={{ width: `${Math.max(0, (result.base_nav - result.p5_nav) / (result.p95_nav - result.p5_nav) * 100)}%` }} />
              {/* Base NAV marker */}
              <div className="absolute inset-y-0 w-0.5 bg-gray-700" style={{ left: `${(result.base_nav - result.p5_nav) / (result.p95_nav - result.p5_nav) * 100}%` }} />
              {/* Gain zone */}
              <div className="absolute inset-y-0 right-0 bg-green-200" style={{ width: `${Math.max(0, (result.p95_nav - result.base_nav) / (result.p95_nav - result.p5_nav) * 100)}%` }} />
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>{formatCurrency(result.p5_nav)}</span>
              <span className="font-medium text-gray-700">Base: {formatCurrency(result.base_nav)}</span>
              <span>{formatCurrency(result.p95_nav)}</span>
            </div>
          </div>

          {/* Histogram */}
          {histogramData.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="font-semibold text-gray-900 mb-4">NAV Distribution</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={histogramData} barCategoryGap="1%">
                  <XAxis dataKey="nav" hide />
                  <YAxis hide />
                  <Tooltip formatter={(v: number) => [v.toLocaleString(), "simulations"]} labelFormatter={(l: number) => `NAV: ${formatCurrency(l)}`} />
                  <ReferenceLine x={result.base_nav} stroke="#6B7280" strokeDasharray="4 2" label={{ value: "Base", position: "top", fontSize: 10 }} />
                  <Bar dataKey="count">
                    {histogramData.map((entry, i) => (
                      <Cell key={i} fill={entry.isLoss ? "#FCA5A5" : "#86EFAC"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="h-3 w-3 rounded bg-red-300 inline-block" /> Loss scenarios</span>
                <span className="flex items-center gap-1"><span className="h-3 w-3 rounded bg-green-300 inline-block" /> Gain scenarios</span>
              </div>
            </div>
          )}

          {/* Per-project sensitivity */}
          {result.project_sensitivities.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Project Sensitivity</h3>
              <table className="w-full text-sm">
                <thead className="text-xs uppercase text-gray-500 border-b">
                  <tr>
                    <th className="pb-3 text-left">Project</th>
                    <th className="pb-3 text-right">Base Value</th>
                    <th className="pb-3 text-right">Stressed Value</th>
                    <th className="pb-3 text-right">Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {result.project_sensitivities.map(p => (
                    <tr key={p.project_id} className="hover:bg-gray-50">
                      <td className="py-3 font-medium text-gray-900">{p.project_name}</td>
                      <td className="py-3 text-right text-gray-700">{formatCurrency(p.base_value)}</td>
                      <td className="py-3 text-right text-gray-700">{formatCurrency(p.stressed_value)}</td>
                      <td className={`py-3 text-right font-medium ${p.change_pct < 0 ? "text-red-600" : "text-green-600"}`}>
                        {p.change_pct > 0 ? "+" : ""}{p.change_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
