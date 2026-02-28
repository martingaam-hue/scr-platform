"use client"

import { useState } from "react"
import { formatDate } from "@/lib/format"
import {
  useWatchlists, useWatchlistAlerts, useCreateWatchlist,
  useDeleteWatchlist, useToggleWatchlist, useMarkAlertRead, useParseCriteria,
} from "@/lib/watchlists"
import {
  Bell, BellOff, Plus, X, Trash2, CheckCircle, TrendingUp,
  AlertTriangle, Activity, Zap, Circle, ToggleLeft, ToggleRight, Sparkles, Loader2,
} from "lucide-react"

const WATCH_TYPE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  new_projects: Zap,
  score_changes: TrendingUp,
  risk_alerts: AlertTriangle,
  market_events: Activity,
  specific_project: Circle,
}

const ALERT_TYPE_COLOR: Record<string, string> = {
  new_match: "bg-blue-50 border-blue-200 text-blue-700",
  score_change: "bg-purple-50 border-purple-200 text-purple-700",
  risk_flag: "bg-red-50 border-red-200 text-red-700",
  market_event: "bg-yellow-50 border-yellow-200 text-yellow-700",
}

export default function WatchlistsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [nlQuery, setNlQuery] = useState("")
  const [newWatchlist, setNewWatchlist] = useState({
    name: "",
    watch_type: "new_projects",
    criteria: "{}",
    alert_channels: ["in_app"],
    alert_frequency: "immediate",
  })

  const { data: watchlists = [] } = useWatchlists()
  const { data: alerts = [] } = useWatchlistAlerts()
  const createMutation = useCreateWatchlist()
  const toggleMutation = useToggleWatchlist()
  const deleteMutation = useDeleteWatchlist()
  const markReadMutation = useMarkAlertRead()
  const parseCriteriaMutation = useParseCriteria()

  const unreadCount = alerts.filter(a => !a.is_read).length
  const activeCount = watchlists.filter(w => w.is_active).length

  const toggleChannel = (channel: string) => {
    setNewWatchlist(prev => ({
      ...prev,
      alert_channels: prev.alert_channels.includes(channel)
        ? prev.alert_channels.filter(c => c !== channel)
        : [...prev.alert_channels, channel],
    }))
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            Watchlists & Alerts
            {unreadCount > 0 && (
              <span className="ml-1 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">
                {unreadCount} new
              </span>
            )}
          </h1>
          <p className="text-sm text-gray-500 mt-1">AI-powered deal discovery and monitoring</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" />
          New Watchlist
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Active Watchlists", value: activeCount, icon: Bell, color: "text-primary-600", bg: "bg-primary-50 border-primary-200" },
          { label: "Unread Alerts", value: unreadCount, icon: AlertTriangle, color: "text-orange-600", bg: "bg-orange-50 border-orange-200" },
          { label: "Total Alerts Sent", value: watchlists.reduce((s, w) => s + w.total_alerts_sent, 0), icon: Activity, color: "text-blue-600", bg: "bg-blue-50 border-blue-200" },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className={`rounded-xl border p-4 ${bg}`}>
            <div className="flex items-center gap-2">
              <Icon className={`h-5 w-5 ${color}`} />
              <span className="text-sm font-medium text-gray-700">{label}</span>
            </div>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Watchlists */}
        <div>
          <h2 className="font-semibold text-gray-900 mb-3">My Watchlists</h2>
          <div className="space-y-3">
            {watchlists.map((wl) => {
              const Icon = WATCH_TYPE_ICON[wl.watch_type] ?? Bell
              return (
                <div key={wl.id} className={`rounded-xl border bg-white p-4 ${wl.is_active ? "border-gray-200" : "border-gray-100 opacity-60"}`}>
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${wl.is_active ? "bg-primary-100" : "bg-gray-100"}`}>
                      <Icon className={`h-5 w-5 ${wl.is_active ? "text-primary-600" : "text-gray-400"}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-gray-900 text-sm">{wl.name}</p>
                      <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                        <span className="capitalize">{wl.watch_type.replace(/_/g, " ")}</span>
                        <span>·</span>
                        <span className="capitalize">{wl.alert_frequency.replace(/_/g, " ")}</span>
                        {wl.unread_alerts > 0 && (
                          <span className="px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-bold">
                            {wl.unread_alerts} new
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button onClick={() => toggleMutation.mutate(wl.id)}>
                        {wl.is_active
                          ? <ToggleRight className="h-7 w-7 text-primary-600" />
                          : <ToggleLeft className="h-7 w-7 text-gray-300" />
                        }
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(wl.id)}
                        className="text-gray-300 hover:text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  {/* Channels */}
                  <div className="flex items-center gap-2 mt-2 pl-12">
                    {wl.alert_channels.map(ch => (
                      <span key={ch} className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600 capitalize">
                        {ch.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>
              )
            })}
            {watchlists.length === 0 && (
              <div className="text-center py-8 border border-dashed border-gray-300 rounded-xl text-gray-500">
                <BellOff className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm">No watchlists yet</p>
                <p className="text-xs mt-1">Create one to get proactive deal alerts</p>
              </div>
            )}
          </div>
        </div>

        {/* Alert feed */}
        <div>
          <h2 className="font-semibold text-gray-900 mb-3">Recent Alerts</h2>
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`rounded-xl border p-4 ${!alert.is_read ? ALERT_TYPE_COLOR[alert.alert_type] ?? "bg-blue-50 border-blue-200" : "bg-white border-gray-100"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {!alert.is_read && <div className="h-2 w-2 rounded-full bg-blue-500 flex-shrink-0" />}
                      <p className="text-sm font-medium text-gray-900 capitalize">
                        {alert.alert_type.replace(/_/g, " ")}
                      </p>
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">{alert.watchlist_name}</p>
                    {alert.data?.title != null && (
                      <p className="text-xs text-gray-500 mt-1">{String(alert.data.title)}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">{formatDate(alert.created_at)}</p>
                  </div>
                  {!alert.is_read && (
                    <button
                      onClick={() => markReadMutation.mutate(alert.id)}
                      className="flex-shrink-0 text-gray-400 hover:text-green-500"
                      title="Mark as read"
                    >
                      <CheckCircle className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
            {alerts.length === 0 && (
              <div className="text-center py-8 border border-dashed border-gray-300 rounded-xl text-gray-500">
                <Bell className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm">No alerts yet</p>
                <p className="text-xs mt-1">Alerts will appear here as they trigger</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Watchlist Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">New Watchlist</h2>
              <button onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            {/* NL Criteria Parser */}
            <div className="rounded-lg bg-primary-50 border border-primary-100 p-3">
              <label className="block text-xs font-semibold text-primary-700 mb-1.5 flex items-center gap-1">
                <Sparkles className="h-3.5 w-3.5" />
                Describe what to watch (AI will parse)
              </label>
              <div className="flex gap-2">
                <textarea
                  className="flex-1 border border-primary-200 rounded-lg px-3 py-2 text-sm bg-white resize-none"
                  rows={2}
                  placeholder="e.g. solar projects in East Africa with $5M+ investment and signal score above 70"
                  value={nlQuery}
                  onChange={e => setNlQuery(e.target.value)}
                />
                <button
                  onClick={() => parseCriteriaMutation.mutate(nlQuery, { onSuccess: (data) => {
                    setNewWatchlist(d => ({
                      ...d,
                      criteria: JSON.stringify(data.criteria, null, 2),
                      watch_type: data.watch_type ?? d.watch_type,
                    }))
                  } })}
                  disabled={!nlQuery.trim() || parseCriteriaMutation.isPending}
                  className="px-3 py-2 bg-primary-600 text-white rounded-lg text-xs hover:bg-primary-700 disabled:opacity-50 flex-shrink-0"
                >
                  {parseCriteriaMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Parse"
                  )}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. EU Solar — New Deals"
                value={newWatchlist.name}
                onChange={e => setNewWatchlist(d => ({ ...d, name: e.target.value }))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Watch Type</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={newWatchlist.watch_type}
                onChange={e => setNewWatchlist(d => ({ ...d, watch_type: e.target.value }))}>
                {Object.keys(WATCH_TYPE_ICON).map(t => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={newWatchlist.alert_frequency}
                onChange={e => setNewWatchlist(d => ({ ...d, alert_frequency: e.target.value }))}>
                {["immediate", "daily_digest", "weekly"].map(f => (
                  <option key={f} value={f}>{f.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Alert Channels</label>
              <div className="flex gap-3">
                {["in_app", "email"].map(ch => (
                  <label key={ch} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox"
                      checked={newWatchlist.alert_channels.includes(ch)}
                      onChange={() => toggleChannel(ch)} />
                    <span className="capitalize">{ch.replace(/_/g, " ")}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => {
                  let criteria = {}
                  try { criteria = JSON.parse(newWatchlist.criteria) } catch {}
                  createMutation.mutate({ ...newWatchlist, criteria }, { onSuccess: () => setShowCreate(false) })
                }}
                disabled={!newWatchlist.name || createMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Creating…" : "Create Watchlist"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
