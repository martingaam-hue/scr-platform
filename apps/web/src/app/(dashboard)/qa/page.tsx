"use client";

import { useState } from "react";
import { HelpCircle, Plus, Clock, CheckCircle, AlertTriangle } from "lucide-react";
import {
  useProjectQuestions,
  useQAStats,
  type QAQuestion,
} from "@/lib/qa";

// ── Helpers ────────────────────────────────────────────────────────────────

function statusBadge(status: string, slaBreached: boolean) {
  if (slaBreached) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        <AlertTriangle className="h-3 w-3" />
        Overdue
      </span>
    );
  }
  if (status === "answered") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        <CheckCircle className="h-3 w-3" />
        Answered
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
      <Clock className="h-3 w-3" />
      Open
    </span>
  );
}

function priorityBadge(priority: string) {
  const map: Record<string, string> = {
    high: "bg-red-50 text-red-700",
    medium: "bg-amber-50 text-amber-700",
    low: "bg-neutral-100 text-neutral-600",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${map[priority] ?? map.low}`}>
      {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

// ── Stat card ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-xs font-medium text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-neutral-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-neutral-400">{sub}</p>}
    </div>
  );
}

// ── QA question row ────────────────────────────────────────────────────────

function QuestionRow({ q }: { q: QAQuestion }) {
  return (
    <tr className="border-b border-neutral-100 hover:bg-neutral-50 transition-colors">
      <td className="px-4 py-3 text-xs text-neutral-400 font-mono">#{q.question_number}</td>
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-neutral-900 line-clamp-1">{q.title}</p>
        <p className="text-xs text-neutral-500 line-clamp-1 mt-0.5">{q.body}</p>
      </td>
      <td className="px-4 py-3">{statusBadge(q.status, q.sla_breached)}</td>
      <td className="px-4 py-3">{priorityBadge(q.priority)}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">
        {q.category.replace(/_/g, " ")}
      </td>
      <td className="px-4 py-3 text-xs text-neutral-500">{formatDate(q.sla_deadline)}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">{formatDate(q.created_at)}</td>
      <td className="px-4 py-3 text-xs text-neutral-500">
        {q.answers.length > 0 ? (
          <span className="text-green-600 font-medium">{q.answers.length} answer{q.answers.length > 1 ? "s" : ""}</span>
        ) : (
          <span className="text-neutral-300">—</span>
        )}
      </td>
    </tr>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

type Tab = "open" | "answered" | "overdue";

export default function QAPage() {
  const [activeTab, setActiveTab] = useState<Tab>("open");
  const [showNewForm, setShowNewForm] = useState(false);

  // QA hooks require a projectId — we show a project selector + aggregate view
  // Since this is an org-level QA page, we fetch without a specific project
  // and show a placeholder for the project selector
  const [selectedProject, setSelectedProject] = useState<string>("");

  const { data: questions, isLoading } = useProjectQuestions(selectedProject || undefined);
  const { data: stats, isLoading: statsLoading } = useQAStats(selectedProject || undefined);

  const allQuestions: QAQuestion[] = questions ?? [];

  const filtered = allQuestions.filter((q) => {
    if (activeTab === "open") return q.status !== "answered" && !q.sla_breached;
    if (activeTab === "answered") return q.status === "answered";
    if (activeTab === "overdue") return q.sla_breached;
    return true;
  });

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "open", label: "Open", count: stats?.open ?? 0 },
    { key: "answered", label: "Answered", count: stats?.answered ?? 0 },
    { key: "overdue", label: "Overdue", count: stats?.sla_breached ?? 0 },
  ];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100">
            <HelpCircle className="h-5 w-5 text-violet-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">Q&A Workflow</h1>
            <p className="text-sm text-neutral-500">Track investor questions, SLA deadlines and official answers</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewForm(true)}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Question
        </button>
      </div>

      {/* Project selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-neutral-700">Project</label>
        <input
          type="text"
          placeholder="Enter project ID to load questions…"
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm w-72 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Stats */}
      {statsLoading ? (
        <div className="grid grid-cols-4 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4">
              <div className="h-3 w-20 bg-neutral-100 rounded mb-2" />
              <div className="h-7 w-16 bg-neutral-200 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Total Questions" value={stats?.total ?? 0} />
          <StatCard label="Open" value={stats?.open ?? 0} />
          <StatCard label="Answered" value={stats?.answered ?? 0} />
          <StatCard
            label="Avg Response Time"
            value={stats?.avg_response_hours != null ? `${stats.avg_response_hours.toFixed(1)}h` : "—"}
            sub="SLA breached: "
          />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-neutral-200">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? "border-primary-600 text-primary-700"
                : "border-transparent text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-2 rounded-full bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-lg border border-neutral-200 bg-white overflow-hidden">
        {isLoading ? (
          <div className="animate-pulse">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="border-b border-neutral-100 px-4 py-4 flex gap-4">
                {Array.from({ length: 7 }).map((_, j) => (
                  <div key={j} className="h-3 bg-neutral-100 rounded flex-1" />
                ))}
              </div>
            ))}
          </div>
        ) : !selectedProject ? (
          <div className="py-16 text-center text-neutral-400 text-sm">
            Enter a project ID above to load questions
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-neutral-400 text-sm">No data available</div>
        ) : (
          <table className="w-full text-left">
            <thead className="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">#</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Question</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Status</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Priority</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Category</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">SLA Deadline</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Created</th>
                <th className="px-4 py-3 text-xs font-semibold text-neutral-500">Answers</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((q) => (
                <QuestionRow key={q.id} q={q} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* New Question modal placeholder */}
      {showNewForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl border border-neutral-200 bg-white p-6 shadow-xl space-y-4">
            <h2 className="text-lg font-semibold text-neutral-900">New Question</h2>
            <p className="text-sm text-neutral-500">
              Use the project-specific Q&A panel to submit questions with full context.
            </p>
            <div className="flex justify-end">
              <button
                onClick={() => setShowNewForm(false)}
                className="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
