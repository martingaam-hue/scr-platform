"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  FileText,
  TrendingUp,
  Globe,
  Shield,
  Leaf,
  Settings,
  Target,
  Sparkles,
  Loader2,
  Upload,
  Download,
  RefreshCw,
  CheckCircle2,
  ClipboardCopy,
  Clock,
  X,
  Eye,
  Save,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  InfoBanner,
} from "@scr/ui";
import {
  BUSINESS_PLAN_ACTIONS,
  useGenerateBusinessPlan,
  useBusinessPlanResult,
  type BusinessPlanActionKey,
} from "@/lib/business-plan";
import { useProjects } from "@/lib/projects";
import { useBusinessPlans } from "@/lib/business-plans";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

// ── Mock data ──────────────────────────────────────────────────────────────

const MOCK_BUSINESS_PLANS = [
  { id: "mbp1", title: "Helios Solar Full Business Plan", version: 1, status: "finalized", page_count: 42, quality_score: 94, created_at: "2026-02-10T10:00:00Z" },
  { id: "mbp2", title: "Alpine Hydro Investment Memo", version: 2, status: "finalized", page_count: 38, quality_score: 91, created_at: "2026-01-22T09:00:00Z" },
  { id: "mbp3", title: "Baltic BESS Development Case", version: 1, status: "draft", page_count: 28, quality_score: 72, created_at: "2026-03-01T14:00:00Z" },
  { id: "mbp4", title: "Nordvik Wind Construction Update", version: 3, status: "finalized", page_count: 24, quality_score: 79, created_at: "2026-02-25T11:00:00Z" },
];

// ── Icon + colour config ───────────────────────────────────────────────────

const SECTION_ICONS: Record<
  BusinessPlanActionKey,
  { Icon: LucideIcon; color: string; bg: string }
> = {
  executive_summary: {
    Icon: FileText,
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  financial_overview: {
    Icon: TrendingUp,
    color: "text-green-600",
    bg: "bg-green-50",
  },
  market_analysis: {
    Icon: Globe,
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
  risk_narrative: {
    Icon: Shield,
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
  esg_statement: {
    Icon: Leaf,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  technical_summary: {
    Icon: Settings,
    color: "text-slate-600",
    bg: "bg-slate-50",
  },
  investor_pitch: {
    Icon: Target,
    color: "text-rose-600",
    bg: "bg-rose-50",
  },
};

// ── Helpers ────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string): string {
  const ms = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins > 1 ? "s" : ""} ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs > 1 ? "s" : ""} ago`;
  const days = Math.floor(hrs / 24);
  return `${days} day${days > 1 ? "s" : ""} ago`;
}

// ── Section Card ───────────────────────────────────────────────────────────

function SectionCard({
  actionKey,
  projectId,
  generateTrigger,
  isActive,
  onActivate,
}: {
  actionKey: BusinessPlanActionKey;
  projectId: string;
  generateTrigger: number;
  isActive: boolean;
  onActivate: (key: BusinessPlanActionKey, content: string) => void;
}) {
  const action = BUSINESS_PLAN_ACTIONS[actionKey];
  const { Icon, color, bg } = SECTION_ICONS[actionKey];
  const generate = useGenerateBusinessPlan(projectId);
  const [taskLogId, setTaskLogId] = useState<string | undefined>();
  const prevTrigger = useRef(0);

  const { data: result } = useBusinessPlanResult(projectId, taskLogId);

  const isLoading =
    generate.isPending ||
    result?.status === "pending" ||
    result?.status === "processing";
  const content = result?.status === "completed" ? result.content : null;

  // Use refs so callbacks are always fresh without re-triggering effects
  const generateRef = useRef<() => void>(() => undefined);
  generateRef.current = () => {
    if (isLoading) return;
    generate.mutate(actionKey, {
      onSuccess: (data) => setTaskLogId(data.task_log_id),
    });
  };

  const onActivateRef = useRef(onActivate);
  onActivateRef.current = onActivate;

  // Auto-trigger when generate-all fires
  useEffect(() => {
    if (generateTrigger > 0 && generateTrigger !== prevTrigger.current) {
      prevTrigger.current = generateTrigger;
      generateRef.current();
    }
  }, [generateTrigger]);

  // Notify parent when content becomes ready
  useEffect(() => {
    if (content) {
      onActivateRef.current(actionKey, content);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, actionKey]);

  return (
    <Card
      className={`cursor-pointer border transition-all hover:shadow-sm hover:border-neutral-300 ${
        isActive
          ? "border-primary-400 ring-1 ring-primary-100"
          : "border-neutral-200"
      }`}
      onClick={() => content && onActivateRef.current(actionKey, content)}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className={`p-2.5 rounded-lg ${bg} shrink-0`}>
            <Icon className={`h-5 w-5 ${color}`} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-neutral-900 leading-snug">
              {action.label}
            </h3>
            <p className="text-xs text-neutral-500 mt-0.5 leading-relaxed">
              {action.description}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-neutral-100">
          <div className="flex items-center gap-1.5">
            {isLoading && (
              <span className="flex items-center gap-1 text-xs text-amber-600">
                <Loader2 className="h-3 w-3 animate-spin" />
                Generating…
              </span>
            )}
            {content && !isLoading && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle2 className="h-3 w-3" />
                Ready — click to view
              </span>
            )}
          </div>

          <Button
            variant="outline"
            onClick={(e) => {
              e.stopPropagation();
              generateRef.current();
            }}
            disabled={isLoading || !projectId}
            className="h-7 text-xs px-2"
          >
            {isLoading ? (
              <Loader2 className="h-3 w-3 animate-spin mr-1" />
            ) : content ? (
              <RefreshCw className="h-3 w-3 mr-1" />
            ) : (
              <Sparkles className="h-3 w-3 mr-1" />
            )}
            {content ? "Regenerate" : "Generate"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Generated Content Panel ────────────────────────────────────────────────

function ContentPanel({
  content,
  label,
  onClose,
}: {
  content: string;
  label: string;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const qc = useQueryClient();

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSave = async () => {
    try {
      await api.post("/legal/documents", {
        template_id: null,
        title: label,
        content,
      });
      qc.invalidateQueries({ queryKey: ["legal-documents"] });
    } catch {
      // silent — user can retry
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${label.replace(/\s+/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="border-primary-200 bg-primary-50/20">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-neutral-800">{label}</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleCopy}
              className="h-7 text-xs px-2"
            >
              {copied ? (
                <CheckCircle2 className="h-3 w-3 text-green-500 mr-1" />
              ) : (
                <ClipboardCopy className="h-3 w-3 mr-1" />
              )}
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button
              variant="outline"
              onClick={handleSave}
              className="h-7 text-xs px-2"
            >
              <Save className="h-3 w-3 mr-1" />
              Save to Docs
            </Button>
            <Button
              variant="outline"
              onClick={handleDownload}
              className="h-7 text-xs px-2"
            >
              <Download className="h-3 w-3 mr-1" />
              Download
            </Button>
            <button
              onClick={onClose}
              className="p-1 text-neutral-400 hover:text-neutral-600 rounded-md hover:bg-neutral-100 ml-1"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="text-sm text-neutral-800 leading-relaxed whitespace-pre-wrap bg-white rounded-lg p-4 border border-neutral-200 max-h-96 overflow-y-auto">
          {content}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Drop Zone ──────────────────────────────────────────────────────────────

function DropZone() {
  const [dragging, setDragging] = useState(false);
  const [fileList, setFileList] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = Array.from(e.dataTransfer.files);
    setFileList((prev) => [...prev, ...files]);
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setFileList((prev) => [...prev, ...files]);
  };

  const removeFile = (index: number) => {
    setFileList((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragging
            ? "border-primary-400 bg-primary-50"
            : "border-neutral-200 bg-neutral-50 hover:border-neutral-300 hover:bg-white"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.txt,.csv"
          onChange={handleInput}
        />
        <Upload className="h-8 w-8 text-neutral-400 mx-auto mb-2" />
        <p className="text-sm font-medium text-neutral-700">
          Click to upload or drag and drop
        </p>
        <p className="text-xs text-neutral-500 mt-1">
          PDF, DOC, DOCX, XLS, XLSX, TXT, CSV supported
        </p>
      </div>

      {fileList.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {fileList.map((f, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 bg-neutral-100 rounded-md px-2.5 py-1 text-xs text-neutral-700"
            >
              <FileText className="h-3 w-3 text-neutral-500 shrink-0" />
              <span className="max-w-[160px] truncate">{f.name}</span>
              <button
                onClick={() => removeFile(i)}
                className="text-neutral-400 hover:text-neutral-600 shrink-0"
                aria-label="Remove file"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function BusinessPlanPage() {
  const searchParams = useSearchParams();
  const paramProjectId = searchParams.get("project_id") ?? "";

  const [selectedProjectId, setSelectedProjectId] = useState(paramProjectId);
  const { data: projects } = useProjects({ page_size: 50 });
  const { data: plans } = useBusinessPlans(selectedProjectId || undefined);

  const [generateAllTrigger, setGenerateAllTrigger] = useState(0);
  const [activeResult, setActiveResult] = useState<{
    key: BusinessPlanActionKey;
    content: string;
  } | null>(null);

  const selectedProject = projects?.items.find(
    (p) => p.id === selectedProjectId
  );
  const sectionKeys = Object.keys(
    BUSINESS_PLAN_ACTIONS
  ) as BusinessPlanActionKey[];

  const handleActivate = useCallback(
    (key: BusinessPlanActionKey, content: string) => {
      setActiveResult({ key, content });
    },
    []
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <FileText className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Business Planning
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              AI-powered business plan generation using Claude
            </p>
          </div>
        </div>

        <select
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white min-w-52 focus:outline-none focus:ring-2 focus:ring-primary-500"
          value={selectedProjectId}
          onChange={(e) => {
            setSelectedProjectId(e.target.value);
            setActiveResult(null);
          }}
        >
          <option value="">Select a project…</option>
          {projects?.items.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <InfoBanner>
        <strong>Business Planning</strong> uses AI to generate professional business plans from your uploaded documents. Create executive summaries, market analyses, financial projections, and operational plans with one click. Upload your pitch deck and project documents to transform them into comprehensive, investor-ready documentation.
      </InfoBanner>

      {!selectedProjectId ? (
        <EmptyState
          icon={<FileText className="h-12 w-12 text-neutral-400" />}
          title="Select a project"
          description="Choose a project from the dropdown to generate AI-powered business plan sections."
        />
      ) : (
        <>
          {/* Info banner */}
          <div className="flex items-start gap-2.5 p-3.5 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-700">
            <Sparkles className="h-4 w-4 shrink-0 mt-0.5" />
            <span>
              Generate individual sections or click{" "}
              <strong>Generate Professional Business Plan</strong> to produce a
              complete investor-ready document for{" "}
              <strong>{selectedProject?.name}</strong>.
            </span>
          </div>

          {/* Upload Project Documents */}
          <div>
            <h2 className="text-sm font-semibold text-neutral-900 mb-0.5">
              Upload Project Documents
            </h2>
            <p className="text-xs text-neutral-500 mb-3">
              Add supporting documents to provide additional context for AI
              generation
            </p>
            <DropZone />
          </div>

          {/* Generate All */}
          <Button
            variant="default"
            className="w-full h-12 text-base font-semibold"
            onClick={() => setGenerateAllTrigger((n) => n + 1)}
          >
            <Sparkles className="h-5 w-5 mr-2" />
            Generate Professional Business Plan
          </Button>

          {/* Quick Generate Reports */}
          <div>
            <div className="mb-4">
              <h2 className="text-sm font-semibold text-neutral-900">
                Quick Generate Reports
              </h2>
              <p className="text-xs text-neutral-500 mt-0.5">
                Generate individual sections with AI — click any card to view
                its output
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sectionKeys.map((key) => (
                <SectionCard
                  key={key}
                  actionKey={key}
                  projectId={selectedProjectId}
                  generateTrigger={generateAllTrigger}
                  isActive={activeResult?.key === key}
                  onActivate={handleActivate}
                />
              ))}
            </div>
          </div>

          {/* Generated content panel */}
          {activeResult && (
            <ContentPanel
              content={activeResult.content}
              label={BUSINESS_PLAN_ACTIONS[activeResult.key].label}
              onClose={() => setActiveResult(null)}
            />
          )}

          {/* Recent Business Plans */}
          {(() => {
            const displayPlans = plans && plans.length > 0 ? plans : MOCK_BUSINESS_PLANS;
            return displayPlans.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-neutral-900 mb-3">
                Recent Business Plans
              </h2>
              <div className="space-y-2">
                {displayPlans.map((plan) => (
                  <div
                    key={plan.id}
                    className="flex items-center justify-between p-3 bg-white border border-neutral-200 rounded-lg hover:border-neutral-300 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-1.5 bg-neutral-100 rounded-lg shrink-0">
                        <FileText className="h-4 w-4 text-neutral-500" />
                      </div>
                      <div>
                        <span className="text-sm font-medium text-neutral-800">
                          {plan.title}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-neutral-400 flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {timeAgo(plan.created_at)}
                          </span>
                          <span className="text-xs text-neutral-300">·</span>
                          <span className="text-xs text-neutral-400">
                            v{plan.version}
                          </span>
                          <span className="text-xs text-neutral-300">·</span>
                          <Badge
                            variant={
                              plan.status === "finalized" ? "success" : "info"
                            }
                          >
                            {plan.status}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        className="p-1.5 text-neutral-400 hover:text-neutral-600 rounded-md hover:bg-neutral-100"
                        aria-label="View"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        className="p-1.5 text-neutral-400 hover:text-neutral-600 rounded-md hover:bg-neutral-100"
                        aria-label="Download"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
