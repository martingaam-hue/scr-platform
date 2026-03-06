"use client";

import { useState, useRef, useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileText,
  Info,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  X,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  FileUploader,
  type FileItem,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@scr/ui";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AIFeedback } from "@/components/ai-feedback";
import { api } from "@/lib/api";
import {
  useTemplates,
  useTemplate,
  useLegalDocuments,
  useLegalDocument,
  useCreateLegalDocument,
  useUpdateDocumentAnswers,
  useGenerateDocument,
  useReviewDocument,
  useReviewResult,
  legalKeys,
  docStatusBadge,
  clauseRiskBadge,
  DOC_TYPE_LABELS,
  DOC_STATUS_LABELS,
  REVIEW_MODE_LABELS,
  SUPPORTED_JURISDICTIONS,
  type LegalDocumentResponse,
  type TemplateListItem,
  type QuestionnaireField,
  type ReviewResultResponse,
} from "@/lib/legal";
import { usePermission } from "@/lib/auth";

// ── Helpers ─────────────────────────────────────────────────────────────────

const DOC_TYPE_ICONS: Record<string, string> = {
  nda: "🔒",
  term_sheet: "📄",
  subscription_agreement: "📑",
  side_letter: "✉️",
  spv_incorporation: "🏢",
  amendment: "📝",
};

function GenerationStatusBadge({ status }: { status: string | null }) {
  if (!status || status === "not_started") return null;
  const config: Record<string, { label: string; class: string }> = {
    pending: { label: "Queued", class: "text-neutral-500" },
    generating: { label: "Generating…", class: "text-amber-600" },
    completed: { label: "Ready", class: "text-green-600" },
    failed: { label: "Failed", class: "text-red-600" },
  };
  const c = config[status] ?? config["pending"];
  return (
    <span className={`text-xs font-medium ${c.class}`}>{c.label}</span>
  );
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve((e.target?.result as string) ?? "");
    reader.onerror = reject;
    reader.readAsText(file);
  });
}

// ── Questionnaire Wizard ─────────────────────────────────────────────────────

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: QuestionnaireField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const base =
    "text-sm border border-neutral-200 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-primary-300";

  if (field.type === "boolean") {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded"
        />
        <span className="text-sm text-neutral-700">{field.label}</span>
      </label>
    );
  }

  if (field.type === "select") {
    return (
      <select
        className={base}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select…</option>
        {field.options?.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === "textarea") {
    return (
      <textarea
        className={`${base} h-20 resize-none`}
        value={String(value ?? "")}
        placeholder={field.placeholder ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  return (
    <input
      type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
      className={base}
      value={String(value ?? "")}
      placeholder={field.placeholder ?? ""}
      onChange={(e) =>
        onChange(field.type === "number" ? Number(e.target.value) : e.target.value)
      }
    />
  );
}

function DocumentWizard({
  templateId,
  onClose,
}: {
  templateId: string;
  onClose: () => void;
}) {
  const { data: template } = useTemplate(templateId);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [docId, setDocId] = useState<string | null>(null);
  const [step, setStep] = useState<"form" | "generating" | "done">("form");
  const createDoc = useCreateLegalDocument();
  const updateAnswers = useUpdateDocumentAnswers();
  const generateDoc = useGenerateDocument();
  const { data: doc } = useLegalDocument(docId);

  if (!template) {
    return (
      <div className="flex items-center justify-center h-40">
        <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  const handleGenerate = async () => {
    let id = docId;
    if (!id) {
      const created = await createDoc.mutateAsync({
        template_id: templateId,
        title: `${template.name} — ${new Date().toLocaleDateString()}`,
      });
      id = created.id;
      setDocId(id);
    }
    await updateAnswers.mutateAsync({ documentId: id, answers });
    await generateDoc.mutateAsync({ documentId: id });
    setStep("generating");
  };

  const setField = (fieldId: string, value: unknown) => {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
  };

  if (step === "generating" || step === "done") {
    const gs = doc?.generation_status;
    const isReady = gs === "completed";
    const isFailed = gs === "failed";

    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center gap-3">
          {isReady ? (
            <CheckCircle2 className="h-8 w-8 text-green-500" />
          ) : isFailed ? (
            <AlertTriangle className="h-8 w-8 text-red-500" />
          ) : (
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          )}
          <div>
            <p className="font-semibold text-neutral-900">
              {isReady
                ? "Document Ready"
                : isFailed
                  ? "Generation Failed"
                  : "Generating document…"}
            </p>
            <p className="text-sm text-neutral-500">
              {isReady
                ? "Your document has been generated and is ready to download."
                : isFailed
                  ? "An error occurred. Please try again."
                  : "AI is drafting your legal document. This may take a minute."}
            </p>
          </div>
        </div>
        {isReady && doc?.download_url && (
          <a
            href={doc.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-700"
          >
            <Download className="h-4 w-4" />
            Download Document
          </a>
        )}
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-h-[70vh] overflow-y-auto">
      <div>
        <h3 className="text-lg font-bold text-neutral-900">{template.name}</h3>
        <p className="text-sm text-neutral-500">{template.description}</p>
      </div>

      {template.questionnaire.sections.map((section) => (
        <div key={section.id}>
          <h4 className="text-sm font-semibold text-neutral-800 mb-3 pb-1 border-b">
            {section.title}
          </h4>
          <div className="space-y-4">
            {section.fields.map((field) => (
              <div key={field.id}>
                {field.type !== "boolean" && (
                  <label className="block text-xs font-medium text-neutral-700 mb-1">
                    {field.label}
                    {field.required && (
                      <span className="text-red-500 ml-1">*</span>
                    )}
                  </label>
                )}
                <FieldInput
                  field={field}
                  value={answers[field.id]}
                  onChange={(v) => setField(field.id, v)}
                />
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="flex gap-3 pt-2 border-t">
        <Button
          onClick={handleGenerate}
          disabled={createDoc.isPending || updateAnswers.isPending || generateDoc.isPending}
        >
          <Sparkles className="mr-2 h-4 w-4" />
          Generate Document
        </Button>
        <Button variant="outline" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

// ── AI Analysis Section ───────────────────────────────────────────────────────

function AnalysisSection({ onViewDocuments }: { onViewDocuments: () => void }) {
  const qc = useQueryClient();
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [fileItems, setFileItems] = useState<FileItem[]>([]);
  const [analysisPrompt, setAnalysisPrompt] = useState("");
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [savedDocId, setSavedDocId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const hasSaved = useRef(false);

  const reviewDoc = useReviewDocument();
  const { data: result } = useReviewResult(reviewId);

  const saveAnalysis = useMutation({
    mutationFn: (title: string) =>
      api
        .post<LegalDocumentResponse>("/legal/documents", {
          template_id: null,
          title,
        })
        .then((r) => r.data),
    onSuccess: (data) => {
      setSavedDocId(data.id);
      qc.invalidateQueries({ queryKey: legalKeys.documents() });
    },
    onError: () => {
      setSaveError("Could not save analysis to My Documents.");
    },
  });

  useEffect(() => {
    if (
      result?.status === "completed" &&
      !hasSaved.current &&
      uploadedFile
    ) {
      hasSaved.current = true;
      const title = `Legal Analysis — ${uploadedFile.name} — ${new Date().toLocaleDateString()}`;
      saveAnalysis.mutate(title);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result?.status]);

  const handleFilesSelected = (files: File[]) => {
    const file = files[0];
    setUploadedFile(file);
    setFileItems([{ file, progress: 100, status: "done" }]);
    setReviewId(null);
    setSavedDocId(null);
    setSaveError(null);
    hasSaved.current = false;
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setFileItems([]);
    setReviewId(null);
    setSavedDocId(null);
    setSaveError(null);
    hasSaved.current = false;
  };

  const handleAnalyze = async () => {
    if (!uploadedFile) return;
    hasSaved.current = false;
    setSavedDocId(null);
    setSaveError(null);

    const fileText = await readFileAsText(uploadedFile);

    const documentText = analysisPrompt.trim()
      ? `Analysis Request: ${analysisPrompt}\n\n---\n\nDocument Content:\n${fileText}`
      : fileText;

    const res = await reviewDoc.mutateAsync({
      document_text: documentText,
      mode: "comprehensive",
    });
    setReviewId(res.review_id);
  };

  const isPending =
    result?.status === "pending" || result?.status === "processing";
  const isAnalyzing = reviewDoc.isPending || isPending;

  return (
    <Card>
      <CardContent className="p-6 space-y-5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary-600" />
          <h2 className="text-base font-semibold text-neutral-900">
            AI Document Review & Analysis
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div>
            <label className="block text-xs font-medium text-neutral-700 mb-2">
              Upload Document
            </label>
            <FileUploader
              accept=".pdf,.doc,.docx,.txt"
              multiple={false}
              maxSizeMB={20}
              onFilesSelected={handleFilesSelected}
              files={fileItems}
              onRemove={handleRemoveFile}
              disabled={isAnalyzing}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="block text-xs font-medium text-neutral-700">
              Analysis Request
            </label>
            <textarea
              className="text-sm border border-neutral-200 rounded px-3 py-2 flex-1 resize-none min-h-[120px] focus:outline-none focus:ring-2 focus:ring-primary-300"
              placeholder={`Describe what you want the AI to focus on.\n\nE.g. "Identify unfavourable clauses for the investor", "Check for missing indemnity provisions", "Summarise key payment terms"…`}
              value={analysisPrompt}
              onChange={(e) => setAnalysisPrompt(e.target.value)}
              disabled={isAnalyzing}
            />
          </div>
        </div>

        <Button
          className="w-full"
          onClick={handleAnalyze}
          disabled={!uploadedFile || isAnalyzing}
        >
          {isAnalyzing ? (
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Search className="mr-2 h-4 w-4" />
          )}
          {isAnalyzing ? "Analysing document…" : "Analyze Document"}
        </Button>

        {savedDocId && (
          <div className="flex items-center gap-3 rounded-lg bg-green-50 border border-green-200 px-4 py-3">
            <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
            <p className="text-sm text-green-800">
              Analysis saved to{" "}
              <button
                className="font-semibold underline"
                onClick={onViewDocuments}
              >
                My Documents
              </button>
            </p>
          </div>
        )}

        {saveError && (
          <div className="flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3">
            <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700">{saveError}</p>
          </div>
        )}

        {result && result.status === "completed" && (
          <ReviewResultDisplay result={result} />
        )}
      </CardContent>
    </Card>
  );
}

// ── Templates Tab ─────────────────────────────────────────────────────────────

function TemplatesTab() {
  const { data: templates, isLoading } = useTemplates();
  const [activeTemplate, setActiveTemplate] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (activeTemplate) {
    return (
      <Card>
        <DocumentWizard
          templateId={activeTemplate}
          onClose={() => setActiveTemplate(null)}
        />
      </Card>
    );
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-2">
      {templates?.map((tmpl: TemplateListItem) => (
        <div key={tmpl.id} className="min-w-[200px] flex-1">
          <Card className="h-full hover:shadow-md transition-shadow">
            <CardContent className="p-5 flex flex-col h-full">
              <div className="flex items-start gap-3 mb-3">
                <span className="text-3xl">
                  {DOC_TYPE_ICONS[tmpl.doc_type] ?? "📄"}
                </span>
                <div>
                  <h3 className="font-semibold text-neutral-900 text-sm">
                    {tmpl.name}
                  </h3>
                  <p className="text-xs text-neutral-500">
                    ~{tmpl.estimated_pages} pages
                  </p>
                </div>
              </div>
              <p className="text-xs text-neutral-600 mb-4 flex-1">
                {tmpl.description}
              </p>
              <Button
                size="sm"
                onClick={() => setActiveTemplate(tmpl.id)}
                className="w-full"
              >
                <FileText className="mr-1.5 h-3.5 w-3.5" />
                Start
              </Button>
            </CardContent>
          </Card>
        </div>
      ))}
    </div>
  );
}

// ── My Documents Tab ──────────────────────────────────────────────────────────

function MyDocumentsTab() {
  const { data, isLoading } = useLegalDocuments();

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!data?.items.length) {
    return (
      <EmptyState
        icon={<FileText className="h-12 w-12 text-neutral-400" />}
        title="No documents yet"
        description="Generate your first legal document from the Templates tab, or analyse an uploaded document above."
      />
    );
  }

  return (
    <div className="space-y-3">
      {data.items.map((doc: LegalDocumentResponse) => (
        <Card key={doc.id}>
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-2xl flex-shrink-0">
                {DOC_TYPE_ICONS[doc.doc_type] ?? "📄"}
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-neutral-900 truncate">
                    {doc.title}
                  </p>
                  <Badge variant={docStatusBadge(doc.status)}>
                    {DOC_STATUS_LABELS[doc.status] ?? doc.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  <p className="text-xs text-neutral-500">
                    {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
                  </p>
                  <GenerationStatusBadge status={doc.generation_status} />
                  <p className="text-xs text-neutral-400">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              {doc.download_url && (
                <a
                  href={doc.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button size="sm" variant="outline">
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Review Tab ────────────────────────────────────────────────────────────────

function ReviewTab() {
  const [mode, setMode] = useState("risk_focused");
  const [jurisdiction, setJurisdiction] = useState("England & Wales");
  const [documentText, setDocumentText] = useState("");
  const [reviewId, setReviewId] = useState<string | null>(null);

  const reviewDoc = useReviewDocument();
  const { data: result } = useReviewResult(reviewId);

  const handleReview = async () => {
    const res = await reviewDoc.mutateAsync({
      document_text: documentText,
      mode,
      jurisdiction,
    });
    setReviewId(res.review_id);
  };

  const isPending =
    result?.status === "pending" || result?.status === "processing";

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="p-5 space-y-4">
          <h3 className="font-semibold text-neutral-900">
            AI Document Review
          </h3>
          <p className="text-sm text-neutral-500">
            Paste a legal document for AI-powered analysis, risk identification,
            and recommendations.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-neutral-700 mb-1">
                Review Mode
              </label>
              <select
                className="text-sm border border-neutral-200 rounded px-3 py-2 w-full"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                {Object.entries(REVIEW_MODE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-700 mb-1">
                Jurisdiction
              </label>
              <select
                className="text-sm border border-neutral-200 rounded px-3 py-2 w-full"
                value={jurisdiction}
                onChange={(e) => setJurisdiction(e.target.value)}
              >
                {SUPPORTED_JURISDICTIONS.map((j) => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-700 mb-1">
              Document Text
            </label>
            <textarea
              className="text-sm border border-neutral-200 rounded px-3 py-2 w-full h-40 resize-none font-mono"
              placeholder="Paste your legal document text here…"
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
            />
          </div>

          <Button
            onClick={handleReview}
            disabled={!documentText.trim() || reviewDoc.isPending || isPending}
          >
            {isPending || reviewDoc.isPending ? (
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Search className="mr-2 h-4 w-4" />
            )}
            {isPending || reviewDoc.isPending ? "Reviewing…" : "Review Document"}
          </Button>
        </CardContent>
      </Card>

      {result && result.status === "completed" && (
        <ReviewResultDisplay result={result} />
      )}
    </div>
  );
}

// ── Review Result Display ─────────────────────────────────────────────────────

function ReviewResultDisplay({ result }: { result: ReviewResultResponse }) {
  const riskColor =
    (result.overall_risk_score ?? 0) >= 70
      ? "text-red-600"
      : (result.overall_risk_score ?? 0) >= 40
        ? "text-amber-600"
        : "text-green-600";

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <p className="text-xs font-medium text-neutral-500 mb-1">
                Review Summary ({REVIEW_MODE_LABELS[result.mode] ?? result.mode} ·{" "}
                {result.jurisdiction})
              </p>
              <p className="text-sm text-neutral-700">{result.summary}</p>
            </div>
            {result.overall_risk_score !== null && (
              <div className="text-center flex-shrink-0">
                <p className={`text-3xl font-bold ${riskColor}`}>
                  {result.overall_risk_score}
                </p>
                <p className="text-xs text-neutral-400">Risk Score</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {result.clause_analyses.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-semibold text-neutral-700 mb-3">
              Clause Analysis ({result.clause_analyses.length})
            </p>
            <div className="space-y-3">
              {result.clause_analyses.map((c, i) => (
                <div
                  key={i}
                  className="border border-neutral-200 rounded-lg p-3"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={clauseRiskBadge(c.risk_level)}>
                      {c.risk_level}
                    </Badge>
                    <span className="text-xs font-medium text-neutral-700 capitalize">
                      {c.clause_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-500 italic mb-2 line-clamp-2">
                    &quot;{c.text_excerpt}&quot;
                  </p>
                  {c.issue && (
                    <p className="text-xs text-red-600">⚠ {c.issue}</p>
                  )}
                  {c.recommendation && (
                    <p className="text-xs text-green-700 mt-1">
                      ✓ {c.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {result.missing_clauses.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-neutral-700 mb-2">
                Missing Clauses
              </p>
              <ul className="space-y-1">
                {result.missing_clauses.map((c, i) => (
                  <li key={i} className="text-xs text-red-600 flex gap-1">
                    <X className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                    {c}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
        {result.recommendations.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-neutral-700 mb-2">
                Recommendations
              </p>
              <ul className="space-y-1">
                {result.recommendations.map((r, i) => (
                  <li key={i} className="text-xs text-green-700 flex gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                    {r}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      {result.jurisdiction_issues.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-semibold text-neutral-700 mb-2">
              <Shield className="inline h-4 w-4 mr-1 text-amber-500" />
              Jurisdiction Issues
            </p>
            <ul className="space-y-1">
              {result.jurisdiction_issues.map((issue, i) => (
                <li key={i} className="text-xs text-amber-700">
                  ⚠ {issue}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
      <AIFeedback
        taskType="legal_review"
        entityType="document"
        entityId={result.review_id}
        compact
      />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LegalPage() {
  const canCreate = usePermission("create", "report");
  const [activeTab, setActiveTab] = useState("templates");

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">
          Legal Automation & Compliance
        </h1>
        <p className="text-neutral-500 mt-1">
          AI-powered document generation and compliance management
        </p>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 rounded-lg bg-blue-50 border border-blue-200 px-4 py-3">
        <Info className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-blue-800">
          Upload contracts, term sheets, NDAs, or any legal document for instant AI-powered analysis.
          You can also generate new documents from our template library. All results are saved to
          your document library for future reference.
        </p>
      </div>

      {/* AI Analysis — above templates */}
      <AnalysisSection onViewDocuments={() => setActiveTab("documents")} />

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="documents">My Documents</TabsTrigger>
          <TabsTrigger value="review">AI Review</TabsTrigger>
        </TabsList>

        <TabsContent value="templates" className="mt-6">
          {canCreate ? (
            <TemplatesTab />
          ) : (
            <EmptyState
              icon={<FileText className="h-12 w-12 text-neutral-400" />}
              title="Insufficient permissions"
              description="You need document creation permissions to use legal templates."
            />
          )}
        </TabsContent>

        <TabsContent value="documents" className="mt-6">
          <MyDocumentsTab />
        </TabsContent>

        <TabsContent value="review" className="mt-6">
          <ReviewTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
