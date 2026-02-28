"use client"

import { useState } from "react"
import { useComps, useCreateComp, useCompsValuation, QUALITY_BADGE, ASSET_TYPES, STAGES, type Comp } from "@/lib/comps"
import { formatCurrency, formatPct } from "@/lib/format"
import { Plus, Calculator, TrendingUp, X } from "lucide-react"
import { AIFeedback } from "@/components/ai-feedback"

export default function CompsPage() {
  const [filters, setFilters] = useState({
    asset_type: "",
    geography: "",
    year_from: "",
    year_to: "",
    stage: "",
  })
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showAddForm, setShowAddForm] = useState(false)
  const [newComp, setNewComp] = useState({ deal_name: "", asset_type: "solar", close_year: "", capacity_mw: "", ev_per_mw: "", equity_irr: "", data_quality: "estimated" })

  const { data, isLoading } = useComps(filters)
  const { data: valuationResult, mutate: calcValuation, isPending: calcPending } = useCompsValuation()
  const addMutation = useCreateComp()

  const comps: Comp[] = data?.items ?? []
  const total: number = data?.total ?? 0

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Comparable Transactions</h1>
          <p className="text-sm text-gray-500 mt-1">{total} transactions · public + org-private</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
          >
            <Plus className="h-4 w-4" />
            Add Transaction
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 p-4 bg-gray-50 rounded-xl border border-gray-200">
        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filters.asset_type}
          onChange={(e) => setFilters((f) => ({ ...f, asset_type: e.target.value }))}
        >
          <option value="">All Asset Types</option>
          {ASSET_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
        </select>

        <input
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-36"
          placeholder="Geography"
          value={filters.geography}
          onChange={(e) => setFilters((f) => ({ ...f, geography: e.target.value }))}
        />

        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Year:</span>
          <input
            className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm w-20"
            placeholder="From"
            value={filters.year_from}
            onChange={(e) => setFilters((f) => ({ ...f, year_from: e.target.value }))}
          />
          <span>–</span>
          <input
            className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm w-20"
            placeholder="To"
            value={filters.year_to}
            onChange={(e) => setFilters((f) => ({ ...f, year_to: e.target.value }))}
          />
        </div>

        <select
          className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
          value={filters.stage}
          onChange={(e) => setFilters((f) => ({ ...f, stage: e.target.value }))}
        >
          <option value="">All Stages</option>
          {STAGES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>

        {Object.values(filters).some(Boolean) && (
          <button onClick={() => setFilters({ asset_type: "", geography: "", year_from: "", year_to: "", stage: "" })} className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
            <X className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* Implied valuation bar (when comps selected) */}
      {selectedIds.size > 0 && (
        <div className="flex items-center justify-between p-4 bg-primary-50 border border-primary-200 rounded-xl">
          <p className="text-sm font-medium text-primary-800">{selectedIds.size} comparable{selectedIds.size > 1 ? "s" : ""} selected</p>
          <div className="flex items-center gap-3">
            {valuationResult && (
              <div className="text-sm text-primary-900">
                <span className="font-semibold">Implied EV/MW:</span>{" "}
                {valuationResult.ev_per_mw != null ? `€${(valuationResult.ev_per_mw / 1000).toFixed(0)}k/MW` : "—"}
                {valuationResult.ev_eur != null && (
                  <span className="ml-3"><span className="font-semibold">Implied EV (50MW):</span> {formatCurrency(valuationResult.ev_eur)}</span>
                )}
              </div>
            )}
            <button
              onClick={() => calcValuation({ ids: Array.from(selectedIds) })}
              disabled={calcPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              <Calculator className="h-4 w-4" />
              {calcPending ? "Calculating…" : "Implied Valuation"}
            </button>
            <button onClick={() => setSelectedIds(new Set())} className="text-primary-600 text-sm hover:underline">Clear</button>
          </div>
        </div>
      )}

      {/* AI Feedback */}
      {valuationResult && (
        <AIFeedback
          taskType="comps_analysis"
          entityType="project"
          compact
          className="mt-2"
        />
      )}

      {/* Table */}
      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="w-8 px-4 py-3"></th>
              <th className="px-4 py-3 text-left">Deal Name</th>
              <th className="px-4 py-3 text-left">Asset Type</th>
              <th className="px-4 py-3 text-left">Geography</th>
              <th className="px-4 py-3 text-center">Year</th>
              <th className="px-4 py-3 text-right">Size</th>
              <th className="px-4 py-3 text-right">Capacity</th>
              <th className="px-4 py-3 text-right">EV/MW</th>
              <th className="px-4 py-3 text-right">Eq. IRR</th>
              <th className="px-4 py-3 text-left">Stage</th>
              <th className="px-4 py-3 text-center">Quality</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">Loading…</td>
              </tr>
            )}
            {!isLoading && comps.length === 0 && (
              <tr>
                <td colSpan={11} className="px-4 py-12 text-center text-gray-500">
                  <TrendingUp className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  No comparable transactions found. Adjust filters or add one.
                </td>
              </tr>
            )}
            {comps.map((comp) => (
              <tr key={comp.id} className={`hover:bg-gray-50 ${selectedIds.has(comp.id) ? "bg-primary-50" : ""}`}>
                <td className="px-4 py-3">
                  <input type="checkbox" checked={selectedIds.has(comp.id)} onChange={() => toggleSelect(comp.id)} className="rounded" />
                </td>
                <td className="px-4 py-3">
                  <span className="font-medium text-gray-900">{comp.deal_name}</span>
                  {!comp.org_id && <span className="ml-1 text-xs text-gray-400">(global)</span>}
                </td>
                <td className="px-4 py-3 capitalize text-gray-700">{comp.asset_type.replace("_", " ")}</td>
                <td className="px-4 py-3 text-gray-700">{comp.geography ?? "—"}</td>
                <td className="px-4 py-3 text-center text-gray-700">{comp.close_year ?? "—"}</td>
                <td className="px-4 py-3 text-right text-gray-700">{comp.deal_size_eur ? formatCurrency(comp.deal_size_eur) : "—"}</td>
                <td className="px-4 py-3 text-right text-gray-700">{comp.capacity_mw ? `${comp.capacity_mw} MW` : "—"}</td>
                <td className="px-4 py-3 text-right text-gray-700">{comp.ev_per_mw ? `€${(comp.ev_per_mw / 1000).toFixed(0)}k` : "—"}</td>
                <td className="px-4 py-3 text-right text-gray-700">{comp.equity_irr ? formatPct(comp.equity_irr) : "—"}</td>
                <td className="px-4 py-3 text-gray-700 capitalize">{comp.stage_at_close?.replace("_", " ") ?? "—"}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${QUALITY_BADGE[comp.data_quality] ?? "bg-gray-100 text-gray-600"}`}>
                    {comp.data_quality}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Transaction Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-lg space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Add Comparable Transaction</h2>
              <button onClick={() => setShowAddForm(false)}><X className="h-5 w-5 text-gray-500" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Deal Name *</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.deal_name} onChange={(e) => setNewComp((c) => ({ ...c, deal_name: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Asset Type</label>
                  <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.asset_type} onChange={(e) => setNewComp((c) => ({ ...c, asset_type: e.target.value }))}>
                    {ASSET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Close Year</label>
                  <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.close_year} onChange={(e) => setNewComp((c) => ({ ...c, close_year: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Capacity (MW)</label>
                  <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.capacity_mw} onChange={(e) => setNewComp((c) => ({ ...c, capacity_mw: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">EV/MW (€)</label>
                  <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.ev_per_mw} onChange={(e) => setNewComp((c) => ({ ...c, ev_per_mw: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Equity IRR (%)</label>
                  <input type="number" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.equity_irr} onChange={(e) => setNewComp((c) => ({ ...c, equity_irr: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data Quality</label>
                  <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newComp.data_quality} onChange={(e) => setNewComp((c) => ({ ...c, data_quality: e.target.value }))}>
                    <option value="confirmed">Confirmed</option>
                    <option value="estimated">Estimated</option>
                    <option value="rumored">Rumored</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowAddForm(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
              <button
                onClick={() => addMutation.mutate({
                  ...newComp,
                  close_year: newComp.close_year ? parseInt(newComp.close_year) : null,
                  capacity_mw: newComp.capacity_mw ? parseFloat(newComp.capacity_mw) : null,
                  ev_per_mw: newComp.ev_per_mw ? parseFloat(newComp.ev_per_mw) : null,
                  equity_irr: newComp.equity_irr ? parseFloat(newComp.equity_irr) : null,
                }, { onSuccess: () => setShowAddForm(false) })}
                disabled={!newComp.deal_name || addMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {addMutation.isPending ? "Adding…" : "Add Transaction"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
