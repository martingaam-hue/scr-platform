"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { formatDate, formatCurrency, formatPct } from "@/lib/format"
import { CheckCircle, Clock, FileText, Plus, Download, ChevronRight } from "lucide-react"
import { AIFeedback } from "@/components/ai-feedback"

interface LPReport {
  id: string
  report_period: string
  period_start: string
  period_end: string
  status: string
  gross_irr: number | null
  net_irr: number | null
  tvpi: number | null
  dpi: number | null
  rvpi: number | null
  moic: number | null
  total_committed: number | null
  total_invested: number | null
  total_returned: number | null
  total_nav: number | null
  narrative: {
    executive_summary?: string
    portfolio_commentary?: string
    market_outlook?: string
    esg_highlights?: string
  } | null
  investments_data: Record<string, unknown>[] | null
  pdf_s3_key: string | null
  created_at: string
  updated_at: string
  download_url?: string | null
}

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  review: "bg-yellow-100 text-yellow-700",
  approved: "bg-green-100 text-green-700",
  distributed: "bg-blue-100 text-blue-700",
}

function MetricCard({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value ?? "—"}</p>
    </div>
  )
}

function ReportRow({ report, onSelect }: { report: LPReport; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="w-full flex items-center justify-between px-4 py-3 rounded-lg border border-gray-200 bg-white hover:border-primary-300 hover:bg-primary-50 transition-colors text-left"
    >
      <div>
        <p className="font-semibold text-gray-900">{report.report_period}</p>
        <p className="text-sm text-gray-500">
          {formatDate(report.period_start)} – {formatDate(report.period_end)}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_STYLES[report.status] ?? "bg-gray-100 text-gray-600"}`}>
          {report.status}
        </span>
        <ChevronRight className="h-4 w-4 text-gray-400" />
      </div>
    </button>
  )
}

export default function LPReportsPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showNewForm, setShowNewForm] = useState(false)
  const [newPeriod, setNewPeriod] = useState({ report_period: "", period_start: "", period_end: "" })

  const { data: listData, isLoading } = useQuery({
    queryKey: ["lp-reports"],
    queryFn: () => api.get("/lp-reports").then((r) => r.data),
  })

  const { data: report } = useQuery({
    queryKey: ["lp-report", selectedId],
    queryFn: () => api.get(`/lp-reports/${selectedId}`).then((r) => r.data),
    enabled: !!selectedId,
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/lp-reports", body).then((r) => r.data),
    onSuccess: (data: LPReport) => {
      queryClient.invalidateQueries({ queryKey: ["lp-reports"] })
      setSelectedId(data.id)
      setShowNewForm(false)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/lp-reports/${id}/approve`).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lp-report", selectedId] }),
  })

  const generatePdfMutation = useMutation({
    mutationFn: (id: string) => api.post(`/lp-reports/${id}/generate-pdf`).then((r) => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["lp-report", selectedId] }),
  })

  const reports: LPReport[] = listData?.items ?? []

  return (
    <div className="flex h-full min-h-screen">
      {/* Sidebar — report list */}
      <aside className="w-72 border-r border-gray-200 bg-gray-50 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">LP Reports</h2>
          <button
            onClick={() => setShowNewForm(true)}
            className="flex items-center gap-1 px-2 py-1 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700"
          >
            <Plus className="h-3.5 w-3.5" />
            New
          </button>
        </div>

        {showNewForm && (
          <div className="p-4 border-b border-gray-200 space-y-3">
            <input
              className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
              placeholder="Period e.g. Q1 2025"
              value={newPeriod.report_period}
              onChange={(e) => setNewPeriod((p) => ({ ...p, report_period: e.target.value }))}
            />
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-500">Start</label>
                <input
                  type="date"
                  className="w-full border border-gray-300 rounded-md px-2 py-1 text-sm"
                  value={newPeriod.period_start}
                  onChange={(e) => setNewPeriod((p) => ({ ...p, period_start: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">End</label>
                <input
                  type="date"
                  className="w-full border border-gray-300 rounded-md px-2 py-1 text-sm"
                  value={newPeriod.period_end}
                  onChange={(e) => setNewPeriod((p) => ({ ...p, period_end: e.target.value }))}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => createMutation.mutate({ ...newPeriod, cash_flows: [], investments_data: [] })}
                disabled={createMutation.isPending}
                className="flex-1 bg-primary-600 text-white text-sm py-1.5 rounded-md hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Generating…" : "Generate"}
              </button>
              <button onClick={() => setShowNewForm(false)} className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-100">
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {isLoading && <p className="text-sm text-gray-500">Loading…</p>}
          {reports.map((r) => (
            <ReportRow key={r.id} report={r} onSelect={() => setSelectedId(r.id)} />
          ))}
          {!isLoading && reports.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-8">No reports yet. Create one to get started.</p>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        {!report ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <FileText className="h-12 w-12 text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-700">Select a report</h3>
            <p className="text-sm text-gray-500 mt-1">Choose a report from the sidebar or create a new one.</p>
          </div>
        ) : (
          <div className="max-w-4xl space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{report.report_period} — LP Report</h1>
                <p className="text-sm text-gray-500 mt-1">
                  {formatDate(report.period_start)} – {formatDate(report.period_end)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${STATUS_STYLES[report.status] ?? ""}`}>
                  {report.status}
                </span>
                {report.status === "draft" && (
                  <button
                    onClick={() => approveMutation.mutate(report.id)}
                    disabled={approveMutation.isPending}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    <CheckCircle className="h-4 w-4" />
                    Approve
                  </button>
                )}
                <button
                  onClick={() =>
                    report.download_url
                      ? window.open(report.download_url)
                      : generatePdfMutation.mutate(report.id)
                  }
                  disabled={generatePdfMutation.isPending}
                  className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700 disabled:opacity-50"
                >
                  <Download className="h-4 w-4" />
                  {generatePdfMutation.isPending ? "Generating…" : report.download_url ? "Download" : "Generate PDF"}
                </button>
              </div>
            </div>

            {/* Performance metrics */}
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Fund Performance</h2>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                <MetricCard label="Gross IRR" value={report.gross_irr != null ? formatPct(report.gross_irr) : null} />
                <MetricCard label="Net IRR" value={report.net_irr != null ? formatPct(report.net_irr) : null} />
                <MetricCard label="TVPI" value={report.tvpi != null ? `${report.tvpi.toFixed(2)}x` : null} />
                <MetricCard label="DPI" value={report.dpi != null ? `${report.dpi.toFixed(2)}x` : null} />
                <MetricCard label="RVPI" value={report.rvpi != null ? `${report.rvpi.toFixed(2)}x` : null} />
                <MetricCard label="MOIC" value={report.moic != null ? `${report.moic.toFixed(2)}x` : null} />
                <MetricCard label="Total Invested" value={report.total_invested != null ? formatCurrency(report.total_invested) : null} />
                <MetricCard label="Total NAV" value={report.total_nav != null ? formatCurrency(report.total_nav) : null} />
              </div>
            </section>

            {/* Narrative */}
            {report.narrative && (
              <section className="space-y-6">
                <h2 className="text-lg font-semibold text-gray-900">Narrative</h2>

                {report.narrative.executive_summary && (
                  <div className="rounded-lg border border-gray-200 p-5">
                    <h3 className="font-semibold text-gray-800 mb-2">Executive Summary</h3>
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{report.narrative.executive_summary}</p>
                  </div>
                )}

                {report.narrative.portfolio_commentary && (
                  <div className="rounded-lg border border-gray-200 p-5">
                    <h3 className="font-semibold text-gray-800 mb-2">Portfolio Commentary</h3>
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{report.narrative.portfolio_commentary}</p>
                  </div>
                )}

                {report.narrative.market_outlook && (
                  <div className="rounded-lg border border-gray-200 p-5">
                    <h3 className="font-semibold text-gray-800 mb-2">Market Outlook</h3>
                    <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{report.narrative.market_outlook}</p>
                  </div>
                )}

                {report.narrative.esg_highlights && (
                  <div className="rounded-lg border border-green-200 bg-green-50 p-5">
                    <h3 className="font-semibold text-green-800 mb-2">ESG Highlights</h3>
                    <p className="text-green-700 leading-relaxed whitespace-pre-wrap">{report.narrative.esg_highlights}</p>
                  </div>
                )}
              </section>
            )}

            {/* AI Feedback */}
            <AIFeedback
              taskType="lp_report"
              entityType="report"
              entityId={report.id}
              compact
              className="mt-2"
            />

            {/* Investments table */}
            {report.investments_data && report.investments_data.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Investment Detail</h2>
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                      <tr>
                        <th className="px-4 py-3 text-left">Project</th>
                        <th className="px-4 py-3 text-right">Committed</th>
                        <th className="px-4 py-3 text-right">NAV</th>
                        <th className="px-4 py-3 text-right">MOIC</th>
                        <th className="px-4 py-3 text-left">Stage</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {(report.investments_data as Record<string, unknown>[]).map((inv, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{String(inv.name ?? "—")}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{inv.committed ? formatCurrency(Number(inv.committed)) : "—"}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{inv.nav ? formatCurrency(Number(inv.nav)) : "—"}</td>
                          <td className="px-4 py-3 text-right text-gray-700">{inv.moic ? `${Number(inv.moic).toFixed(2)}x` : "—"}</td>
                          <td className="px-4 py-3 text-gray-600 capitalize">{String(inv.stage ?? "—")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
