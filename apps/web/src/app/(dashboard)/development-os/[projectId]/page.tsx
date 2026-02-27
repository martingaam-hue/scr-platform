"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  Package,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState } from "@scr/ui";

import {
  milestoneStatusColor,
  milestoneStatusLabel,
  procurementStatusLabel,
  useCreateMilestone,
  useDeleteMilestone,
  useDevelopmentOS,
  useUpdateMilestone,
  type ConstructionPhase,
  type Milestone,
  type MilestoneCreate,
  type MilestoneUpdate,
  type ProcurementItem,
} from "@/lib/development-os";

// ── Progress Bar ──────────────────────────────────────────────────────────────

function ProgressBar({
  pct,
  color = "bg-blue-500",
}: {
  pct: number;
  color?: string;
}) {
  return (
    <div className="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    completed: "bg-green-100 text-green-700",
    in_progress: "bg-blue-100 text-blue-700",
    not_started: "bg-neutral-100 text-neutral-600",
    delayed: "bg-red-100 text-red-700",
    blocked: "bg-orange-100 text-orange-700",
  };
  return (
    <span
      className={`text-xs font-medium px-2 py-0.5 rounded-full ${map[status] ?? "bg-neutral-100 text-neutral-600"}`}
    >
      {milestoneStatusLabel(status)}
    </span>
  );
}

// ── Edit Milestone Modal ──────────────────────────────────────────────────────

function EditMilestoneModal({
  milestone,
  projectId,
  onClose,
}: {
  milestone: Milestone;
  projectId: string;
  onClose: () => void;
}) {
  const updateMutation = useUpdateMilestone(projectId);
  const [form, setForm] = useState<MilestoneUpdate>({
    title: milestone.title,
    description: milestone.description ?? "",
    due_date: milestone.due_date ?? "",
    status: milestone.status,
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    updateMutation.mutate(
      { milestoneId: milestone.id, body: form },
      { onSuccess: onClose },
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-5">
          <h2 className="text-base font-semibold mb-4">Edit Milestone</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Title
              </label>
              <input
                type="text"
                value={form.title ?? ""}
                onChange={(e) =>
                  setForm((p) => ({ ...p, title: e.target.value }))
                }
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Description
              </label>
              <textarea
                value={form.description ?? ""}
                onChange={(e) =>
                  setForm((p) => ({ ...p, description: e.target.value }))
                }
                rows={2}
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  Due Date
                </label>
                <input
                  type="date"
                  value={form.due_date ?? ""}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, due_date: e.target.value }))
                  }
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  Status
                </label>
                <select
                  value={form.status ?? "not_started"}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, status: e.target.value }))
                  }
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {[
                    "not_started",
                    "in_progress",
                    "completed",
                    "delayed",
                    "blocked",
                  ].map((s) => (
                    <option key={s} value={s}>
                      {milestoneStatusLabel(s)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                type="submit"
                disabled={updateMutation.isPending}
                className="flex-1"
              >
                {updateMutation.isPending && (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                )}
                Save
              </Button>
              <Button variant="outline" type="button" onClick={onClose}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Milestone Row ─────────────────────────────────────────────────────────────

function MilestoneRow({
  milestone,
  projectId,
}: {
  milestone: Milestone;
  projectId: string;
}) {
  const [editing, setEditing] = useState(false);
  const deleteMutation = useDeleteMilestone(projectId);

  return (
    <>
      <div className="flex items-center gap-3 py-2.5 border-b border-neutral-50 last:border-0">
        <div
          className={`shrink-0 ${milestoneStatusColor(milestone.status)}`}
        >
          {milestone.status === "completed" ? (
            <CheckCircle2 size={16} />
          ) : (
            <Clock size={16} />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neutral-800 truncate">
            {milestone.title}
          </p>
          {milestone.description && (
            <p className="text-xs text-neutral-400 truncate">
              {milestone.description}
            </p>
          )}
        </div>
        {milestone.due_date && (
          <span className="text-xs text-neutral-400 shrink-0">
            {new Date(milestone.due_date).toLocaleDateString()}
          </span>
        )}
        <StatusBadge status={milestone.status} />
        <button
          onClick={() => setEditing(true)}
          className="p-1 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600"
        >
          <Pencil size={13} />
        </button>
        <button
          onClick={() => deleteMutation.mutate(milestone.id)}
          className="p-1 rounded hover:bg-red-50 text-neutral-400 hover:text-red-500"
        >
          <Trash2 size={13} />
        </button>
      </div>
      {editing && (
        <EditMilestoneModal
          milestone={milestone}
          projectId={projectId}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}

// ── Phase Accordion ───────────────────────────────────────────────────────────

function PhaseAccordion({
  phase,
  projectId,
}: {
  phase: ConstructionPhase;
  projectId: string;
}) {
  const [open, setOpen] = useState(phase.status === "in_progress");
  const [addingMilestone, setAddingMilestone] = useState(false);
  const createMutation = useCreateMilestone(projectId);
  const [newTitle, setNewTitle] = useState("");
  const [newDue, setNewDue] = useState("");

  const phaseColor =
    phase.status === "completed"
      ? "bg-green-500"
      : phase.status === "in_progress"
        ? "bg-blue-500"
        : "bg-neutral-300";

  function handleAddMilestone(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    const body: MilestoneCreate = {
      title: newTitle.trim(),
      due_date: newDue || undefined,
      status: "not_started",
    };
    createMutation.mutate(body, {
      onSuccess: () => {
        setNewTitle("");
        setNewDue("");
        setAddingMilestone(false);
      },
    });
  }

  return (
    <div className="rounded-lg border border-neutral-200 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-neutral-50 hover:bg-neutral-100 transition-colors"
      >
        <div className={`w-2 h-2 rounded-full ${phaseColor}`} />
        <span className="font-medium text-neutral-800 text-sm flex-1 text-left">
          {phase.phase_name}
        </span>
        <div className="flex items-center gap-3">
          <div className="w-24">
            <ProgressBar pct={phase.completion_pct} color={phaseColor} />
          </div>
          <span className="text-xs text-neutral-500 w-10 text-right">
            {phase.completion_pct.toFixed(0)}%
          </span>
          <span className="text-xs text-neutral-400">
            {phase.milestones.length} milestone
            {phase.milestones.length !== 1 ? "s" : ""}
          </span>
        </div>
        {open ? (
          <ChevronUp size={16} className="text-neutral-400" />
        ) : (
          <ChevronDown size={16} className="text-neutral-400" />
        )}
      </button>

      {open && (
        <div className="px-4 py-2">
          {phase.milestones.length === 0 ? (
            <p className="text-xs text-neutral-400 py-2 italic">
              No milestones in this phase.
            </p>
          ) : (
            phase.milestones.map((m) => (
              <MilestoneRow key={m.id} milestone={m} projectId={projectId} />
            ))
          )}

          {/* Add milestone inline */}
          {addingMilestone ? (
            <form
              onSubmit={handleAddMilestone}
              className="flex gap-2 mt-2 pt-2 border-t border-neutral-100"
            >
              <input
                autoFocus
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Milestone title…"
                className="flex-1 rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="date"
                value={newDue}
                onChange={(e) => setNewDue(e.target.value)}
                className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <Button type="submit" disabled={createMutation.isPending}>
                Add
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setAddingMilestone(false)}
              >
                Cancel
              </Button>
            </form>
          ) : (
            <button
              onClick={() => setAddingMilestone(true)}
              className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 mt-2 pt-2 border-t border-neutral-100"
            >
              <Plus size={12} />
              Add milestone
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Procurement Table ─────────────────────────────────────────────────────────

function ProcurementTable({ items }: { items: ProcurementItem[] }) {
  const statusColors: Record<string, string> = {
    contracted: "text-green-600",
    delivered: "text-green-700",
    negotiating: "text-blue-600",
    rfq_sent: "text-amber-600",
    pending: "text-neutral-400",
  };

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200">
      <table className="w-full text-sm text-left">
        <thead className="bg-neutral-50 border-b border-neutral-200">
          <tr>
            <th className="px-4 py-2.5 font-medium text-neutral-600">Item</th>
            <th className="px-4 py-2.5 font-medium text-neutral-600">
              Category
            </th>
            <th className="px-4 py-2.5 font-medium text-neutral-600">
              Vendor
            </th>
            <th className="px-4 py-2.5 font-medium text-neutral-600 text-right">
              Est. Cost
            </th>
            <th className="px-4 py-2.5 font-medium text-neutral-600">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className="border-b border-neutral-100 hover:bg-neutral-50"
            >
              <td className="px-4 py-2.5 font-medium">{item.name}</td>
              <td className="px-4 py-2.5 text-neutral-500">{item.category}</td>
              <td className="px-4 py-2.5 text-neutral-500">
                {item.vendor ?? "TBD"}
              </td>
              <td className="px-4 py-2.5 text-right">
                {item.estimated_cost_usd
                  ? `$${(item.estimated_cost_usd / 1_000).toFixed(0)}K`
                  : "—"}
              </td>
              <td
                className={`px-4 py-2.5 font-medium ${statusColors[item.status] ?? "text-neutral-500"}`}
              >
                {procurementStatusLabel(item.status)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function DevelopmentOSPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.projectId as string;

  const { data, isLoading, isError } = useDevelopmentOS(projectId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 max-w-5xl mx-auto">
        <EmptyState
          icon={<Calendar size={40} className="text-neutral-400" />}
          title="Project not found"
          description="The project could not be loaded. Check the project ID."
        />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Back + header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => router.back()}
          className="mt-1 p-1.5 rounded-lg hover:bg-neutral-100 text-neutral-500"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <p className="text-xs text-neutral-400 font-medium uppercase tracking-wide mb-0.5">
            Development OS
          </p>
          <h1 className="text-2xl font-bold text-neutral-900">
            {data.project_name}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            <Badge variant="neutral">{data.project_stage.replace(/_/g, " ")}</Badge>
            <span className="text-sm text-neutral-500">
              {data.overall_completion_pct.toFixed(0)}% complete
            </span>
          </div>
        </div>
      </div>

      {/* Overall progress */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-neutral-700">
              Overall Completion
            </p>
            <span className="text-xl font-bold text-blue-600">
              {data.overall_completion_pct.toFixed(0)}%
            </span>
          </div>
          <ProgressBar pct={data.overall_completion_pct} color="bg-blue-500" />
        </CardContent>
      </Card>

      {/* Next milestone callout */}
      {data.next_milestone && (
        <div className="rounded-lg border-l-4 border-l-amber-400 border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3">
          <Calendar size={18} className="text-amber-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-800">
              Next Milestone
            </p>
            <p className="text-sm text-amber-700">
              {data.next_milestone.title}
            </p>
            <p className="text-xs text-amber-500 mt-0.5">
              Due:{" "}
              {data.next_milestone.due_date
                ? new Date(data.next_milestone.due_date).toLocaleDateString()
                : "TBD"}
              {data.days_to_next_milestone !== null && (
                <span className="ml-2">
                  ({data.days_to_next_milestone > 0
                    ? `in ${data.days_to_next_milestone} days`
                    : `${Math.abs(data.days_to_next_milestone)} days overdue`})
                </span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Phase accordions */}
      <div className="space-y-3">
        <h2 className="text-base font-semibold text-neutral-800">
          Construction Phases
        </h2>
        {data.phases.map((phase) => (
          <PhaseAccordion
            key={phase.phase_name}
            phase={phase}
            projectId={projectId}
          />
        ))}
      </div>

      {/* Procurement */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Package size={18} className="text-neutral-500" />
          <h2 className="text-base font-semibold text-neutral-800">
            Procurement
          </h2>
        </div>
        {data.procurement.length > 0 ? (
          <ProcurementTable items={data.procurement} />
        ) : (
          <p className="text-sm text-neutral-400 italic">
            No procurement items.
          </p>
        )}
      </div>

      {/* Last updated */}
      <p className="text-xs text-neutral-400 text-right">
        Last updated:{" "}
        {new Date(data.last_updated).toLocaleString()}
      </p>
    </div>
  );
}
