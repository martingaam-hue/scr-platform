"use client"

import { useState } from "react"
import { formatDate } from "@/lib/format"
import {
  useDealRooms, useRoomMessages, useRoomActivity,
  useCreateRoom, useInviteMember, useSendMessage,
} from "@/lib/deal-rooms"
import {
  Users, MessageSquare, FileText, Shield, Plus, X, Send,
  Lock, Eye, Activity
} from "lucide-react"

const STATUS_BADGE: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-500",
  pending: "bg-yellow-100 text-yellow-700",
}

export default function DealRoomsPage() {
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showInvite, setShowInvite] = useState(false)
  const [newMessage, setNewMessage] = useState("")
  const [newRoom, setNewRoom] = useState({ name: "", project_id: "", nda_required: true, download_restricted: false })
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("viewer")

  const { data: rooms = [] } = useDealRooms()
  const { data: messages = [], refetch: refetchMessages } = useRoomMessages(selectedRoom)
  const { data: activities = [] } = useRoomActivity(selectedRoom)
  const createMutation = useCreateRoom()
  const inviteMutation = useInviteMember(selectedRoom ?? "")
  const messageMutation = useSendMessage(selectedRoom ?? "")

  const activeRoom = rooms.find(r => r.id === selectedRoom)

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

            <div className="grid grid-cols-3 gap-4">
              {/* Message thread */}
              <div className="col-span-2 rounded-xl border border-gray-200 bg-white flex flex-col" style={{ height: 480 }}>
                <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
                  <MessageSquare className="h-4 w-4 text-gray-400" />
                  <span className="font-semibold text-gray-900 text-sm">Messages</span>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.map((msg) => (
                    <div key={msg.id} className="flex gap-3">
                      <div className="h-7 w-7 rounded-full bg-primary-100 flex items-center justify-center text-xs font-bold text-primary-700 flex-shrink-0">
                        {String(msg.user_id).slice(0, 2).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2">
                          <span className="text-sm font-medium text-gray-900 font-mono">{String(msg.user_id).slice(0, 8)}…</span>
                          <span className="text-xs text-gray-400">{formatDate(msg.created_at)}</span>
                        </div>
                        <p className="text-sm text-gray-700 mt-0.5">{msg.content}</p>
                      </div>
                    </div>
                  ))}
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
                  {activities.map((act) => (
                    <div key={act.id} className="flex gap-2 text-xs">
                      <div className="h-5 w-5 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Activity className="h-3 w-3 text-gray-400" />
                      </div>
                      <div>
                        <span className="font-medium text-gray-700 font-mono">{String(act.user_id).slice(0, 8)}…</span>
                        <span className="text-gray-500"> {act.activity_type.replace(/_/g, " ")}</span>
                        <p className="text-gray-400 mt-0.5">{formatDate(act.created_at)}</p>
                      </div>
                    </div>
                  ))}
                  {activities.length === 0 && (
                    <p className="text-center text-xs text-gray-400 py-8">No activity yet</p>
                  )}
                </div>
              </div>
            </div>
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
