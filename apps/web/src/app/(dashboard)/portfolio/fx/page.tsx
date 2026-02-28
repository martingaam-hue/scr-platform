"use client"

import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { RefreshCw, TrendingUp, AlertTriangle } from "lucide-react"

const CURRENCY_COLORS: Record<string, string> = {
  EUR: "#4F46E5",
  USD: "#10B981",
  GBP: "#F59E0B",
  CHF: "#EF4444",
  SEK: "#8B5CF6",
  NOK: "#06B6D4",
  DKK: "#84CC16",
  JPY: "#F97316",
  AUD: "#EC4899",
  CAD: "#6B7280",
}

interface ExposureItem {
  currency: string
  value_eur: number
  pct: number
  project_count: number
}

interface FXRate {
  currency: string
  rate: number
}

function formatEur(value: number): string {
  if (value >= 1_000_000) return `€${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `€${(value / 1_000).toFixed(0)}k`
  return `€${value.toFixed(0)}`
}

export default function FXDashboardPage() {
  const [baseCurrency, setBaseCurrency] = useState("EUR")

  const { data: exposure, isLoading: loadingExposure } = useQuery({
    queryKey: ["fx-exposure", baseCurrency],
    queryFn: () => api.get(`/fx/exposure?base_currency=${baseCurrency}`).then((r) => r.data),
  })

  const { data: ratesData, isLoading: loadingRates } = useQuery({
    queryKey: ["fx-rates-latest"],
    queryFn: () => api.get("/fx/rates/latest").then((r) => r.data),
  })

  const refreshMutation = useMutation({
    mutationFn: () => api.post("/fx/rates/refresh").then((r) => r.data),
  })

  const exposureItems: ExposureItem[] = exposure?.exposure ?? []
  const totalValue: number = exposure?.total_value_base ?? 0
  const recommendation: string = exposure?.hedging_recommendation ?? ""
  const rateDate: string = ratesData?.rate_date ?? "—"
  const rates: Record<string, number> = ratesData?.rates ?? {}

  const pieData = exposureItems.map((e) => ({
    name: e.currency,
    value: e.pct,
    value_eur: e.value_eur,
  }))

  const ratesList: FXRate[] = Object.entries(rates)
    .filter(([c]) => c !== "EUR")
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([currency, rate]) => ({ currency, rate }))

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">FX Exposure</h1>
          <p className="text-sm text-gray-500 mt-1">Portfolio currency breakdown · Rates as of {rateDate}</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Base currency toggle */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            {["EUR", "USD", "GBP"].map((c) => (
              <button
                key={c}
                onClick={() => setBaseCurrency(c)}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${baseCurrency === c ? "bg-primary-600 text-white" : "bg-white text-gray-700 hover:bg-gray-50"}`}
              >
                {c}
              </button>
            ))}
          </div>
          <button
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
            Refresh Rates
          </button>
        </div>
      </div>

      {/* Hedging recommendation */}
      {recommendation && (
        <div className={`flex items-start gap-3 p-4 rounded-xl border ${recommendation.includes("High concentration") ? "bg-yellow-50 border-yellow-200" : "bg-green-50 border-green-200"}`}>
          {recommendation.includes("High concentration")
            ? <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            : <TrendingUp className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
          }
          <p className={`text-sm ${recommendation.includes("High concentration") ? "text-yellow-800" : "text-green-800"}`}>
            {recommendation}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Exposure Pie Chart */}
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="font-semibold text-gray-900 mb-1">Currency Exposure</h2>
          <p className="text-sm text-gray-500 mb-4">Portfolio NAV {formatEur(totalValue)} total</p>
          {loadingExposure ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-600 border-t-transparent" />
            </div>
          ) : pieData.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-gray-400">No data</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" outerRadius={100} dataKey="value" nameKey="name" label={({ name, value }: { name: string; value: number }) => `${name} ${value.toFixed(1)}%`}>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={CURRENCY_COLORS[entry.name] ?? "#94A3B8"} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Exposure Table */}
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Breakdown by Currency</h2>
          <table className="w-full text-sm">
            <thead className="text-xs uppercase text-gray-500 border-b border-gray-100">
              <tr>
                <th className="pb-3 text-left">Currency</th>
                <th className="pb-3 text-right">Value (EUR)</th>
                <th className="pb-3 text-right">% Portfolio</th>
                <th className="pb-3 text-right">Projects</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {exposureItems.map((item) => (
                <tr key={item.currency} className="hover:bg-gray-50">
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-3 w-3 rounded-full" style={{ backgroundColor: CURRENCY_COLORS[item.currency] ?? "#94A3B8" }} />
                      <span className="font-medium text-gray-900">{item.currency}</span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-gray-700">{formatEur(item.value_eur)}</td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${item.pct}%`, backgroundColor: CURRENCY_COLORS[item.currency] ?? "#94A3B8" }} />
                      </div>
                      <span className="text-gray-700 w-10 text-right">{item.pct.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="py-3 text-right text-gray-700">{item.project_count}</td>
                </tr>
              ))}
              {exposureItems.length === 0 && !loadingExposure && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-gray-400">No portfolio data available</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* FX Rates table */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">ECB Reference Rates</h2>
          <span className="text-sm text-gray-500">Base: EUR · As of {rateDate}</span>
        </div>
        {loadingRates ? (
          <div className="text-center py-4 text-gray-400">Loading rates…</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {ratesList.map((rate) => (
              <div key={rate.currency} className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
                <p className="text-xs font-medium text-gray-500 uppercase">{rate.currency}</p>
                <p className="text-lg font-bold text-gray-900 mt-0.5">{rate.rate.toFixed(4)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
