"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity,
  BarChart3,
  Bot,
  CheckCircle2,
  ChevronDown,
  Download,
  FileText,
  Globe,
  Leaf,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Scale,
  Shield,
  Sparkles,
  TrendingUp,
  Upload,
  Wrench,
  X,
} from "lucide-react";
import { Button, Card, CardContent } from "@scr/ui";
import { useQueryClient } from "@tanstack/react-query";
import { AIFeedback } from "@/components/ai-feedback";
import { api } from "@/lib/api";
import { legalKeys } from "@/lib/legal";
import {
  useCreateConversation,
  useConversation,
  useStreamMessage,
  type RalphMessage,
} from "@/lib/ralph";
import { InfoBanner } from "@/components/info-banner";

// ── Constants ─────────────────────────────────────────────────────────────────

const QUICK_ACTIONS = [
  {
    icon: FileText,
    label: "Investment Memo",
    color: "text-blue-600",
    bg: "bg-blue-50",
    prompt:
      "Generate a comprehensive investment memo including executive summary, investment thesis, financial analysis, risk assessment, team evaluation, and investment recommendation",
  },
  {
    icon: CheckCircle2,
    label: "Due Diligence",
    color: "text-violet-600",
    bg: "bg-violet-50",
    prompt:
      "Run a full due diligence analysis covering financial, legal, technical, and ESG dimensions with completeness scoring and gap identification",
  },
  {
    icon: Sparkles,
    label: "Signal Score",
    color: "text-amber-600",
    bg: "bg-amber-50",
    prompt:
      "Calculate and explain the Signal Score breakdown across all 6 dimensions with strengths, gaps, and a prioritised improvement roadmap",
  },
  {
    icon: Shield,
    label: "Risk Assessment",
    color: "text-red-600",
    bg: "bg-red-50",
    prompt:
      "Perform a structured risk assessment across technical, financial, regulatory, ESG, and market dimensions with mitigation strategies for each",
  },
  {
    icon: Scale,
    label: "Legal Review",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    prompt:
      "Review the attached legal document — identify key clauses, flag unusual or problematic terms, extract obligations, and assess overall completeness",
  },
  {
    icon: TrendingUp,
    label: "Portfolio Benchmark",
    color: "text-green-600",
    bg: "bg-green-50",
    prompt:
      "Compare my portfolio performance against peer benchmarks including quartile positioning, J-curve analysis, and vintage year comparison",
  },
  {
    icon: BarChart3,
    label: "LP Quarterly Report",
    color: "text-sky-600",
    bg: "bg-sky-50",
    prompt:
      "Generate an LP quarterly report with fund performance summary, portfolio company updates, benchmark positioning, covenant status, and ESG highlights",
  },
  {
    icon: Globe,
    label: "Market Analysis",
    color: "text-teal-600",
    bg: "bg-teal-50",
    prompt:
      "Analyze the current market landscape for this sector including comparable transactions, macro trends, competitive positioning, and investment implications",
  },
  {
    icon: Leaf,
    label: "ESG Impact Report",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    prompt:
      "Generate an ESG impact report covering carbon reduction metrics, EU taxonomy alignment, social impact KPIs, SDG mapping, and governance assessment",
  },
  {
    icon: Activity,
    label: "Covenant & KPI Check",
    color: "text-orange-600",
    bg: "bg-orange-50",
    prompt:
      "Review all active covenants and KPIs across the portfolio — flag any breaches or warning states and summarise compliance status with recommended actions",
  },
] as const;

const PROMPT_TEMPLATES = [
  {
    label: "Investment Memo",
    prompt:
      "Generate a comprehensive investment memo for [Company Name]. Include: executive summary, market opportunity, business model analysis, financial projections review, risk factors, team assessment, and investment recommendation with proposed terms.",
  },
  {
    label: "LP Quarterly Report",
    prompt:
      "Generate our LP quarterly report for Q[X] [Year]. Include: fund overview, NAV and performance summary, portfolio company updates, new investments and exits, benchmark comparison, covenant status, and ESG metrics.",
  },
  {
    label: "Due Diligence Checklist",
    prompt:
      "Run due diligence on [Company Name]. Assess: financial statements and projections, legal structure and cap table, technology and IP, market size and competitive dynamics, management team, ESG profile, and key risks with a completeness score.",
  },
  {
    label: "Risk Heat Map",
    prompt:
      "Produce a risk heat map across my portfolio. For each holding, score technical, financial, regulatory, ESG, and market risk on a 1-5 scale. Highlight the top 5 risk concentrations and suggest portfolio-level mitigations.",
  },
  {
    label: "ESG Impact Summary",
    prompt:
      "Summarise ESG performance across my portfolio for [Year]. Include: carbon metrics (Scope 1/2/3), renewable energy capacity, jobs created, SDG alignment, taxonomy compliance, and governance scores. Flag any red flags.",
  },
  {
    label: "Valuation Analysis",
    prompt:
      "Perform a valuation analysis for [Company/Project Name] using DCF, comparable transactions, and market multiples. Provide a valuation range with key sensitivities and assumptions clearly stated.",
  },
  {
    label: "Legal Document Summary",
    prompt:
      "Summarise the attached legal document. Extract: key parties and obligations, payment terms, termination clauses, indemnities and liabilities, governing law, and any unusual or high-risk provisions.",
  },
  {
    label: "Covenant Compliance Report",
    prompt:
      "Review covenant compliance across all active portfolio companies. List each covenant, current status (pass/warn/breach), headroom, and recommended actions. Flag any immediate concerns requiring investor attention.",
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve((e.target?.result as string) ?? "");
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ToolCallIndicator({ name }: { name: string }) {
  const label = name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <div className="flex items-center gap-2 text-xs text-neutral-400 py-2">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100">
        <Wrench className="h-3.5 w-3.5 text-amber-600" />
      </div>
      <Loader2 className="h-3 w-3 animate-spin" />
      <span>{label}…</span>
    </div>
  );
}

function AssistantContent({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming?: boolean;
}) {
  return (
    <div className="text-sm leading-relaxed text-neutral-800">
      {content ? (
        <div className="prose prose-sm prose-neutral max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : isStreaming ? (
        <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
      ) : null}
      {isStreaming && content && (
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400" />
      )}
    </div>
  );
}

interface MessageRowProps {
  message: RalphMessage | { id: string; role: "assistant"; content: string; created_at: string };
  isStreaming?: boolean;
  isSaved: boolean;
  isSaving: boolean;
  onSave: () => void;
  onDownload: () => void;
}

function MessageRow({
  message,
  isStreaming,
  isSaved,
  isSaving,
  onSave,
  onDownload,
}: MessageRowProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex gap-3 py-3">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-neutral-200 text-xs font-semibold text-neutral-600 mt-0.5">
          You
        </div>
        <p className="flex-1 text-sm text-neutral-700 pt-1">{message.content}</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-neutral-100 bg-white p-5 space-y-4">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-100">
          <Bot className="h-4 w-4 text-primary-600" />
        </div>
        <span className="text-xs font-semibold text-primary-700">Ralph</span>
        {isStreaming && (
          <span className="text-[10px] text-neutral-400 flex items-center gap-1">
            <RefreshCw className="h-2.5 w-2.5 animate-spin" />
            Generating…
          </span>
        )}
      </div>

      <AssistantContent content={message.content} isStreaming={isStreaming} />

      {!isStreaming && message.content && (
        <div className="flex items-center gap-2 pt-2 border-t border-neutral-100">
          <Button
            size="sm"
            variant="outline"
            onClick={onSave}
            disabled={isSaved || isSaving}
          >
            {isSaved ? (
              <CheckCircle2 className="mr-1.5 h-3.5 w-3.5 text-green-600" />
            ) : isSaving ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="mr-1.5 h-3.5 w-3.5" />
            )}
            {isSaved ? "Saved" : "Save to My Documents"}
          </Button>
          <Button size="sm" variant="outline" onClick={onDownload}>
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Download
          </Button>
          <AIFeedback
            taskType="ralph_chat"
            entityType="message"
            entityId={message.id}
            compact
          />
        </div>
      )}
    </div>
  );
}

function QuickActionCard({
  action,
  onSelect,
}: {
  action: (typeof QUICK_ACTIONS)[number];
  onSelect: (prompt: string) => void;
}) {
  const Icon = action.icon;
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 flex flex-col gap-3 hover:border-neutral-300 hover:shadow-sm transition-all">
      <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${action.bg}`}>
        <Icon className={`h-4 w-4 ${action.color}`} />
      </div>
      <p className="text-xs font-semibold text-neutral-800 leading-tight flex-1">
        {action.label}
      </p>
      <Button
        size="sm"
        variant="outline"
        className="w-full text-xs"
        onClick={() => onSelect(action.prompt)}
      >
        Use
      </Button>
    </div>
  );
}

function TemplateMenu({
  onSelect,
  onClose,
}: {
  onSelect: (prompt: string) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute bottom-full mb-2 right-0 z-50 w-72 rounded-xl border border-neutral-200 bg-white shadow-lg overflow-hidden"
    >
      <p className="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-widest text-neutral-400 border-b border-neutral-100">
        Prompt Templates
      </p>
      <div className="max-h-64 overflow-y-auto py-1">
        {PROMPT_TEMPLATES.map((t) => (
          <button
            key={t.label}
            onClick={() => {
              onSelect(t.prompt);
              onClose();
            }}
            className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-neutral-50 transition-colors"
          >
            <FileText className="h-3.5 w-3.5 text-neutral-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-neutral-800">{t.label}</p>
              <p className="text-xs text-neutral-400 line-clamp-1 mt-0.5">
                {t.prompt.slice(0, 60)}…
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RalphPage() {
  const qc = useQueryClient();

  // Prompt & file state
  const [prompt, setPrompt] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);

  // Saved docs per message
  const [savedDocs, setSavedDocs] = useState<Record<string, boolean>>({});
  const [savingDocs, setSavingDocs] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Hooks
  const createConversation = useCreateConversation();
  const { data: conversation, refetch } = useConversation(conversationId);

  const handleToken = useCallback((token: string) => {
    setStreamingContent((prev) => (prev ?? "") + token);
  }, []);

  const handleDone = useCallback(
    (_msgId: string) => {
      setStreamingContent(null);
      refetch();
    },
    [refetch],
  );

  const { sendMessage, isStreaming, activeToolCalls } = useStreamMessage(
    conversationId,
    handleToken,
    handleDone,
  );

  // Send pending prompt after conversation is created
  useEffect(() => {
    if (pendingPrompt && conversationId && !isStreaming) {
      sendMessage(pendingPrompt);
      setPendingPrompt(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingPrompt, conversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages, streamingContent, activeToolCalls]);

  const handleGenerate = async () => {
    const trimmed = prompt.trim();
    if (!trimmed || isStreaming) return;

    // Build full prompt with file contents
    let fullPrompt = trimmed;
    if (attachedFiles.length > 0) {
      const fileTexts = await Promise.all(
        attachedFiles.map(async (f) => {
          const text = await readFileAsText(f);
          return `\n\n---\n[Attached: ${f.name}]\n${text}`;
        }),
      );
      fullPrompt += fileTexts.join("");
    }

    setPrompt("");

    if (conversationId) {
      setStreamingContent("");
      sendMessage(fullPrompt);
    } else {
      setPendingPrompt(fullPrompt);
      setStreamingContent("");
      const conv = await createConversation.mutateAsync({
        title: trimmed.slice(0, 60),
      });
      setConversationId(conv.id);
    }
  };

  const handleFilesSelected = (files: File[]) => {
    setAttachedFiles((prev) => [...prev, ...files]);
  };

  const handleRemoveFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleQuickAction = (actionPrompt: string) => {
    setPrompt(actionPrompt);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleNewConversation = () => {
    setConversationId(null);
    setStreamingContent(null);
    setPendingPrompt(null);
    setPrompt("");
    setSavedDocs({});
    setSavingDocs({});
  };

  const handleSave = async (messageId: string, content: string) => {
    setSavingDocs((prev) => ({ ...prev, [messageId]: true }));
    try {
      await api.post("/legal/documents", {
        template_id: null,
        title: `Ralph — ${new Date().toLocaleDateString()}`,
        content,
      });
      setSavedDocs((prev) => ({ ...prev, [messageId]: true }));
      qc.invalidateQueries({ queryKey: legalKeys.documents() });
    } finally {
      setSavingDocs((prev) => ({ ...prev, [messageId]: false }));
    }
  };

  const handleDownload = (content: string) => {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ralph-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Build display messages
  const displayMessages: Array<
    RalphMessage | { id: string; role: "assistant"; content: string; created_at: string }
  > = [
    ...(conversation?.messages ?? []).filter(
      (m) => m.role === "user" || m.role === "assistant",
    ),
    ...(streamingContent !== null
      ? [
          {
            id: "streaming",
            role: "assistant" as const,
            content: streamingContent,
            created_at: new Date().toISOString(),
          },
        ]
      : []),
  ];

  const hasMessages = displayMessages.length > 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-100">
              <Bot className="h-5 w-5 text-primary-600" />
            </div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Ralph — AI Command Center
            </h1>
          </div>
          <p className="text-neutral-500 mt-1.5 ml-0.5">
            Full investment analysis, document generation, and portfolio intelligence — powered by your data
          </p>
        </div>
        {hasMessages && (
          <Button variant="outline" size="sm" onClick={handleNewConversation}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New Chat
          </Button>
        )}
      </div>

      <InfoBanner>
        <strong>Ralph AI</strong> is your AI investment analyst powered by Claude. Ask questions about
        your portfolio, request analysis of specific holdings, get deal screening summaries, or generate
        reports — all using natural language. Ralph has full context of your fund and portfolio.
      </InfoBanner>

      {/* Main prompt section */}
      <Card>
        <CardContent className="p-5 space-y-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary-100">
              <Bot className="h-4 w-4 text-primary-600" />
            </div>
            <span className="text-sm font-semibold text-neutral-900">Ralph</span>
            {hasMessages && (
              <span className="text-xs text-neutral-400">
                · continuing conversation
              </span>
            )}
          </div>

          <textarea
            className="w-full text-sm border border-neutral-200 rounded-lg px-4 py-3 min-h-[120px] resize-none focus:outline-none focus:ring-2 focus:ring-primary-300 placeholder-neutral-400"
            placeholder={`e.g. "Generate an investment memo for SolarTech Ventures"\n"Compare risk profiles across my top 5 portfolio holdings"\n"Review this NDA and flag problematic clauses"\n"What's our portfolio IRR vs benchmark?"\n"Summarize all covenant breaches this quarter"`}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.metaKey) handleGenerate();
            }}
            disabled={isStreaming}
          />

          {/* Attached file chips */}
          {attachedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {attachedFiles.map((f, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700"
                >
                  <FileText className="h-3 w-3 text-neutral-500" />
                  {f.name}
                  <button
                    onClick={() => handleRemoveFile(i)}
                    className="text-neutral-400 hover:text-neutral-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Action row */}
          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={handleGenerate}
              disabled={!prompt.trim() || isStreaming}
            >
              {isStreaming ? (
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-2 h-4 w-4" />
              )}
              {isStreaming ? "Generating…" : "Generate"}
            </Button>

            {/* Upload */}
            <div className="relative">
              <input
                type="file"
                id="ralph-upload"
                multiple
                accept=".pdf,.doc,.docx,.xlsx,.pptx,.txt"
                className="hidden"
                onChange={(e) =>
                  handleFilesSelected(Array.from(e.target.files ?? []))
                }
              />
              <Button
                variant="outline"
                onClick={() => document.getElementById("ralph-upload")?.click()}
              >
                <Upload className="mr-1.5 h-4 w-4" />
                Upload
              </Button>
            </div>

            {/* Use Template */}
            <div className="relative">
              <Button
                variant="outline"
                onClick={() => setShowTemplateMenu((v) => !v)}
              >
                <FileText className="mr-1.5 h-4 w-4" />
                Use Template
                <ChevronDown className="ml-1.5 h-3.5 w-3.5" />
              </Button>
              {showTemplateMenu && (
                <TemplateMenu
                  onSelect={setPrompt}
                  onClose={() => setShowTemplateMenu(false)}
                />
              )}
            </div>
          </div>
          <p className="text-[11px] text-neutral-400">
            ⌘ + Enter to generate · Attach documents to provide context for analysis
          </p>
        </CardContent>
      </Card>

      {/* Quick action cards */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400 mb-3">
          Quick Actions
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
          {QUICK_ACTIONS.map((action) => (
            <QuickActionCard
              key={action.label}
              action={action}
              onSelect={handleQuickAction}
            />
          ))}
        </div>
      </div>

      {/* Response area */}
      {hasMessages && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-neutral-200" />
            <p className="text-xs font-semibold uppercase tracking-widest text-neutral-400">
              Conversation
            </p>
            <div className="h-px flex-1 bg-neutral-200" />
          </div>

          <div className="space-y-3">
            {displayMessages.map((message) => {
              const isStreamingMsg = message.id === "streaming";
              return (
                <MessageRow
                  key={message.id}
                  message={message}
                  isStreaming={isStreamingMsg}
                  isSaved={savedDocs[message.id] ?? false}
                  isSaving={savingDocs[message.id] ?? false}
                  onSave={() =>
                    handleSave(message.id, message.content)
                  }
                  onDownload={() => handleDownload(message.content)}
                />
              );
            })}

            {/* Tool call indicators */}
            {activeToolCalls.map((toolName) => (
              <ToolCallIndicator key={toolName} name={toolName} />
            ))}

            <div ref={messagesEndRef} />
          </div>

          <div className="flex justify-center pt-2">
            <Button variant="outline" size="sm" onClick={handleNewConversation}>
              <Plus className="mr-1.5 h-3.5 w-3.5" />
              Start New Conversation
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
