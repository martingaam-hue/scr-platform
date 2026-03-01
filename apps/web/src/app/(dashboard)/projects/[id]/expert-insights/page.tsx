"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowLeft,
  Calendar,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Loader2,
  Plus,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
} from "@scr/ui";
import {
  useExpertNotes,
  useCreateExpertNote,
  useDeleteExpertNote,
  useEnrichNote,
  NOTE_TYPES,
  getNoteTypeLabel,
  ENRICHMENT_STATUS_LABELS,
  type CreateExpertNotePayload,
  type ExpertNote,
  type Participant,
} from "@/lib/expert-insights";

// ── Note type badge ───────────────────────────────────────────────────────────

function NoteTypeBadge({ noteType }: { noteType: string }) {
  const variants: Record<string, "info" | "success" | "warning" | "neutral" | "gold"> = {
    call_notes: "info",
    site_visit: "success",
    expert_interview: "gold",
    management_meeting: "warning",
    reference_check: "neutral",
  };
  return (
    <Badge variant={variants[noteType] ?? "neutral"} className="text-xs">
      {getNoteTypeLabel(noteType)}
    </Badge>
  );
}

// ── Enrichment status badge ───────────────────────────────────────────────────

function EnrichmentBadge({ status }: { status: string }) {
  const variants: Record<string, "info" | "success" | "warning" | "error" | "neutral"> = {
    pending: "neutral",
    processing: "info",
    done: "success",
    failed: "error",
  };
  return (
    <Badge variant={variants[status] ?? "neutral"} className="text-xs">
      {status === "processing" && (
        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
      )}
      {ENRICHMENT_STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

// ── Add Note Form ─────────────────────────────────────────────────────────────

function AddNoteModal({
  projectId,
  onClose,
}: {
  projectId: string;
  onClose: () => void;
}) {
  const createNote = useCreateExpertNote(projectId);
  const [form, setForm] = useState<{
    title: string;
    note_type: string;
    content: string;
    meeting_date: string;
    is_private: boolean;
    participants: Participant[];
  }>({
    title: "",
    note_type: "call_notes",
    content: "",
    meeting_date: "",
    is_private: false,
    participants: [],
  });

  const addParticipant = () => {
    setForm((f) => ({
      ...f,
      participants: [...f.participants, { name: "", role: "", org: "" }],
    }));
  };

  const removeParticipant = (i: number) => {
    setForm((f) => ({
      ...f,
      participants: f.participants.filter((_, idx) => idx !== i),
    }));
  };

  const updateParticipant = (
    i: number,
    field: keyof Participant,
    value: string
  ) => {
    setForm((f) => ({
      ...f,
      participants: f.participants.map((p, idx) =>
        idx === i ? { ...p, [field]: value } : p
      ),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload: CreateExpertNotePayload = {
      project_id: projectId,
      note_type: form.note_type,
      title: form.title,
      content: form.content,
      is_private: form.is_private,
    };
    if (form.meeting_date) {
      payload.meeting_date = form.meeting_date;
    }
    if (form.participants.length > 0) {
      payload.participants = form.participants.filter((p) => p.name.trim());
    }
    await createNote.mutateAsync(payload);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-neutral-900 mb-5">
            Add Expert Note
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title */}
            <div>
              <label className="text-sm font-medium text-neutral-700 block mb-1">
                Title *
              </label>
              <input
                type="text"
                required
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="e.g. Management team call — Q4 strategy"
                value={form.title}
                onChange={(e) =>
                  setForm((f) => ({ ...f, title: e.target.value }))
                }
              />
            </div>

            {/* Note type + meeting date */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-neutral-700 block mb-1">
                  Note Type *
                </label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={form.note_type}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, note_type: e.target.value }))
                  }
                >
                  {NOTE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-neutral-700 block mb-1">
                  Meeting Date
                </label>
                <input
                  type="date"
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={form.meeting_date}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, meeting_date: e.target.value }))
                  }
                />
              </div>
            </div>

            {/* Content */}
            <div>
              <label className="text-sm font-medium text-neutral-700 block mb-1">
                Notes *
              </label>
              <textarea
                required
                className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
                rows={6}
                placeholder="Capture the key discussion points, observations, and conclusions..."
                value={form.content}
                onChange={(e) =>
                  setForm((f) => ({ ...f, content: e.target.value }))
                }
              />
            </div>

            {/* Participants */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-neutral-700">
                  Participants
                </label>
                <button
                  type="button"
                  onClick={addParticipant}
                  className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add
                </button>
              </div>
              {form.participants.length > 0 && (
                <div className="space-y-2">
                  {form.participants.map((p, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <input
                        type="text"
                        className="flex-1 border rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
                        placeholder="Name"
                        value={p.name}
                        onChange={(e) =>
                          updateParticipant(i, "name", e.target.value)
                        }
                      />
                      <input
                        type="text"
                        className="flex-1 border rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
                        placeholder="Role"
                        value={p.role}
                        onChange={(e) =>
                          updateParticipant(i, "role", e.target.value)
                        }
                      />
                      <input
                        type="text"
                        className="flex-1 border rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
                        placeholder="Org (optional)"
                        value={p.org ?? ""}
                        onChange={(e) =>
                          updateParticipant(i, "org", e.target.value)
                        }
                      />
                      <button
                        type="button"
                        onClick={() => removeParticipant(i)}
                        className="text-neutral-400 hover:text-red-500"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Private toggle */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_private"
                checked={form.is_private}
                onChange={(e) =>
                  setForm((f) => ({ ...f, is_private: e.target.checked }))
                }
                className="rounded"
              />
              <label
                htmlFor="is_private"
                className="text-sm text-neutral-700 cursor-pointer"
              >
                Mark as private (only visible to your org)
              </label>
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-end pt-2 border-t">
              <Button variant="outline" type="button" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={createNote.isPending}>
                {createNote.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Note
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// ── Note card ─────────────────────────────────────────────────────────────────

function NoteCard({
  note,
  projectId,
}: {
  note: ExpertNote;
  projectId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const deleteNote = useDeleteExpertNote(projectId);
  const enrichNote = useEnrichNote(projectId);

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <button
        className="w-full text-left px-5 py-4 hover:bg-neutral-50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <NoteTypeBadge noteType={note.note_type} />
              <EnrichmentBadge status={note.enrichment_status} />
              {note.is_private && (
                <Badge variant="neutral" className="text-xs">
                  Private
                </Badge>
              )}
            </div>
            <h3 className="font-semibold text-neutral-900 text-sm leading-snug">
              {note.title}
            </h3>
            {note.meeting_date && (
              <p className="text-xs text-neutral-400 mt-0.5 flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(note.meeting_date).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              </p>
            )}
            {note.ai_summary && !expanded && (
              <p className="text-sm text-neutral-600 mt-2 line-clamp-2">
                {note.ai_summary}
              </p>
            )}
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-neutral-400 shrink-0 mt-1" />
          ) : (
            <ChevronDown className="h-4 w-4 text-neutral-400 shrink-0 mt-1" />
          )}
        </div>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="border-t px-5 pb-5 pt-4 space-y-4">
          {/* AI Summary */}
          {note.ai_summary && (
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1.5 flex items-center gap-1">
                <Sparkles className="h-3.5 w-3.5" />
                AI Summary
              </p>
              <p className="text-sm text-neutral-700">{note.ai_summary}</p>
            </div>
          )}

          {/* Key takeaways */}
          {note.key_takeaways && note.key_takeaways.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                <Lightbulb className="h-3.5 w-3.5" />
                Key Takeaways
              </p>
              <ul className="space-y-1.5">
                {note.key_takeaways.map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-neutral-700">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary-500 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Risk factors */}
          {note.risk_factors_identified && note.risk_factors_identified.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                <ShieldAlert className="h-3.5 w-3.5" />
                Risk Factors Identified
              </p>
              <ul className="space-y-1.5">
                {note.risk_factors_identified.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-red-400 shrink-0" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Signal dimensions */}
          {note.linked_signal_dimensions && note.linked_signal_dimensions.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
                Signal Dimensions Affected
              </p>
              <div className="flex flex-wrap gap-1.5">
                {note.linked_signal_dimensions.map((d) => (
                  <Badge key={d} variant="info" className="text-xs">
                    {d.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Participants */}
          {note.participants && note.participants.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                <Users className="h-3.5 w-3.5" />
                Participants
              </p>
              <div className="flex flex-wrap gap-2">
                {note.participants.map((p, i) => (
                  <div
                    key={i}
                    className="text-xs bg-neutral-100 rounded px-2.5 py-1 text-neutral-700"
                  >
                    <span className="font-medium">{p.name}</span>
                    {p.role && <span className="text-neutral-400"> · {p.role}</span>}
                    {p.org && <span className="text-neutral-400"> ({p.org})</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw content */}
          <div>
            <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              Raw Notes
            </p>
            <p className="text-sm text-neutral-700 whitespace-pre-wrap leading-relaxed">
              {note.content}
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex gap-2">
              {note.enrichment_status === "failed" && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => enrichNote.mutate(note.id)}
                  disabled={enrichNote.isPending}
                >
                  {enrichNote.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  Re-enrich
                </Button>
              )}
              {note.enrichment_status === "done" && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => enrichNote.mutate(note.id)}
                  disabled={enrichNote.isPending}
                >
                  {enrichNote.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  Re-enrich
                </Button>
              )}
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                if (confirm("Delete this note?")) {
                  deleteNote.mutate(note.id);
                }
              }}
              disabled={deleteNote.isPending}
              className="text-red-600 hover:bg-red-50 border-red-200"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              Delete
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ExpertInsightsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterType, setFilterType] = useState<string>("all");

  const { data, isLoading, refetch } = useExpertNotes(id);
  const notes = data?.items ?? [];

  const filteredNotes =
    filterType === "all"
      ? notes
      : notes.filter((n) => n.note_type === filterType);

  // Count notes per type for filter badges
  const typeCounts = notes.reduce<Record<string, number>>((acc, n) => {
    acc[n.note_type] = (acc[n.note_type] ?? 0) + 1;
    return acc;
  }, {});

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.push(`/projects/${id}`)}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Project
        </button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Expert Insights
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              Structured notes from expert calls, site visits, and management
              meetings — enriched by AI.
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
            >
              <RefreshCw className="h-4 w-4 mr-1.5" />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setShowAddModal(true)}>
              <Plus className="h-4 w-4 mr-1.5" />
              Add Note
            </Button>
          </div>
        </div>
      </div>

      {/* Filter tabs */}
      {notes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              filterType === "all"
                ? "bg-primary-600 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
            }`}
          >
            All ({notes.length})
          </button>
          {NOTE_TYPES.filter((t) => typeCounts[t.value]).map((t) => (
            <button
              key={t.value}
              onClick={() => setFilterType(t.value)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                filterType === t.value
                  ? "bg-primary-600 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
              }`}
            >
              {t.label} ({typeCounts[t.value]})
            </button>
          ))}
        </div>
      )}

      {/* Stats strip */}
      {notes.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Total Notes</p>
              <p className="text-2xl font-bold text-neutral-900">
                {notes.length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">AI Enriched</p>
              <p className="text-2xl font-bold text-green-600">
                {notes.filter((n) => n.enrichment_status === "done").length}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Risk Factors</p>
              <p className="text-2xl font-bold text-red-600">
                {notes.reduce(
                  (sum, n) => sum + (n.risk_factors_identified?.length ?? 0),
                  0
                )}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Pending</p>
              <p className="text-2xl font-bold text-amber-600">
                {
                  notes.filter(
                    (n) =>
                      n.enrichment_status === "pending" ||
                      n.enrichment_status === "processing"
                  ).length
                }
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty state */}
      {notes.length === 0 && (
        <EmptyState
          icon={<Lightbulb className="h-12 w-12 text-neutral-400" />}
          title="No expert notes yet"
          description="Capture insights from expert calls, site visits, and management meetings. AI will automatically extract key takeaways and risk factors."
          action={
            <Button onClick={() => setShowAddModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add First Note
            </Button>
          }
        />
      )}

      {/* Notes list */}
      {filteredNotes.length > 0 && (
        <div className="space-y-3">
          {filteredNotes.map((note) => (
            <NoteCard key={note.id} note={note} projectId={id} />
          ))}
        </div>
      )}

      {filteredNotes.length === 0 && notes.length > 0 && (
        <p className="text-center text-sm text-neutral-400 py-8">
          No notes matching the selected filter.
        </p>
      )}

      {/* Add note modal */}
      {showAddModal && (
        <AddNoteModal
          projectId={id}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
}
