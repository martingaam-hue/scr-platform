"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { formatDate } from "@/lib/format"
import {
  Calendar, List, AlertTriangle, CheckCircle, Clock, Plus, Zap, X, ChevronRight,
  Shield, FileText, Landmark, Leaf, Briefcase, RefreshCw
} from "lucide-react"

const CATEGORY_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  regulatory_filing: Landmark,
  tax: Briefcase,
  environmental: Leaf,
  permit: FileText,
  license: FileText,
  insurance: Shield,
  reporting: FileText,
  sfdr: Shield,
}

const STATUS_BADGE: Record<string, string> = {
  upcoming: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  overdue: "bg-red-100 text-red-700",
  waived: "bg-gray-100 text-gray-500",
}

const PRIORITY_DOT: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-blue-400",
}

interface Deadline {
  id: string
  category: string
  title: string
  description: string | null
  jurisdiction: string | null
  regulatory_body: string | null
  due_date: string
  recurrence: string | null
  status: string
  priority: string
  days_until_due: number
  is_overdue: boolean
}

export default function CompliancePage() {
  const queryClient = useQueryClient()
  const [view, setView] = useState<"list" | "calendar">("list")
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newDeadline, setNewDeadline] = useState({
    category: "regulatory_filing",
    title: "",
    description: "",
    jurisdiction: "EU",
    regulatory_body: "",
    due_date: "",
    recurrence: "annually",
    priority: "high",
  })

  const { data, isLoading } = useQuery({
    queryKey: ["compliance-deadlines", statusFilter],
    queryFn: () => api.get(`/compliance/deadlines${statusFilter ? `?status=${statusFilter}` : ""}`).then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/compliance/deadlines", body).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compliance-deadlines"] })
      setShowAddForm(false)
    },
  })

  const completeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/compliance/deadlines/${id}/complete`).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["compliance-deadlines"] }),
  })

  const autoGenerateMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/compliance/deadlines/auto-generate", body).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["compliance-deadlines"] }),
  })

  const deadlines: Deadline[] = data?.items ?? []
  const overdueCount: number = data?.overdue_count ?? 0
  const dueThisWeek: number = data?.due_this_week ?? 0
  const dueThisMonth: number = data?.due_this_month ?? 0

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            Regulatory Calendar
            {overdueCount > 0 && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">
                {overdueCount} overdue
              </span>
            )}
          </h1>
          <p className="text-sm text-gray-500 mt-1">Compliance deadlines with auto-reminders</p>
        </div>
        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex rounded-lg border border-gray-300 overflow-hidden">
            <button onClick={() => setView("list")} className={`px-3 py-1.5 text-sm ${view === "list" ? "bg-primary-600 text-white" : "bg-white text-gray-700"}`}>
              <List className="h-4 w-4" />
            </button>
            <button onClick={() => setView("calendar")} className={`px-3 py-1.5 text-sm ${view === "calendar" ? "bg-primary-600 text-white" : "bg-white text-gray-700"}`}>
              <Calendar className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={() => autoGenerateMutation.mutate({ jurisdiction: "EU", project_type: "solar" })}
            disabled={autoGenerateMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            <Zap className="h-4 w-4 text-yellow-500" />
            Auto-Generate
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Add Deadline
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Overdue", count: overdueCount, color: "text-red-600", bg: "bg-red-50 border-red-200", icon: AlertTriangle },
          { label: "Due this week", count: dueThisWeek, color: "text-orange-600", bg: "bg-orange-50 border-orange-200", icon: Clock },
          { label: "Due this month", count: dueThisMonth, color: "text-blue-600", bg: "bg-blue-50 border-blue-200", icon: Calendar },
        ].map(({ label, count, color, bg, icon: Icon }) => (
          <div key={label} className={`rounded-xl border p-4 ${bg}`}>
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 ${color}`} />
              <span className="text-sm font-medium text-gray-700">{label}</span>
            </div>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{count}</p>
          </div>
        ))}
      </div>

      {/* Status filters */}
      <div className="flex gap-2">
        {[null, "upcoming", "in_progress", "overdue", "completed"].map((s) => (
          <button
            key={s ?? "all"}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${statusFilter === s ? "bg-primary-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
          >
            {s ? s.replace("_", " ") : "All"}
          </button>
        ))}
      </div>

      {/* Deadline list */}
      {isLoading && <div className="text-center py-8 text-gray-400">Loading…</div>}

      <div className="space-y-3">
        {deadlines.map((d) => {
          const Icon = CATEGORY_ICON[d.category] ?? FileText
          return (
            <div
              key={d.id}
              className={`rounded-xl border bg-white p-4 ${d.is_overdue ? "border-red-200 bg-red-50/30" : "border-gray-200"}`}
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 mt-0.5">
                  <Icon className={`h-5 w-5 ${d.is_overdue ? "text-red-500" : "text-gray-400"}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-gray-900">{d.title}</span>
                    <div className={`h-2 w-2 rounded-full flex-shrink-0 ${PRIORITY_DOT[d.priority] ?? "bg-gray-400"}`} />
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_BADGE[d.status] ?? "bg-gray-100 text-gray-600"}`}>
                      {d.status.replace("_", " ")}
                    </span>
                    {d.recurrence && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-500 capitalize">
                        <RefreshCw className="h-3 w-3 inline mr-0.5" />{d.recurrence}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                    <span className={d.is_overdue ? "text-red-600 font-medium" : ""}>
                      Due {formatDate(d.due_date)}
                      {!d.is_overdue && d.days_until_due <= 30 && ` (${d.days_until_due}d)`}
                    </span>
                    {d.jurisdiction && <span>{d.jurisdiction}</span>}
                    {d.regulatory_body && <span>· {d.regulatory_body}</span>}
                  </div>
                  {d.description && <p className="text-xs text-gray-500 mt-1">{d.description}</p>}
                </div>
                {d.status !== "completed" && d.status !== "waived" && (
                  <button
                    onClick={() => completeMutation.mutate(d.id)}
                    className="flex-shrink-0 flex items-center gap-1 text-xs text-green-600 hover:text-green-700 border border-green-200 rounded-lg px-2 py-1 hover:bg-green-50"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    Complete
                  </button>
                )}
              </div>
            </div>
          )
        })}
        {!isLoading && deadlines.length === 0 && (
          <div className="text-center py-12 border border-dashed border-gray-300 rounded-xl text-gray-500">
            <Shield className="h-10 w-10 text-gray-300 mx-auto mb-3" />
            <p className="font-medium">No compliance deadlines</p>
            <p className="text-sm mt-1">Click "Auto-Generate" to create jurisdiction-appropriate deadlines</p>
          </div>
        )}
      </div>

      {/* Add Deadline Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-lg space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Add Compliance Deadline</h2>
              <button onClick={() => setShowAddForm(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newDeadline.category} onChange={e => setNewDeadline(d => ({ ...d, category: e.target.value }))}>
                  {["regulatory_filing", "tax", "environmental", "permit", "license", "insurance", "reporting", "sfdr"].map(c =>
                    <option key={c} value={c}>{c.replace("_", " ")}</option>
                  )}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newDeadline.priority} onChange={e => setNewDeadline(d => ({ ...d, priority: e.target.value }))}>
                  {["critical", "high", "medium", "low"].map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={newDeadline.title} onChange={e => setNewDeadline(d => ({ ...d, title: e.target.value }))}
                placeholder="e.g. Annual EIA Renewal" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Due Date *</label>
                <input type="date" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newDeadline.due_date} onChange={e => setNewDeadline(d => ({ ...d, due_date: e.target.value }))} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Recurrence</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newDeadline.recurrence} onChange={e => setNewDeadline(d => ({ ...d, recurrence: e.target.value }))}>
                  {["one_time", "monthly", "quarterly", "annually"].map(r => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Jurisdiction</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newDeadline.jurisdiction} onChange={e => setNewDeadline(d => ({ ...d, jurisdiction: e.target.value }))}
                  placeholder="EU, UK, US..." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Regulatory Body</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newDeadline.regulatory_body} onChange={e => setNewDeadline(d => ({ ...d, regulatory_body: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowAddForm(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => createMutation.mutate({ ...newDeadline, due_date: newDeadline.due_date || null })}
                disabled={!newDeadline.title || !newDeadline.due_date || createMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Adding…" : "Add Deadline"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
