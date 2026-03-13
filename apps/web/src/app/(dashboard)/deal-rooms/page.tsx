"use client"

import { useState } from "react"
import { formatDate } from "@/lib/format"
import {
  useDealRooms, useRoomMessages, useRoomActivity,
  useCreateRoom, useInviteMember, useSendMessage,
  type DealRoom, type DealRoomMessage, type DealRoomActivity,
} from "@/lib/deal-rooms"
import { useProjectQuestions, useCreateQuestion, useQAStats } from "@/lib/qa"
import {
  Users, MessageSquare, Plus, X, Send,
  Lock, Eye, Activity, HelpCircle,
} from "lucide-react"

const STATUS_BADGE: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-500",
  pending: "bg-yellow-100 text-yellow-700",
}

// ── Mock data ──────────────────────────────────────────────────────────────

const MOCK_ROOMS: DealRoom[] = [
  {
    id: "room-p2",
    name: "Danube Hydro Expansion — Due Diligence",
    project_id: "p2",
    status: "active",
    created_by: "user-sofia",
    settings: { nda_required: true, download_restricted: false },
    members: [
      { id: "mbr-1", room_id: "room-p2", user_id: "user-sofia",  email: "sofia.bergman@fund.eu",    role: "admin",  org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-10T09:00:00Z", joined_at: "2026-02-10T09:00:00Z", nda_signed_at: "2026-02-10T09:05:00Z" },
      { id: "mbr-2", room_id: "room-p2", user_id: "user-marco",  email: "marco.rossi@fund.eu",      role: "member", org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-10T09:10:00Z", joined_at: "2026-02-10T10:00:00Z", nda_signed_at: "2026-02-10T10:00:00Z" },
      { id: "mbr-3", room_id: "room-p2", user_id: "user-danube", email: "ceo@danubehydro.ro",       role: "member", org_name: "Danube Hydro SA",          permissions: {}, invited_at: "2026-02-11T08:00:00Z", joined_at: "2026-02-11T09:00:00Z", nda_signed_at: "2026-02-11T09:05:00Z" },
    ],
    created_at: "2026-02-10T09:00:00Z",
  },
  {
    id: "room-p3",
    name: "Aegean Wind Cluster — Due Diligence",
    project_id: "p3",
    status: "active",
    created_by: "user-erik",
    settings: { nda_required: true, download_restricted: true },
    members: [
      { id: "mbr-4", room_id: "room-p3", user_id: "user-erik",   email: "erik.lindstrom@fund.eu",   role: "admin",  org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-15T10:00:00Z", joined_at: "2026-02-15T10:00:00Z", nda_signed_at: "2026-02-15T10:05:00Z" },
      { id: "mbr-5", room_id: "room-p3", user_id: "user-sofia",  email: "sofia.bergman@fund.eu",    role: "member", org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-15T10:10:00Z", joined_at: "2026-02-15T11:00:00Z", nda_signed_at: "2026-02-15T11:05:00Z" },
      { id: "mbr-6", room_id: "room-p3", user_id: "user-aegean", email: "ir@aegeanwind.gr",         role: "member", org_name: "Aegean Wind GmbH",         permissions: {}, invited_at: "2026-02-16T08:00:00Z", joined_at: "2026-02-16T09:30:00Z", nda_signed_at: "2026-02-16T09:35:00Z" },
    ],
    created_at: "2026-02-15T10:00:00Z",
  },
  {
    id: "room-p4",
    name: "Bavarian Biomass Network — Negotiation",
    project_id: "p4",
    status: "active",
    created_by: "user-marco",
    settings: { nda_required: false, download_restricted: false },
    members: [
      { id: "mbr-7", room_id: "room-p4", user_id: "user-marco",   email: "marco.rossi@fund.eu",     role: "admin",  org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-20T09:00:00Z", joined_at: "2026-02-20T09:00:00Z", nda_signed_at: null },
      { id: "mbr-8", room_id: "room-p4", user_id: "user-erik",    email: "erik.lindstrom@fund.eu",  role: "member", org_name: "European Renewables Fund", permissions: {}, invited_at: "2026-02-20T09:10:00Z", joined_at: "2026-02-20T10:00:00Z", nda_signed_at: null },
      { id: "mbr-9", room_id: "room-p4", user_id: "user-bavarian",email: "cfo@bavarianbiomass.de",  role: "member", org_name: "Bavarian Biomass GmbH",    permissions: {}, invited_at: "2026-02-21T08:00:00Z", joined_at: "2026-02-21T09:00:00Z", nda_signed_at: null },
    ],
    created_at: "2026-02-20T09:00:00Z",
  },
]

const MOCK_MESSAGES: Record<string, DealRoomMessage[]> = {
  "room-p2": [
    { id: "msg-1", room_id: "room-p2", user_id: "user-sofia",  parent_id: null, content: "Welcome to the Danube Hydro DD room. Please upload the latest hydrology report and grid connection permit by end of week.", mentions: [], created_at: "2026-02-10T09:15:00Z" },
    { id: "msg-2", room_id: "room-p2", user_id: "user-danube", parent_id: null, content: "Thank you. We will upload the Q4 2025 hydrology study and the ANRE grid permit today. The technical report from Bureau Veritas will follow Thursday.", mentions: [], created_at: "2026-02-10T11:30:00Z" },
    { id: "msg-3", room_id: "room-p2", user_id: "user-marco",  parent_id: null, content: "I have reviewed the P50/P90 yield study. The P50 annual generation is 142 GWh which is in line with our assumptions. Can you confirm the curtailment assumptions used?", mentions: [], created_at: "2026-02-12T14:00:00Z" },
    { id: "msg-4", room_id: "room-p2", user_id: "user-danube", parent_id: null, content: "Curtailment is modelled at 3.2% based on the 2024 grid operator report for the Craiova substation. We have the detailed model available for sharing.", mentions: [], created_at: "2026-02-12T15:45:00Z" },
    { id: "msg-5", room_id: "room-p2", user_id: "user-sofia",  parent_id: null, content: "DD checklist is now 65% complete. Outstanding items: environmental permit, land title registry, and offtake term sheet. Target completion: 5 March.", mentions: [], created_at: "2026-03-01T10:00:00Z" },
  ],
  "room-p3": [
    { id: "msg-6", room_id: "room-p3", user_id: "user-erik",   parent_id: null, content: "Aegean Wind room is open. We are targeting IC submission by 28 March. Key focus areas: turbine supply chain, grid capacity, and permitting timeline.", mentions: [], created_at: "2026-02-15T10:30:00Z" },
    { id: "msg-7", room_id: "room-p3", user_id: "user-aegean", parent_id: null, content: "Site visit has been scheduled for 4 March at 09:00 local time. We will arrange transport from Athens airport. Please confirm attendee names for permits.", mentions: [], created_at: "2026-02-16T09:00:00Z" },
    { id: "msg-8", room_id: "room-p3", user_id: "user-sofia",  parent_id: null, content: "Erik and I will attend. Marco will join remotely. We are also requesting the RWE technical advisor to join for the turbine foundation inspection.", mentions: [], created_at: "2026-02-16T11:00:00Z" },
    { id: "msg-9", room_id: "room-p3", user_id: "user-aegean", parent_id: null, content: "Understood. Term sheet draft has been shared via the data room. Section 4.2 on development fee recoverability is open for discussion.", mentions: [], created_at: "2026-03-02T14:00:00Z" },
    { id: "msg-10", room_id: "room-p3", user_id: "user-erik",  parent_id: null, content: "We reviewed section 4.2. The development fee cap of €1.8M is acceptable subject to a milestone-linked disbursement schedule. We will provide redlines by Friday.", mentions: [], created_at: "2026-03-03T09:30:00Z" },
  ],
  "room-p4": [
    { id: "msg-11", room_id: "room-p4", user_id: "user-marco",   parent_id: null, content: "Bavarian Biomass negotiation room is now active. We have agreed the headline terms. This room is for finalising the SPA and ancillary documents.", mentions: [], created_at: "2026-02-20T09:15:00Z" },
    { id: "msg-12", room_id: "room-p4", user_id: "user-bavarian",parent_id: null, content: "Understood. Our legal team (Noerr München) will upload the first draft SPA by 25 February. Key open items: change of control consent and biomass supply warranties.", mentions: [], created_at: "2026-02-20T11:00:00Z" },
    { id: "msg-13", room_id: "room-p4", user_id: "user-erik",    parent_id: null, content: "We engaged Linklaters on our side. They will revert within 5 business days on the SPA draft. The biomass supply warranties are a key risk point for us — we need a 10-year indexed supply contract.", mentions: [], created_at: "2026-02-21T10:00:00Z" },
    { id: "msg-14", room_id: "room-p4", user_id: "user-bavarian",parent_id: null, content: "We have a 7-year supply agreement in place with Bayerische Holzwerke. Extension option for 5 years at pre-agreed index. Full contract is uploaded in folder /Legal.", mentions: [], created_at: "2026-02-25T14:00:00Z" },
  ],
}

const MOCK_ACTIVITIES: Record<string, DealRoomActivity[]> = {
  "room-p2": [
    { id: "act-1", room_id: "room-p2", user_id: "user-danube", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-1", description: "Uploaded Q4 2025 Hydrology Study", created_at: "2026-02-11T10:00:00Z" },
    { id: "act-2", room_id: "room-p2", user_id: "user-danube", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-2", description: "Uploaded ANRE Grid Connection Permit", created_at: "2026-02-11T14:00:00Z" },
    { id: "act-3", room_id: "room-p2", user_id: "user-marco",  activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-1", description: "Viewed hydrology study (12 min)", created_at: "2026-02-13T09:30:00Z" },
    { id: "act-4", room_id: "room-p2", user_id: "user-danube", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-3", description: "Uploaded Bureau Veritas Technical Report", created_at: "2026-02-13T16:00:00Z" },
  ],
  "room-p3": [
    { id: "act-5", room_id: "room-p3", user_id: "user-aegean", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-4", description: "Uploaded Wind Resource Assessment (WRA)", created_at: "2026-02-17T09:00:00Z" },
    { id: "act-6", room_id: "room-p3", user_id: "user-erik",   activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-4", description: "Viewed WRA report (28 min)", created_at: "2026-02-17T14:00:00Z" },
    { id: "act-7", room_id: "room-p3", user_id: "user-aegean", activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-5", description: "Uploaded Term Sheet Draft v1", created_at: "2026-03-02T13:00:00Z" },
  ],
  "room-p4": [
    { id: "act-8",  room_id: "room-p4", user_id: "user-bavarian",activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-6", description: "Uploaded SPA First Draft", created_at: "2026-02-25T10:00:00Z" },
    { id: "act-9",  room_id: "room-p4", user_id: "user-erik",    activity_type: "document_viewed",   entity_type: "document", entity_id: "doc-6", description: "Viewed SPA draft (45 min)", created_at: "2026-02-25T15:00:00Z" },
    { id: "act-10", room_id: "room-p4", user_id: "user-bavarian",activity_type: "document_uploaded", entity_type: "document", entity_id: "doc-7", description: "Uploaded Biomass Supply Agreement", created_at: "2026-02-25T16:00:00Z" },
  ],
}

export default function DealRoomsPage() {
  const [selectedRoom, setSelectedRoom] = useState<string | null>("room-p2")
  const [showCreate, setShowCreate] = useState(false)
  const [showInvite, setShowInvite] = useState(false)
  const [newMessage, setNewMessage] = useState("")
  const [newRoom, setNewRoom] = useState({ name: "", project_id: "", nda_required: true, download_restricted: false })
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("viewer")
  const [detailTab, setDetailTab] = useState<"messages" | "qa">("messages")
  const [showAskForm, setShowAskForm] = useState(false)
  const [qaForm, setQaForm] = useState({ category: "financial", priority: "normal", title: "", body: "" })

  const { data: apiRooms = [] } = useDealRooms()
  const rooms: DealRoom[] = apiRooms.length > 0 ? apiRooms : MOCK_ROOMS
  const { data: apiMessages = [], refetch: refetchMessages } = useRoomMessages(selectedRoom)
  const messages: DealRoomMessage[] = apiMessages.length > 0 ? apiMessages : (selectedRoom ? (MOCK_MESSAGES[selectedRoom] ?? []) : [])
  const { data: apiActivities = [] } = useRoomActivity(selectedRoom)
  const activities: DealRoomActivity[] = apiActivities.length > 0 ? apiActivities : (selectedRoom ? (MOCK_ACTIVITIES[selectedRoom] ?? []) : [])
  const createMutation = useCreateRoom()
  const inviteMutation = useInviteMember(selectedRoom ?? "")
  const messageMutation = useSendMessage(selectedRoom ?? "")

  const activeRoom = rooms.find(r => r.id === selectedRoom)
  const projectId = activeRoom?.project_id ? String(activeRoom.project_id) : undefined
  const { data: questions = [] } = useProjectQuestions(projectId)
  const { data: qaStats } = useQAStats(projectId)
  const createQuestion = useCreateQuestion()

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Deal Rooms</h1>
          <p className="text-sm text-gray-500 mt-1">Secure spaces for multi-party deal collaboration</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" />
          New Room
        </button>
      </div>

      <div className="flex gap-6">
        {/* Room list */}
        <div className="w-72 flex-shrink-0 space-y-2">
          {rooms.map((room) => (
            <button
              key={room.id}
              onClick={() => setSelectedRoom(room.id)}
              className={`w-full text-left rounded-xl border p-4 transition-colors ${selectedRoom === room.id ? "border-primary-300 bg-primary-50" : "border-gray-200 bg-white hover:bg-gray-50"}`}
            >
              <div className="flex items-start justify-between">
                <p className="font-semibold text-gray-900 text-sm truncate pr-2">{room.name}</p>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${STATUS_BADGE[room.status] ?? "bg-gray-100 text-gray-600"}`}>
                  {room.status}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1 truncate font-mono">{String(room.project_id).slice(0, 8)}…</p>
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                <span className="flex items-center gap-1"><Users className="h-3.5 w-3.5" />{room.members.length}</span>
                {room.settings.nda_required && <Lock className="h-3.5 w-3.5 text-orange-500" />}
              </div>
            </button>
          ))}
          {rooms.length === 0 && (
            <div className="text-center py-8 border border-dashed border-gray-300 rounded-xl text-gray-500">
              <Users className="h-8 w-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm">No deal rooms yet</p>
            </div>
          )}
        </div>

        {/* Room detail */}
        {selectedRoom && activeRoom ? (
          <div className="flex-1 min-w-0 space-y-4">
            {/* Room header */}
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">{activeRoom.name}</h2>
                  <p className="text-sm text-gray-500 font-mono">{String(activeRoom.project_id).slice(0, 8)}…</p>
                </div>
                <div className="flex items-center gap-2">
                  {activeRoom.settings.nda_required && (
                    <span className="flex items-center gap-1 text-xs text-orange-600 bg-orange-50 border border-orange-200 rounded-lg px-2 py-1">
                      <Lock className="h-3.5 w-3.5" /> NDA Required
                    </span>
                  )}
                  {activeRoom.settings.download_restricted && (
                    <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-2 py-1">
                      <Eye className="h-3.5 w-3.5" /> View-only
                    </span>
                  )}
                  <button
                    onClick={() => setShowInvite(true)}
                    className="flex items-center gap-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                  >
                    <Plus className="h-4 w-4" /> Invite
                  </button>
                </div>
              </div>
            </div>

            {/* Detail tabs */}
            <div className="flex gap-1 border-b border-gray-200">
              {(["messages", "qa"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setDetailTab(tab)}
                  className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${detailTab === tab ? "border-primary-600 text-primary-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
                >
                  {tab === "messages" ? <MessageSquare className="h-3.5 w-3.5" /> : <HelpCircle className="h-3.5 w-3.5" />}
                  {tab === "messages" ? "Messages" : "Q&A"}
                  {tab === "qa" && qaStats && qaStats.open > 0 && (
                    <span className="ml-1 rounded-full bg-primary-100 px-1.5 py-0.5 text-[10px] font-semibold text-primary-700">{qaStats.open}</span>
                  )}
                </button>
              ))}
            </div>

            {detailTab === "qa" && (
              <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
                {/* Stats bar */}
                {qaStats && (
                  <div className="flex gap-4 text-xs text-gray-500">
                    <span>Open: <strong className="text-gray-700">{qaStats.open}</strong></span>
                    <span>Answered: <strong className="text-gray-700">{qaStats.answered}</strong></span>
                    {qaStats.sla_breached > 0 && (
                      <span className="text-red-600">SLA Breached: <strong>{qaStats.sla_breached}</strong></span>
                    )}
                  </div>
                )}
                {/* Ask question form */}
                {showAskForm ? (
                  <div className="rounded-lg border border-gray-200 p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
                        <select className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" value={qaForm.category} onChange={e => setQaForm(f => ({ ...f, category: e.target.value }))}>
                          {["financial","legal","technical","commercial","regulatory","esg","operational"].map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
                        <select className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" value={qaForm.priority} onChange={e => setQaForm(f => ({ ...f, priority: e.target.value }))}>
                          {["urgent","high","normal","low"].map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                      </div>
                    </div>
                    <input className="w-full border border-gray-300 rounded px-3 py-2 text-sm" placeholder="Question title" value={qaForm.title} onChange={e => setQaForm(f => ({ ...f, title: e.target.value }))} />
                    <textarea className="w-full border border-gray-300 rounded px-3 py-2 text-sm resize-none" rows={3} placeholder="Question body" value={qaForm.body} onChange={e => setQaForm(f => ({ ...f, body: e.target.value }))} />
                    <div className="flex gap-2">
                      <button className="px-3 py-1.5 bg-primary-600 text-white rounded text-sm hover:bg-primary-700 disabled:opacity-50" disabled={!qaForm.title.trim() || createQuestion.isPending} onClick={() => {
                        if (!projectId) return
                        createQuestion.mutate({ project_id: projectId, ...qaForm }, { onSuccess: () => { setShowAskForm(false); setQaForm({ category: "financial", priority: "normal", title: "", body: "" }) } })
                      }}>Submit</button>
                      <button className="px-3 py-1.5 border border-gray-300 rounded text-sm" onClick={() => setShowAskForm(false)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <button className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50" onClick={() => setShowAskForm(true)}>
                    <Plus className="h-4 w-4" /> Ask Question
                  </button>
                )}
                {/* Questions list */}
                {questions.length === 0 ? (
                  <p className="text-center text-sm text-gray-400 py-8">No questions yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead><tr className="border-b text-left text-gray-500">
                        <th className="py-2 pr-3 font-medium">#</th>
                        <th className="py-2 pr-3 font-medium">Category</th>
                        <th className="py-2 pr-3 font-medium">Priority</th>
                        <th className="py-2 pr-3 font-medium">Status</th>
                        <th className="py-2 font-medium">Title</th>
                      </tr></thead>
                      <tbody>
                        {questions.map(q => (
                          <tr key={q.id} className="border-b last:border-0">
                            <td className="py-2 pr-3 text-gray-400">{q.question_number}</td>
                            <td className="py-2 pr-3 capitalize text-gray-700">{q.category}</td>
                            <td className="py-2 pr-3">
                              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${q.priority === "urgent" ? "bg-red-100 text-red-700" : q.priority === "high" ? "bg-orange-100 text-orange-700" : "bg-gray-100 text-gray-600"}`}>{q.priority}</span>
                            </td>
                            <td className="py-2 pr-3">
                              <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${q.status === "answered" ? "bg-green-100 text-green-700" : q.sla_breached ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"}`}>{q.sla_breached ? "SLA breach" : q.status}</span>
                            </td>
                            <td className="py-2 text-gray-900">{q.title}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {detailTab === "messages" && <div className="grid grid-cols-3 gap-4">
              {/* Message thread */}
              <div className="col-span-2 rounded-xl border border-gray-200 bg-white flex flex-col" style={{ height: 480 }}>
                <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
                  <MessageSquare className="h-4 w-4 text-gray-400" />
                  <span className="font-semibold text-gray-900 text-sm">Messages</span>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((msg) => {
                    const nameMap: Record<string, string> = {
                      "user-sofia": "Sofia Bergman", "user-erik": "Erik Lindström",
                      "user-marco": "Marco Rossi", "user-danube": "Danube Hydro SA",
                      "user-aegean": "Aegean Wind GmbH", "user-bavarian": "Bavarian Biomass GmbH",
                    }
                    const displayName = nameMap[msg.user_id] ?? msg.user_id.slice(0, 8) + "…"
                    const initials = displayName.split(" ").slice(0, 2).map((w: string) => w[0] ?? "").join("").toUpperCase()
                    return (
                    <div key={msg.id} className="flex gap-3">
                      <div className="h-7 w-7 rounded-full bg-primary-100 flex items-center justify-center text-xs font-bold text-primary-700 flex-shrink-0">
                        {initials}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2">
                          <span className="text-sm font-medium text-gray-900">{displayName}</span>
                          <span className="text-xs text-gray-400">{formatDate(msg.created_at)}</span>
                        </div>
                        <p className="text-sm text-gray-700 mt-0.5">{msg.content}</p>
                      </div>
                    </div>
                    )
                  })}
                  {messages.length === 0 && (
                    <p className="text-center text-sm text-gray-400 py-8">No messages yet. Start the conversation.</p>
                  )}
                </div>
                <div className="p-3 border-t border-gray-100">
                  <div className="flex gap-2">
                    <textarea
                      rows={2}
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
                      placeholder="Type a message… (Enter to send)"
                      value={newMessage}
                      onChange={e => setNewMessage(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault()
                          if (newMessage.trim()) messageMutation.mutate(newMessage.trim(), { onSuccess: () => { refetchMessages(); setNewMessage("") } })
                        }
                      }}
                    />
                    <button
                      onClick={() => { if (newMessage.trim()) messageMutation.mutate(newMessage.trim(), { onSuccess: () => { refetchMessages(); setNewMessage("") } }) }}
                      disabled={!newMessage.trim() || messageMutation.isPending}
                      className="flex-shrink-0 flex items-center justify-center h-10 w-10 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Activity feed */}
              <div className="rounded-xl border border-gray-200 bg-white flex flex-col" style={{ height: 480 }}>
                <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
                  <Activity className="h-4 w-4 text-gray-400" />
                  <span className="font-semibold text-gray-900 text-sm">Activity</span>
                </div>
                <div className="flex-1 overflow-y-auto p-3 space-y-3">
                  {activities.map((act) => {
                    const nameMap: Record<string, string> = {
                      "user-sofia": "Sofia B.", "user-erik": "Erik L.",
                      "user-marco": "Marco R.", "user-danube": "Danube Hydro",
                      "user-aegean": "Aegean Wind", "user-bavarian": "Bavarian Biomass",
                    }
                    const displayName = nameMap[act.user_id] ?? act.user_id.slice(0, 8) + "…"
                    return (
                    <div key={act.id} className="flex gap-2 text-xs">
                      <div className="h-5 w-5 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Activity className="h-3 w-3 text-gray-400" />
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">{displayName}</span>
                        {act.description
                          ? <span className="text-gray-500"> {act.description}</span>
                          : <span className="text-gray-500"> {act.activity_type.replace(/_/g, " ")}</span>
                        }
                        <p className="text-gray-400 mt-0.5">{formatDate(act.created_at)}</p>
                      </div>
                    </div>
                    )
                  })}
                  {activities.length === 0 && (
                    <p className="text-center text-xs text-gray-400 py-8">No activity yet</p>
                  )}
                </div>
              </div>
            </div>}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Users className="h-12 w-12 text-gray-200 mx-auto mb-3" />
              <p className="font-medium text-gray-500">Select a deal room</p>
              <p className="text-sm mt-1">or create a new one to get started</p>
            </div>
          </div>
        )}
      </div>

      {/* Create Room Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Create Deal Room</h2>
              <button onClick={() => setShowCreate(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Room Name *</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="e.g. Solar Farm A — Series A"
                value={newRoom.name}
                onChange={e => setNewRoom(d => ({ ...d, name: e.target.value }))} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Project ID</label>
              <input className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="UUID of the project"
                value={newRoom.project_id}
                onChange={e => setNewRoom(d => ({ ...d, project_id: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" className="rounded"
                  checked={newRoom.nda_required}
                  onChange={e => setNewRoom(d => ({ ...d, nda_required: e.target.checked }))} />
                <Lock className="h-4 w-4 text-orange-500" />
                Require NDA before access
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" className="rounded"
                  checked={newRoom.download_restricted}
                  onChange={e => setNewRoom(d => ({ ...d, download_restricted: e.target.checked }))} />
                <Eye className="h-4 w-4 text-blue-500" />
                Restrict downloads (view-only)
              </label>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => createMutation.mutate({ name: newRoom.name, project_id: newRoom.project_id, settings: { nda_required: newRoom.nda_required, download_restricted: newRoom.download_restricted } }, { onSuccess: (data) => { setShowCreate(false); setSelectedRoom(data.id) } })}
                disabled={!newRoom.name || createMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {createMutation.isPending ? "Creating…" : "Create Room"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInvite && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900">Invite Member</h2>
              <button onClick={() => setShowInvite(false)}><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input type="email" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="colleague@firm.com"
                value={inviteEmail}
                onChange={e => setInviteEmail(e.target.value)} />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
              <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={inviteRole} onChange={e => setInviteRole(e.target.value)}>
                {["viewer", "member", "admin"].map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowInvite(false)} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => inviteMutation.mutate({ email: inviteEmail, role: inviteRole }, { onSuccess: () => { setShowInvite(false); setInviteEmail("") } })}
                disabled={!inviteEmail || inviteMutation.isPending}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
              >
                {inviteMutation.isPending ? "Inviting…" : "Send Invite"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
