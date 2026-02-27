"use client";

import { useState } from "react";
import { Network, Plus, Loader2, Star, ArrowRight } from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState } from "@scr/ui";

import {
  ecosystemKeys,
  engagementStatusColor,
  RELATIONSHIP_TYPES,
  STAKEHOLDER_TYPES,
  stakeholderTypeColor,
  useAddRelationship,
  useAddStakeholder,
  useEcosystem,
  type RelationshipCreate,
  type StakeholderCreate,
  type StakeholderEdge,
  type StakeholderNode,
} from "@/lib/ecosystem";

// ── Strength Stars ────────────────────────────────────────────────────────────

function StrengthStars({ strength }: { strength: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <Star
          key={i}
          size={12}
          className={
            i < strength ? "text-amber-400 fill-amber-400" : "text-neutral-200"
          }
        />
      ))}
    </div>
  );
}

// ── Stakeholder Card ──────────────────────────────────────────────────────────

function StakeholderCard({ node }: { node: StakeholderNode }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-neutral-900 text-sm truncate">
                {node.name}
              </h3>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${stakeholderTypeColor(node.type)}`}
              >
                {node.type}
              </span>
              {node.sub_type && (
                <span className="text-xs text-neutral-400 bg-neutral-100 px-2 py-0.5 rounded-full">
                  {node.sub_type}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1.5">
              <StrengthStars strength={node.relationship_strength} />
              <span
                className={`text-xs font-medium ${engagementStatusColor(node.engagement_status)}`}
              >
                {node.engagement_status}
              </span>
            </div>
            {node.tags.length > 0 && (
              <div className="flex gap-1 mt-1.5 flex-wrap">
                {node.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Edge Row ──────────────────────────────────────────────────────────────────

function EdgeRow({
  edge,
  nodeMap,
}: {
  edge: StakeholderEdge;
  nodeMap: Map<string, string>;
}) {
  const sourceLabel = nodeMap.get(edge.source) ?? edge.source;
  const targetLabel = nodeMap.get(edge.target) ?? edge.target;

  return (
    <div className="flex items-center gap-2 py-2.5 border-b border-neutral-50 last:border-0 text-sm">
      <span className="text-neutral-700 font-medium truncate max-w-[160px]">
        {sourceLabel}
      </span>
      <ArrowRight size={14} className="text-neutral-400 shrink-0" />
      <span className="text-xs text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full shrink-0">
        {edge.relationship_type.replace(/_/g, " ")}
      </span>
      <ArrowRight size={14} className="text-neutral-400 shrink-0" />
      <span className="text-neutral-700 font-medium truncate max-w-[160px]">
        {targetLabel}
      </span>
      <span className="ml-auto text-xs text-neutral-400 shrink-0">
        strength {edge.weight}/10
      </span>
    </div>
  );
}

// ── Add Stakeholder Form ──────────────────────────────────────────────────────

function AddStakeholderForm({
  projectId,
  onClose,
}: {
  projectId: string;
  onClose: () => void;
}) {
  const addMutation = useAddStakeholder(projectId);
  const [form, setForm] = useState<StakeholderCreate>({
    name: "",
    type: "investor",
    relationship_strength: 3,
    engagement_status: "active",
    tags: [],
  });
  const [tagInput, setTagInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return;
    addMutation.mutate(form, { onSuccess: onClose });
  }

  function addTag() {
    if (!tagInput.trim()) return;
    setForm((p) => ({ ...p, tags: [...(p.tags ?? []), tagInput.trim()] }));
    setTagInput("");
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-5">
          <h2 className="text-base font-semibold mb-4">Add Stakeholder</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                autoFocus
                type="text"
                value={form.name}
                onChange={(e) =>
                  setForm((p) => ({ ...p, name: e.target.value }))
                }
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  Type
                </label>
                <select
                  value={form.type}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, type: e.target.value }))
                  }
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {STAKEHOLDER_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  Engagement
                </label>
                <select
                  value={form.engagement_status}
                  onChange={(e) =>
                    setForm((p) => ({
                      ...p,
                      engagement_status: e.target.value,
                    }))
                  }
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {["active", "passive", "at_risk", "churned"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Relationship Strength (1–5)
              </label>
              <input
                type="range"
                min={1}
                max={5}
                value={form.relationship_strength}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    relationship_strength: parseInt(e.target.value),
                  }))
                }
                className="w-full"
              />
              <div className="flex justify-between text-xs text-neutral-400 mt-0.5">
                <span>Weak (1)</span>
                <span className="font-medium text-neutral-700">
                  {form.relationship_strength}
                </span>
                <span>Strong (5)</span>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Tags
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                  placeholder="Add tag…"
                  className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Button type="button" variant="outline" onClick={addTag}>
                  Add
                </Button>
              </div>
              {(form.tags ?? []).length > 0 && (
                <div className="flex gap-1 mt-2 flex-wrap">
                  {(form.tags ?? []).map((tag) => (
                    <span
                      key={tag}
                      className="text-xs bg-neutral-100 text-neutral-600 px-2 py-0.5 rounded-full flex items-center gap-1"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() =>
                          setForm((p) => ({
                            ...p,
                            tags: p.tags?.filter((t) => t !== tag),
                          }))
                        }
                        className="text-neutral-400 hover:text-red-500"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                type="submit"
                disabled={addMutation.isPending}
                className="flex-1"
              >
                {addMutation.isPending && (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                )}
                Add Stakeholder
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

// ── Add Relationship Form ─────────────────────────────────────────────────────

function AddRelationshipForm({
  projectId,
  nodes,
  onClose,
}: {
  projectId: string;
  nodes: StakeholderNode[];
  onClose: () => void;
}) {
  const addMutation = useAddRelationship(projectId);
  const [form, setForm] = useState<RelationshipCreate>({
    source_id: nodes[0]?.id ?? "",
    target_id: nodes[1]?.id ?? "",
    relationship_type: "investment",
    weight: 5,
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    addMutation.mutate(form, { onSuccess: onClose });
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardContent className="pt-5">
          <h2 className="text-base font-semibold mb-4">Add Relationship</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  From
                </label>
                <select
                  value={form.source_id}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, source_id: e.target.value }))
                  }
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-500 mb-1">
                  To
                </label>
                <select
                  value={form.target_id}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, target_id: e.target.value }))
                  }
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Relationship Type
              </label>
              <select
                value={form.relationship_type}
                onChange={(e) =>
                  setForm((p) => ({ ...p, relationship_type: e.target.value }))
                }
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {RELATIONSHIP_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Weight (1–10): {form.weight}
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={form.weight}
                onChange={(e) =>
                  setForm((p) => ({ ...p, weight: parseInt(e.target.value) }))
                }
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1">
                Description (optional)
              </label>
              <input
                type="text"
                value={form.description ?? ""}
                onChange={(e) =>
                  setForm((p) => ({ ...p, description: e.target.value }))
                }
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                type="submit"
                disabled={addMutation.isPending}
                className="flex-1"
              >
                {addMutation.isPending && (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                )}
                Add Relationship
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

// ── Summary Stats ─────────────────────────────────────────────────────────────

function SummaryStats({
  summary,
}: {
  summary: Record<string, unknown>;
}) {
  const byType = (summary.by_type ?? {}) as Record<string, number>;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
        <p className="text-xs text-neutral-500">Total Stakeholders</p>
        <p className="text-2xl font-bold text-neutral-900">
          {Number(summary.total_stakeholders ?? 0)}
        </p>
      </div>
      <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
        <p className="text-xs text-neutral-500">Avg. Relationship Strength</p>
        <p className="text-2xl font-bold text-neutral-900">
          {Number(summary.avg_strength ?? 0).toFixed(1)}
          <span className="text-sm text-neutral-400 ml-0.5">/5</span>
        </p>
      </div>
      {Object.entries(byType)
        .slice(0, 2)
        .map(([type, count]) => (
          <div
            key={type}
            className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3"
          >
            <p className="text-xs text-neutral-500 capitalize">{type}s</p>
            <p className="text-2xl font-bold text-neutral-900">{count}</p>
          </div>
        ))}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function EcosystemPage() {
  const { data, isLoading } = useEcosystem();
  const [showAddStakeholder, setShowAddStakeholder] = useState(false);
  const [showAddRelationship, setShowAddRelationship] = useState(false);

  // For org-level ecosystem, we use org_id as the "project" context for mutations.
  // The backend will use entity_id = org_id when no project_id is given.
  const entityId = data?.org_id ?? "";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 size={32} className="animate-spin text-purple-600" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-100">
            <Network size={22} className="text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Ecosystem Map
            </h1>
            <p className="text-sm text-neutral-500">
              Stakeholder relationships and network analysis
            </p>
          </div>
        </div>
        {data && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowAddRelationship(true)}
              disabled={data.nodes.length < 2}
            >
              <Plus size={14} className="mr-1.5" />
              Add Relationship
            </Button>
            <Button onClick={() => setShowAddStakeholder(true)}>
              <Plus size={14} className="mr-1.5" />
              Add Stakeholder
            </Button>
          </div>
        )}
      </div>

      {/* Empty state */}
      {!data && !isLoading && (
        <EmptyState
          icon={<Network size={40} className="text-neutral-400" />}
          title="No ecosystem data"
          description="The ecosystem map will be created automatically."
        />
      )}

      {data && (
        <>
          {/* Summary */}
          <SummaryStats summary={data.summary} />

          {/* Stakeholder grid */}
          <div>
            <h2 className="text-base font-semibold text-neutral-800 mb-3">
              Stakeholders ({data.nodes.length})
            </h2>
            {data.nodes.length === 0 ? (
              <p className="text-sm text-neutral-400 italic">
                No stakeholders yet. Add one above.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {data.nodes.map((node) => (
                  <StakeholderCard key={node.id} node={node} />
                ))}
              </div>
            )}
          </div>

          {/* Relationships */}
          <div>
            <h2 className="text-base font-semibold text-neutral-800 mb-3">
              Relationships ({data.edges.length})
            </h2>
            {data.edges.length === 0 ? (
              <p className="text-sm text-neutral-400 italic">
                No relationships defined yet.
              </p>
            ) : (
              <Card>
                <CardContent className="pt-3 pb-1">
                  {(() => {
                    const nodeMap = new Map(
                      data.nodes.map((n) => [n.id, n.name]),
                    );
                    return data.edges.map((edge, i) => (
                      <EdgeRow key={i} edge={edge} nodeMap={nodeMap} />
                    ));
                  })()}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Last updated */}
          <p className="text-xs text-neutral-400 text-right">
            Last updated: {new Date(data.last_updated).toLocaleString()}
          </p>
        </>
      )}

      {/* Modals */}
      {showAddStakeholder && data && (
        <AddStakeholderForm
          projectId={entityId}
          onClose={() => setShowAddStakeholder(false)}
        />
      )}
      {showAddRelationship && data && data.nodes.length >= 2 && (
        <AddRelationshipForm
          projectId={entityId}
          nodes={data.nodes}
          onClose={() => setShowAddRelationship(false)}
        />
      )}
    </div>
  );
}
