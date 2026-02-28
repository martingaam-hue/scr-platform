"use client";

import { useState } from "react";
import {
  Activity,
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  ToggleLeft,
  ToggleRight,
  Zap,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Badge, Button, Card, CardContent, EmptyState, cn } from "@scr/ui";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PromptTemplate {
  id: string;
  task_type: string;
  version: number;
  name: string;
  system_prompt: string | null;
  user_prompt_template: string;
  output_format_instruction: string | null;
  variables_schema: Record<string, unknown>;
  model_override: string | null;
  temperature_override: number | null;
  max_tokens_override: number | null;
  is_active: boolean;
  traffic_percentage: number;
  total_uses: number;
  avg_confidence: number | null;
  positive_feedback_rate: number | null;
  notes: string | null;
  created_at: string | null;
}

interface PromptsResponse {
  prompts: Record<string, PromptTemplate[]>;
  total_task_types: number;
}

// ── Query hooks ───────────────────────────────────────────────────────────────

const PROMPTS_KEY = ["admin", "prompts"] as const;

function usePrompts() {
  return useQuery({
    queryKey: PROMPTS_KEY,
    queryFn: () => api.get<PromptsResponse>("/admin/prompts").then((r) => r.data),
  });
}

function useActivate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.put(`/admin/prompts/${id}/activate`, null, {
        params: { traffic_percentage: 100 },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: PROMPTS_KEY }),
  });
}

function useDeactivate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.put(`/admin/prompts/${id}/deactivate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: PROMPTS_KEY }),
  });
}

function useCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      task_type: string;
      name: string;
      user_prompt_template: string;
      system_prompt?: string;
      notes?: string;
    }) => api.post("/admin/prompts", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: PROMPTS_KEY }),
  });
}

// ── Template row ──────────────────────────────────────────────────────────────

function TemplateRow({ t }: { t: PromptTemplate }) {
  const [expanded, setExpanded] = useState(false);
  const { mutate: activate, isPending: activating } = useActivate();
  const { mutate: deactivate, isPending: deactivating } = useDeactivate();

  return (
    <div className="border-b last:border-0">
      <div
        className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 cursor-pointer"
        onClick={() => setExpanded((e) => !e)}
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900 truncate">
              v{t.version} — {t.name}
            </span>
            {t.is_active && (
              <Badge variant="success" className="text-[10px]">
                Active
              </Badge>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            {t.model_override ?? "default model"} ·{" "}
            {t.total_uses} uses
            {t.avg_confidence != null && (
              <> · {(t.avg_confidence * 100).toFixed(0)}% conf</>
            )}
            {t.positive_feedback_rate != null && (
              <> · {(t.positive_feedback_rate * 100).toFixed(0)}% pos</>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {t.traffic_percentage > 0 && (
            <span className="text-xs text-gray-400">{t.traffic_percentage}% traffic</span>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (t.is_active) {
                deactivate(t.id);
              } else {
                activate(t.id);
              }
            }}
            disabled={activating || deactivating}
            className="p-1 rounded hover:bg-gray-100"
            title={t.is_active ? "Deactivate" : "Activate"}
          >
            {activating || deactivating ? (
              <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
            ) : t.is_active ? (
              <ToggleRight className="h-4 w-4 text-green-500" />
            ) : (
              <ToggleLeft className="h-4 w-4 text-gray-400" />
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 bg-gray-50/50">
          {t.system_prompt && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1">
                System Prompt
              </p>
              <pre className="text-xs text-gray-700 bg-white border rounded p-3 whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">
                {t.system_prompt}
              </pre>
            </div>
          )}
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1">
              User Prompt Template
            </p>
            <pre className="text-xs text-gray-700 bg-white border rounded p-3 whitespace-pre-wrap font-mono leading-relaxed max-h-48 overflow-y-auto">
              {t.user_prompt_template}
            </pre>
          </div>
          {t.output_format_instruction && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1">
                Output Format
              </p>
              <pre className="text-xs text-gray-700 bg-white border rounded p-3 whitespace-pre-wrap font-mono leading-relaxed">
                {t.output_format_instruction}
              </pre>
            </div>
          )}
          {t.notes && (
            <p className="text-xs text-gray-500 italic">{t.notes}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Task type group ───────────────────────────────────────────────────────────

function TaskTypeGroup({
  taskType,
  templates,
  onNewVersion,
}: {
  taskType: string;
  templates: PromptTemplate[];
  onNewVersion: (taskType: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const activeTemplate = templates.find((t) => t.is_active);

  return (
    <Card>
      <CardContent className="p-0">
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b cursor-pointer hover:bg-gray-50"
          onClick={() => setCollapsed((c) => !c)}
        >
          <div className="flex items-center gap-3">
            {collapsed ? (
              <ChevronRight className="h-4 w-4 text-gray-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-400" />
            )}
            <div>
              <p className="text-sm font-semibold text-gray-900 font-mono">
                {taskType}
              </p>
              <p className="text-xs text-gray-400">
                {templates.length} version{templates.length !== 1 ? "s" : ""}
                {activeTemplate && ` · v${activeTemplate.version} active`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {activeTemplate ? (
              <Badge variant="success" className="text-[10px]">
                <Zap className="h-2.5 w-2.5 mr-1" />
                Live
              </Badge>
            ) : (
              <Badge variant="neutral" className="text-[10px]">
                Fallback
              </Badge>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onNewVersion(taskType);
              }}
              className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700"
              title="Add new version"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {!collapsed && (
          <div>
            {templates.map((t) => (
              <TemplateRow key={t.id} t={t} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Create dialog ─────────────────────────────────────────────────────────────

function CreateDialog({
  defaultTaskType,
  onClose,
}: {
  defaultTaskType: string;
  onClose: () => void;
}) {
  const { mutate: create, isPending } = useCreate();
  const [form, setForm] = useState({
    task_type: defaultTaskType,
    name: "",
    system_prompt: "",
    user_prompt_template: "",
    notes: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    create(
      {
        task_type: form.task_type,
        name: form.name,
        user_prompt_template: form.user_prompt_template,
        system_prompt: form.system_prompt || undefined,
        notes: form.notes || undefined,
      },
      { onSuccess: onClose }
    );
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h2 className="text-lg font-semibold text-gray-900">New Prompt Version</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            New versions start inactive at 0% traffic. Activate when ready.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Task Type <span className="text-red-500">*</span>
              </label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                value={form.task_type}
                onChange={(e) => setForm((f) => ({ ...f, task_type: e.target.value }))}
                placeholder="e.g. score_quality"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Version Name <span className="text-red-500">*</span>
              </label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Improved scoring v2"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              System Prompt
            </label>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
              rows={3}
              value={form.system_prompt}
              onChange={(e) => setForm((f) => ({ ...f, system_prompt: e.target.value }))}
              placeholder="Optional system instructions..."
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              User Prompt Template <span className="text-red-500">*</span>
            </label>
            <p className="text-[10px] text-gray-400 mb-1">
              Use {"{{variable_name}}"} for dynamic values.
            </p>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
              rows={8}
              value={form.user_prompt_template}
              onChange={(e) =>
                setForm((f) => ({ ...f, user_prompt_template: e.target.value }))
              }
              placeholder="Analyse the following document...{{document_text}}"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Notes
            </label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="What changed in this version?"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <Button type="submit" className="flex-1" disabled={isPending}>
              {isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Create Version
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminPromptsPage() {
  const { data, isLoading } = usePrompts();
  const [createFor, setCreateFor] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const prompts = data?.prompts ?? {};
  const taskTypes = Object.keys(prompts).filter((t) =>
    t.toLowerCase().includes(search.toLowerCase())
  );

  const totalActive = Object.values(prompts)
    .flat()
    .filter((t) => t.is_active).length;
  const totalVersions = Object.values(prompts).flat().length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-indigo-500" />
            Prompt Templates
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage and version AI prompt templates across all platform modules.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateFor("")}>
          <Plus className="h-4 w-4 mr-2" />
          New Template
        </Button>
      </div>

      {/* Stats */}
      {!isLoading && (
        <div className="flex items-center gap-6 text-sm text-gray-500">
          <span>
            <span className="font-semibold text-gray-900">{data?.total_task_types ?? 0}</span>{" "}
            task types
          </span>
          <span>
            <span className="font-semibold text-gray-900">{totalVersions}</span>{" "}
            total versions
          </span>
          <span>
            <span className="font-semibold text-green-700">{totalActive}</span>{" "}
            active
          </span>
        </div>
      )}

      {/* Search */}
      <input
        type="text"
        placeholder="Search task types…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />

      {/* Templates */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : taskTypes.length === 0 ? (
        <EmptyState
          title="No prompt templates"
          description="Create your first prompt template to override the system defaults."
          action={
            <Button size="sm" onClick={() => setCreateFor("")}>
              <Plus className="h-4 w-4 mr-2" />
              Create Template
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {taskTypes.map((taskType) => (
            <TaskTypeGroup
              key={taskType}
              taskType={taskType}
              templates={prompts[taskType] ?? []}
              onNewVersion={(t) => setCreateFor(t)}
            />
          ))}
        </div>
      )}

      {/* Create dialog */}
      {createFor !== null && (
        <CreateDialog
          defaultTaskType={createFor}
          onClose={() => setCreateFor(null)}
        />
      )}
    </div>
  );
}
