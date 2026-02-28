"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Bot, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, MessageSquare, HelpCircle, FileText, Printer } from "lucide-react"
import { AIFeedback } from "@/components/ai-feedback"

interface BriefingContent {
  executive_summary?: string
  key_metrics?: Record<string, unknown>
  risk_flags?: Array<{ flag: string; severity: string; mitigation?: string }>
  dd_progress?: { total?: number; completed?: number; pct?: number; outstanding_items?: string[] }
  talking_points?: string[]
  questions_to_ask?: string[]
  changes_since_last?: string[]
}

interface Briefing {
  id: string
  project_id: string
  meeting_type: string
  meeting_date: string | null
  briefing_content: BriefingContent | null
  custom_overrides: Record<string, unknown> | null
  created_at: string
}

const MEETING_TYPES = [
  { value: "screening", label: "Screening" },
  { value: "dd_review", label: "DD Review" },
  { value: "follow_up", label: "Follow-Up" },
  { value: "ic_presentation", label: "IC Presentation" },
]

const RISK_SEVERITY_COLOR: Record<string, string> = {
  high: "bg-red-100 text-red-700 border-red-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-green-100 text-green-700 border-green-200",
}

function CheckedList({ items, label, icon: Icon }: { items: string[]; label: string; icon: React.ComponentType<{ className?: string }> }) {
  const [checked, setChecked] = useState<Set<number>>(new Set())
  const toggle = (i: number) => setChecked((prev) => { const next = new Set(prev); next.has(i) ? next.delete(i) : next.add(i); return next })

  return (
    <div className="rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="h-5 w-5 text-primary-600" />
        <h3 className="font-semibold text-gray-900">{label}</h3>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 cursor-pointer" onClick={() => toggle(i)}>
            <div className={`mt-0.5 h-5 w-5 rounded border flex items-center justify-center flex-shrink-0 ${checked.has(i) ? "bg-primary-600 border-primary-600" : "border-gray-300"}`}>
              {checked.has(i) && <CheckCircle className="h-3.5 w-3.5 text-white" />}
            </div>
            <span className={`text-sm text-gray-700 ${checked.has(i) ? "line-through text-gray-400" : ""}`}>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function MeetingPrepPage() {
  const params = useParams()
  const projectId = params.id as string
  const queryClient = useQueryClient()

  const [meetingType, setMeetingType] = useState("screening")
  const [meetingDate, setMeetingDate] = useState("")
  const [previousDate, setPreviousDate] = useState("")

  const { data: briefingsData } = useQuery({
    queryKey: ["meeting-briefings", projectId],
    queryFn: () => api.get(`/meeting-prep/briefings?project_id=${projectId}`).then((r) => r.data),
  })

  const [selectedBriefingId, setSelectedBriefingId] = useState<string | null>(null)

  const { data: briefing, isLoading: loadingBriefing } = useQuery({
    queryKey: ["meeting-briefing", selectedBriefingId],
    queryFn: () => api.get(`/meeting-prep/briefings/${selectedBriefingId}`).then((r) => r.data),
    enabled: !!selectedBriefingId,
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      api.post("/meeting-prep/briefings", {
        project_id: projectId,
        meeting_type: meetingType,
        meeting_date: meetingDate || null,
        previous_meeting_date: previousDate || null,
      }).then((r) => r.data),
    onSuccess: (data: Briefing) => {
      queryClient.invalidateQueries({ queryKey: ["meeting-briefings", projectId] })
      setSelectedBriefingId(data.id)
    },
  })

  const briefings: Briefing[] = briefingsData?.items ?? []
  const content: BriefingContent = {
    ...(briefing?.briefing_content ?? {}),
    ...(briefing?.custom_overrides ?? {}),
  }

  return (
    <div className="flex h-full min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900 flex items-center gap-2">
            <Bot className="h-4 w-4 text-primary-600" />
            Meeting Prep
          </h2>
        </div>

        {/* Generator */}
        <div className="p-4 border-b border-gray-200 space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Meeting Type</label>
            <div className="grid grid-cols-2 gap-1">
              {MEETING_TYPES.map((mt) => (
                <button
                  key={mt.value}
                  onClick={() => setMeetingType(mt.value)}
                  className={`px-2 py-1 text-xs rounded-md border transition-colors ${meetingType === mt.value ? "bg-primary-600 text-white border-primary-600" : "border-gray-300 text-gray-700 hover:bg-gray-100"}`}
                >
                  {mt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Meeting Date</label>
            <input type="date" className="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} />
          </div>

          {meetingType === "follow_up" && (
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Previous Meeting</label>
              <input type="date" className="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm" value={previousDate} onChange={(e) => setPreviousDate(e.target.value)} />
            </div>
          )}

          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="w-full bg-primary-600 text-white text-sm py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {generateMutation.isPending ? "Generating…" : "Generate Briefing"}
          </button>
        </div>

        {/* History */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase">Past Briefings</p>
          {briefings.map((b) => (
            <button
              key={b.id}
              onClick={() => setSelectedBriefingId(b.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${selectedBriefingId === b.id ? "bg-primary-100 text-primary-800 font-medium" : "text-gray-700 hover:bg-gray-100"}`}
            >
              <span className="capitalize">{b.meeting_type.replace("_", " ")}</span>
              <span className="block text-xs text-gray-400">{formatDate(b.created_at)}</span>
            </button>
          ))}
          {briefings.length === 0 && <p className="text-xs text-gray-400">No briefings yet.</p>}
        </div>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-8">
        {!selectedBriefingId && !generateMutation.isPending ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Bot className="h-12 w-12 text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-700">Generate a Meeting Briefing</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm">Select a meeting type and click Generate to create an AI-powered briefing tailored to your meeting.</p>
          </div>
        ) : loadingBriefing ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-600 border-t-transparent" />
          </div>
        ) : briefing ? (
          <div className="max-w-3xl space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-gray-900 capitalize">{briefing.meeting_type.replace("_", " ")} Briefing</h1>
                {briefing.meeting_date && <p className="text-sm text-gray-500">Meeting: {formatDate(briefing.meeting_date)}</p>}
              </div>
              <div className="flex items-center gap-3">
                <AIFeedback
                  taskType="meeting_briefing"
                  entityType="project"
                  entityId={projectId}
                  compact
                />
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
                >
                  <Printer className="h-4 w-4" />
                  Print / Export PDF
                </button>
              </div>
            </div>

            {/* Executive Summary */}
            {content.executive_summary && (
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
                <h2 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Executive Summary
                </h2>
                <p className="text-blue-800 text-sm leading-relaxed">{content.executive_summary}</p>
              </div>
            )}

            {/* Risk Flags */}
            {content.risk_flags && content.risk_flags.length > 0 && (
              <div className="rounded-xl border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  Risk Flags
                </h2>
                <ul className="space-y-2">
                  {content.risk_flags.map((rf, i) => (
                    <li key={i} className={`flex items-start gap-3 p-3 rounded-lg border text-sm ${RISK_SEVERITY_COLOR[rf.severity] ?? "bg-gray-100 text-gray-700 border-gray-200"}`}>
                      <span className="font-medium capitalize">[{rf.severity}]</span>
                      <div>
                        <p>{rf.flag}</p>
                        {rf.mitigation && <p className="mt-0.5 text-xs opacity-80">Mitigation: {rf.mitigation}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* DD Progress */}
            {content.dd_progress && Object.keys(content.dd_progress).length > 0 && (
              <div className="rounded-xl border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-900 mb-3">DD Progress</h2>
                <div className="flex items-center gap-4">
                  {content.dd_progress.pct != null && (
                    <div className="flex-1">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>{content.dd_progress.completed ?? 0} / {content.dd_progress.total ?? "?"} items</span>
                        <span className="font-medium">{content.dd_progress.pct?.toFixed(0)}%</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div className="h-full bg-primary-600 rounded-full" style={{ width: `${content.dd_progress.pct}%` }} />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Talking Points */}
            {content.talking_points && content.talking_points.length > 0 && (
              <CheckedList items={content.talking_points} label="Talking Points" icon={MessageSquare} />
            )}

            {/* Questions to Ask */}
            {content.questions_to_ask && content.questions_to_ask.length > 0 && (
              <CheckedList items={content.questions_to_ask} label="Questions to Ask" icon={HelpCircle} />
            )}

            {/* Changes since last (follow_up only) */}
            {content.changes_since_last && content.changes_since_last.length > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
                <h2 className="font-semibold text-amber-900 mb-3">Changes Since Last Meeting</h2>
                <ul className="space-y-1.5">
                  {content.changes_since_last.map((change, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-amber-800">
                      <span className="text-amber-600 mt-0.5">•</span>
                      {change}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}
      </main>
    </div>
  )
}
