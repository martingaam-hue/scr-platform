"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Circle,
  Clock,
  FileText,
  Plus,
  RefreshCw,
  Sparkles,
  XCircle,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@scr/ui";
import {
  useProjectChecklist,
  useGenerateChecklist,
  useUpdateItemStatus,
  useAddCustomItem,
  useTriggerAIReview,
  type DDChecklistItemFull,
  type DDChecklistResponse,
  type DDItemStatus,
} from "@/lib/due-diligence";
import { useDocuments } from "@/lib/dataroom";

// ── Status icon ───────────────────────────────────────────────────────────────

function StatusIcon({ status }: { status: DDItemStatus }) {
  switch (status) {
    case "satisfied":
      return <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0" />;
    case "partially_met":
      return <CheckCircle2 className="h-5 w-5 text-amber-500 flex-shrink-0" />;
    case "not_met":
      return <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" />;
    case "in_review":
      return <Clock className="h-5 w-5 text-amber-400 flex-shrink-0" />;
    case "waived":
      return <Circle className="h-5 w-5 text-neutral-300 flex-shrink-0" />;
    default:
      return <Circle className="h-5 w-5 text-neutral-300 flex-shrink-0" />;
  }
}

// ── Priority badge ────────────────────────────────────────────────────────────

function PriorityBadge({ priority }: { priority: string }) {
  if (priority === "required") {
    return (
      <Badge variant="error" className="text-xs font-normal">
        required
      </Badge>
    );
  }
  if (priority === "recommended") {
    return (
      <Badge variant="warning" className="text-xs font-normal">
        recommended
      </Badge>
    );
  }
  return (
    <Badge variant="neutral" className="text-xs font-normal">
      optional
    </Badge>
  );
}

// ── Confidence bar ────────────────────────────────────────────────────────────

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 rounded-full bg-neutral-200">
        <div
          className={`h-1.5 rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-neutral-500">{pct}%</span>
    </div>
  );
}

// ── Checklist item row ────────────────────────────────────────────────────────

function ChecklistItemRow({
  item,
  checklistId,
  projectId,
}: {
  item: DDChecklistItemFull;
  checklistId: string;
  projectId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [notesValue, setNotesValue] = useState(item.reviewer_notes ?? "");
  const updateStatus = useUpdateItemStatus(checklistId);
  const triggerReview = useTriggerAIReview(checklistId);

  const { data: docsData } = useDocuments({
    project_id: projectId,
    page_size: 50,
  });
  const documents = docsData?.items ?? [];

  const handleStatusChange = (newStatus: DDItemStatus) => {
    updateStatus.mutate({ itemId: item.item_id, status: newStatus, notes: notesValue });
  };

  const handleLinkDoc = (docId: string) => {
    updateStatus.mutate({
      itemId: item.item_id,
      status: "in_review",
      document_id: docId,
    });
  };

  const handleAIReview = () => {
    if (item.satisfied_by_document_id) {
      triggerReview.mutate({
        itemId: item.item_id,
        document_id: item.satisfied_by_document_id,
      });
    }
  };

  return (
    <div className="border rounded-lg bg-white">
      {/* Row header */}
      <button
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-neutral-50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <StatusIcon status={item.status} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm text-neutral-900 truncate">
              {item.name}
            </span>
            <PriorityBadge priority={item.priority} />
          </div>
          {item.status === "in_review" && item.satisfied_by_document_id && (
            <p className="text-xs text-amber-600 mt-0.5">Document linked — pending review</p>
          )}
        </div>
        {/* Right-side controls */}
        <div
          className="flex items-center gap-2 flex-shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          {item.status === "pending" && documents.length > 0 && (
            <select
              className="text-xs border rounded px-2 py-1 bg-white text-neutral-700"
              defaultValue=""
              onChange={(e) => e.target.value && handleLinkDoc(e.target.value)}
            >
              <option value="" disabled>
                Link doc...
              </option>
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.name}
                </option>
              ))}
            </select>
          )}
          {item.satisfied_by_document_id && item.status === "in_review" && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleAIReview}
              disabled={triggerReview.isPending}
            >
              {triggerReview.isPending ? (
                <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5 mr-1" />
              )}
              AI Review
            </Button>
          )}
          <select
            className="text-xs border rounded px-2 py-1 bg-white text-neutral-700"
            value={item.status}
            onChange={(e) => handleStatusChange(e.target.value as DDItemStatus)}
          >
            <option value="pending">Pending</option>
            <option value="in_review">In Review</option>
            <option value="satisfied">Satisfied</option>
            <option value="partially_met">Partially Met</option>
            <option value="not_met">Not Met</option>
            <option value="waived">Waived</option>
          </select>
        </div>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t px-4 pb-4 pt-3 space-y-3">
          {item.description && (
            <p className="text-sm text-neutral-600">{item.description}</p>
          )}
          {item.verification_criteria && (
            <div className="bg-neutral-50 rounded p-3">
              <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-1">
                Verification Criteria
              </p>
              <p className="text-sm text-neutral-700">{item.verification_criteria}</p>
            </div>
          )}
          {item.regulatory_reference && (
            <p className="text-xs text-neutral-400">
              Ref: {item.regulatory_reference}
            </p>
          )}
          {item.satisfied_by_document_id && (
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-neutral-400" />
              <span className="text-xs text-neutral-600">
                Linked document: {item.satisfied_by_document_id.slice(0, 8)}...
              </span>
            </div>
          )}
          {item.ai_review_result && !item.ai_review_result.error && (
            <div className="bg-blue-50 rounded p-3 space-y-2">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                AI Review
              </p>
              {typeof item.ai_review_result.confidence === "number" && (
                <ConfidenceBar confidence={item.ai_review_result.confidence} />
              )}
              {item.ai_review_result.summary && (
                <p className="text-sm text-neutral-700">{item.ai_review_result.summary}</p>
              )}
              {item.ai_review_result.gaps && item.ai_review_result.gaps.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-neutral-600 mb-1">Gaps identified:</p>
                  <ul className="space-y-1">
                    {item.ai_review_result.gaps.map((gap, i) => (
                      <li key={i} className="text-xs text-red-700 flex items-start gap-1">
                        <span className="mt-0.5">•</span>
                        <span>{gap}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {item.ai_review_result.recommendation && (
                <p className="text-xs text-neutral-600 italic">
                  {item.ai_review_result.recommendation}
                </p>
              )}
            </div>
          )}
          <div>
            <label className="text-xs font-medium text-neutral-500 block mb-1">
              Reviewer notes
            </label>
            <textarea
              className="w-full text-sm border rounded px-3 py-2 text-neutral-700 resize-none"
              rows={2}
              placeholder="Add notes..."
              value={notesValue}
              onChange={(e) => setNotesValue(e.target.value)}
              onBlur={() => {
                if (notesValue !== item.reviewer_notes) {
                  updateStatus.mutate({
                    itemId: item.item_id,
                    status: item.status,
                    notes: notesValue,
                  });
                }
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Status summary row ────────────────────────────────────────────────────────

function StatusSummary({ checklist }: { checklist: DDChecklistResponse }) {
  const allItems = Object.values(checklist.items_by_category).flat();
  const counts = {
    satisfied: allItems.filter((i) => i.status === "satisfied").length,
    partially_met: allItems.filter((i) => i.status === "partially_met").length,
    in_review: allItems.filter((i) => i.status === "in_review").length,
    not_met: allItems.filter((i) => i.status === "not_met").length,
    pending: allItems.filter((i) => i.status === "pending").length,
  };

  return (
    <div className="flex flex-wrap gap-4 text-sm">
      <span className="flex items-center gap-1.5 text-green-700">
        <CheckCircle2 className="h-4 w-4" />
        <strong>{counts.satisfied}</strong> satisfied
      </span>
      <span className="flex items-center gap-1.5 text-amber-600">
        <CheckCircle2 className="h-4 w-4" />
        <strong>{counts.partially_met}</strong> partially met
      </span>
      <span className="flex items-center gap-1.5 text-amber-500">
        <Clock className="h-4 w-4" />
        <strong>{counts.in_review}</strong> in review
      </span>
      <span className="flex items-center gap-1.5 text-red-600">
        <XCircle className="h-4 w-4" />
        <strong>{counts.not_met}</strong> not met
      </span>
      <span className="flex items-center gap-1.5 text-neutral-400">
        <Circle className="h-4 w-4" />
        <strong>{counts.pending}</strong> pending
      </span>
    </div>
  );
}

// ── Add custom item modal ─────────────────────────────────────────────────────

function AddCustomItemModal({
  checklistId,
  onClose,
}: {
  checklistId: string;
  onClose: () => void;
}) {
  const addItem = useAddCustomItem(checklistId);
  const [form, setForm] = useState({
    name: "",
    category: "legal",
    description: "",
    priority: "recommended" as "required" | "recommended" | "optional",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await addItem.mutateAsync({
      name: form.name,
      category: form.category,
      description: form.description || undefined,
      priority: form.priority,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">
          Add Custom Item
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-neutral-700 block mb-1">
              Name *
            </label>
            <input
              type="text"
              required
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. Stakeholder consultation report"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-neutral-700 block mb-1">
              Category *
            </label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              value={form.category}
              onChange={(e) =>
                setForm((f) => ({ ...f, category: e.target.value }))
              }
            >
              <option value="legal">Legal</option>
              <option value="financial">Financial</option>
              <option value="technical">Technical</option>
              <option value="environmental">Environmental</option>
              <option value="regulatory">Regulatory</option>
              <option value="insurance">Insurance</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-neutral-700 block mb-1">
              Description
            </label>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
              rows={3}
              placeholder="Optional description..."
              value={form.description}
              onChange={(e) =>
                setForm((f) => ({ ...f, description: e.target.value }))
              }
            />
          </div>
          <div>
            <label className="text-sm font-medium text-neutral-700 block mb-1">
              Priority
            </label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              value={form.priority}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  priority: e.target.value as "required" | "recommended" | "optional",
                }))
              }
            >
              <option value="required">Required</option>
              <option value="recommended">Recommended</option>
              <option value="optional">Optional</option>
            </select>
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <Button variant="outline" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={addItem.isPending}>
              {addItem.isPending ? "Adding..." : "Add Item"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const CATEGORIES = [
  "legal",
  "financial",
  "technical",
  "environmental",
  "regulatory",
  "insurance",
] as const;

const CATEGORY_LABELS: Record<string, string> = {
  legal: "Legal",
  financial: "Financial",
  technical: "Technical",
  environmental: "Environmental",
  regulatory: "Regulatory",
  insurance: "Insurance",
};

export default function DueDiligencePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [showAddModal, setShowAddModal] = useState(false);

  const { data: checklist, isLoading, refetch } = useProjectChecklist(id);
  const generateChecklist = useGenerateChecklist();

  const handleGenerate = async () => {
    await generateChecklist.mutateAsync({ project_id: id });
    refetch();
  };

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
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Due Diligence Checklist
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              Track and manage due diligence requirements for this project.
            </p>
          </div>
          {checklist && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => setShowAddModal(true)}
                size="sm"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Item
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerate}
                disabled={generateChecklist.isPending}
              >
                <RefreshCw
                  className={`h-4 w-4 mr-1 ${generateChecklist.isPending ? "animate-spin" : ""}`}
                />
                Refresh Matches
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* No checklist — CTA */}
      {!checklist && (
        <EmptyState
          icon={<FileText className="h-12 w-12 text-neutral-400" />}
          title="No checklist generated yet"
          description="Generate a smart due diligence checklist tailored to this project's type and stage."
          action={
            <Button
              onClick={handleGenerate}
              disabled={generateChecklist.isPending}
            >
              {generateChecklist.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Checklist
                </>
              )}
            </Button>
          }
        />
      )}

      {/* Checklist exists */}
      {checklist && (
        <>
          {/* Progress bar */}
          <Card>
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-neutral-700">
                    Overall Progress
                  </p>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {checklist.completed_items} of {checklist.total_items} items complete
                  </p>
                </div>
                <span className="text-2xl font-bold text-neutral-900">
                  {checklist.completion_percentage.toFixed(0)}%
                </span>
              </div>
              <div className="h-3 rounded-full bg-neutral-200">
                <div
                  className="h-3 rounded-full bg-primary-600 transition-all"
                  style={{ width: `${checklist.completion_percentage}%` }}
                />
              </div>
              <div className="mt-4">
                <StatusSummary checklist={checklist} />
              </div>
            </CardContent>
          </Card>

          {/* Category tabs */}
          <Tabs defaultValue="legal">
            <TabsList className="flex-wrap">
              {CATEGORIES.map((cat) => {
                const items = checklist.items_by_category[cat] ?? [];
                const satisfied = items.filter(
                  (i) => i.status === "satisfied" || i.status === "partially_met"
                ).length;
                return (
                  <TabsTrigger key={cat} value={cat}>
                    {CATEGORY_LABELS[cat]}
                    {items.length > 0 && (
                      <span className="ml-1.5 text-xs text-neutral-400">
                        {satisfied}/{items.length}
                      </span>
                    )}
                  </TabsTrigger>
                );
              })}
            </TabsList>

            {CATEGORIES.map((cat) => {
              const items = checklist.items_by_category[cat] ?? [];
              return (
                <TabsContent key={cat} value={cat} className="mt-4">
                  {items.length === 0 ? (
                    <p className="text-sm text-neutral-400 text-center py-8">
                      No items in this category.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {items.map((item) => (
                        <ChecklistItemRow
                          key={item.item_id}
                          item={item}
                          checklistId={checklist.id}
                          projectId={id}
                        />
                      ))}
                    </div>
                  )}

                  {/* Custom items for this category */}
                  {checklist.custom_items
                    .filter((ci) => ci.category === cat)
                    .map((ci) => (
                      <div
                        key={ci.id}
                        className="border rounded-lg bg-white flex items-center gap-3 p-4 mt-2"
                      >
                        <StatusIcon status={ci.status} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm text-neutral-900">
                              {ci.name}
                            </span>
                            <PriorityBadge priority={ci.priority} />
                            <Badge variant="neutral" className="text-xs">
                              custom
                            </Badge>
                          </div>
                          {ci.description && (
                            <p className="text-xs text-neutral-500 mt-0.5">
                              {ci.description}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                </TabsContent>
              );
            })}
          </Tabs>
        </>
      )}

      {/* Add custom item modal */}
      {showAddModal && checklist && (
        <AddCustomItemModal
          checklistId={checklist.id}
          onClose={() => setShowAddModal(false)}
        />
      )}
    </div>
  );
}
