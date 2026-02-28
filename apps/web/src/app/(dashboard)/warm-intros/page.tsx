"use client"

import { useState } from "react"
import { formatDate } from "@/lib/format"
import {
  useConnections, useAddConnection, useDeleteConnection, useIntroPath,
  STRENGTH_BADGE, warmthColor, warmthBg, CONNECTION_TYPES,
  type IntroPath,
} from "@/lib/warm-intros"
import { Users, Plus, Flame, X, Send, CheckCircle } from "lucide-react"

export default function WarmIntrosPage() {
  const [showAddForm, setShowAddForm] = useState(false)
  const [newConn, setNewConn] = useState({
    connection_type: "advisor",
    connected_org_name: "",
    connected_person_name: "",
    connected_person_email: "",
    relationship_strength: "moderate",
    last_interaction_date: "",
    notes: "",
  })

  const [investorId, setInvestorId] = useState("")
  const [paths, setPaths] = useState<IntroPath[]>([])

  const { data: connectionsData, isLoading } = useConnections()
  const addMutation = useAddConnection()
  const deleteMutation = useDeleteConnection()
  const pathsMutation = useIntroPath()

  const connections = connectionsData?.connections ?? []

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Warm Introductions</h1>
          <p className="text-sm text-gray-500 mt-1">Manage your network and find the warmest path to investors</p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
        >
          <Plus className="h-4 w-4" />
          Add Connection
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* My Connections */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <Users className="h-5 w-5 text-primary-600" />
            My Professional Network ({connections.length})
          </h2>

          {isLoading && <div className="text-center py-8 text-gray-400">Loading…</div>}

          {!isLoading && connections.length === 0 && (
            <div className="text-center py-12 text-gray-500 border border-dashed border-gray-300 rounded-xl">
              <Users className="h-10 w-10 text-gray-300 mx-auto mb-3" />
              <p className="font-medium">No connections yet</p>
              <p className="text-sm mt-1">Add your professional network to find warm introduction paths</p>
            </div>
          )}

          <div className="space-y-3">
            {connections.map((conn) => (
              <div key={conn.id} className="rounded-xl border border-gray-200 bg-white p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900">{conn.connected_org_name}</span>
                      {conn.connected_person_name && (
                        <span className="text-gray-500 text-sm">· {conn.connected_person_name}</span>
                      )}
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STRENGTH_BADGE[conn.relationship_strength] ?? "bg-gray-100 text-gray-600"}`}>
                        {conn.relationship_strength}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-xs text-gray-500 bg-gray-100 capitalize">
                        {conn.connection_type.replace("_", " ")}
                      </span>
                    </div>
                    {conn.connected_person_email && (
                      <p className="text-xs text-gray-400 mt-0.5">{conn.connected_person_email}</p>
                    )}
                    {conn.last_interaction_date && (
                      <p className="text-xs text-gray-400 mt-0.5">Last contact: {formatDate(conn.last_interaction_date)}</p>
                    )}
                    {conn.notes && <p className="text-xs text-gray-500 mt-1">{conn.notes}</p>}
                  </div>
                  <button
                    onClick={() => deleteMutation.mutate(conn.id)}
                    className="ml-3 text-gray-400 hover:text-red-500 flex-shrink-0"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel: Find intro paths */}
        <div className="space-y-4">
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Flame className="h-5 w-5 text-orange-500" />
              Find Introduction Paths
            </h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Investor User ID</label>
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="Paste investor user ID…"
                  value={investorId}
                  onChange={(e) => setInvestorId(e.target.value)}
                />
              </div>
              <button
                onClick={() => investorId && pathsMutation.mutate(investorId, { onSuccess: (d) => setPaths(d.paths ?? []) })}
                disabled={!investorId || pathsMutation.isPending}
                className="w-full bg-orange-500 text-white text-sm py-2 rounded-lg hover:bg-orange-600 disabled:opacity-50"
              >
                {pathsMutation.isPending ? "Searching…" : "Find Warm Paths"}
              </button>
            </div>

            {paths.length > 0 && (
              <div className="mt-5 space-y-3">
                <p className="text-xs font-medium text-gray-500 uppercase">{paths.length} path{paths.length > 1 ? "s" : ""} found</p>
                {paths.map((path, i) => (
                  <div key={i} className="rounded-lg border border-gray-100 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">{path.connector_org}</span>
                      <div className="flex items-center gap-1.5">
                        <div className="h-2 w-12 bg-gray-100 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${warmthBg(path.warmth)}`} style={{ width: `${path.warmth}%` }} />
                        </div>
                        <span className={`text-xs font-semibold ${warmthColor(path.warmth)}`}>{path.warmth.toFixed(0)}</span>
                      </div>
                    </div>
                    {path.connector_person && <p className="text-xs text-gray-500">via {path.connector_person}</p>}
                    <p className="text-xs text-gray-400 capitalize">{path.type.replace("_", " ")} · {path.connection_type.replace("_", " ")}</p>
                    <button className="mt-2 flex items-center gap-1 text-xs text-primary-600 hover:underline">
                      <Send className="h-3 w-3" />
                      Request Introduction
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Connection Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-lg space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Add Professional Connection</h2>
              <button onClick={() => setShowAddForm(false)}><X className="h-5 w-5 text-gray-500" /></button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Connection Type</label>
                  <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.connection_type} onChange={(e) => setNewConn((c) => ({ ...c, connection_type: e.target.value }))}>
                    {CONNECTION_TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ")}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Strength</label>
                  <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.relationship_strength} onChange={(e) => setNewConn((c) => ({ ...c, relationship_strength: e.target.value }))}>
                    <option value="strong">Strong</option>
                    <option value="moderate">Moderate</option>
                    <option value="weak">Weak</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Organisation *</label>
                <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.connected_org_name} onChange={(e) => setNewConn((c) => ({ ...c, connected_org_name: e.target.value }))} placeholder="e.g. BlackRock" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Contact Name</label>
                  <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.connected_person_name} onChange={(e) => setNewConn((c) => ({ ...c, connected_person_name: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Contact Email</label>
                  <input type="email" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.connected_person_email} onChange={(e) => setNewConn((c) => ({ ...c, connected_person_email: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last Interaction Date</label>
                <input type="date" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.last_interaction_date} onChange={(e) => setNewConn((c) => ({ ...c, last_interaction_date: e.target.value }))} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={newConn.notes} onChange={(e) => setNewConn((c) => ({ ...c, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowAddForm(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
              <button
                onClick={() => addMutation.mutate({
                  ...newConn,
                  last_interaction_date: newConn.last_interaction_date || null,
                }, { onSuccess: () => {
                  setShowAddForm(false)
                  setNewConn({ connection_type: "advisor", connected_org_name: "", connected_person_name: "", connected_person_email: "", relationship_strength: "moderate", last_interaction_date: "", notes: "" })
                } })}
                disabled={!newConn.connected_org_name || addMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {addMutation.isPending ? "Adding…" : "Add Connection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
