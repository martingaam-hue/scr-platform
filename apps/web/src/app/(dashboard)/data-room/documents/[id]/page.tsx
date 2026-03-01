"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckSquare,
  Clock,
  Eye,
  FileText,
  GitBranch,
  HardDrive,
  Loader2,
  Scissors,
  Shield,
  Square,
  Upload,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import {
  useDocument,
  useDocumentVersions,
  useAccessLog,
  useDocumentDownload,
  type DocumentVersionResponse,
  type AccessLogEntry,
} from "@/lib/dataroom";
import {
  useRedactionJob,
  useRedactionJobs,
  useAnalyzeDocument,
  useApproveRedactions,
  useApplyRedaction,
  type DetectedEntity,
  type RedactionJob,
} from "@/lib/redaction";
import { PdfViewer } from "@/components/pdf-viewer/pdf-viewer";

// ── Helpers ────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function VersionRow({ version }: { version: DocumentVersionResponse }) {
  const isLatest = version.version === 1;
  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0 hover:bg-neutral-50 px-4 -mx-4">
      <div className="h-9 w-9 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
        <GitBranch className="h-4 w-4 text-primary-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-neutral-900 truncate">
            Version {version.version}
          </p>
          {isLatest && (
            <Badge variant="success" className="text-[10px]">
              Latest
            </Badge>
          )}
        </div>
        <p
          className="text-xs text-neutral-500 truncate"
          title={version.name}
        >
          {version.name}
        </p>
      </div>
      <div className="flex items-center gap-6 text-xs text-neutral-500 flex-shrink-0">
        <span className="flex items-center gap-1">
          <HardDrive className="h-3 w-3" />
          {formatBytes(version.file_size_bytes)}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(version.created_at).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          })}
        </span>
        <span
          className="flex items-center gap-1 font-mono text-[10px]"
          title={version.checksum_sha256}
        >
          <Shield className="h-3 w-3" />
          {version.checksum_sha256.slice(0, 8)}...
        </span>
      </div>
    </div>
  );
}

function AccessLogRow({ entry }: { entry: AccessLogEntry }) {
  return (
    <div className="flex items-center gap-4 py-3 border-b last:border-0 hover:bg-neutral-50 px-4 -mx-4">
      <div className="h-9 w-9 rounded-lg bg-neutral-100 flex items-center justify-center flex-shrink-0">
        <Eye className="h-4 w-4 text-neutral-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p
          className="text-sm font-medium text-neutral-900 font-mono truncate"
          title={entry.user_id}
        >
          {entry.user_id.slice(0, 8)}...
        </p>
        <p className="text-xs text-neutral-500 capitalize">{entry.action}</p>
      </div>
      <div className="flex items-center gap-6 text-xs text-neutral-500 flex-shrink-0">
        {entry.ip_address && (
          <span className="font-mono text-[10px]">{entry.ip_address}</span>
        )}
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(entry.timestamp).toLocaleString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}

// ── PDF viewer tab ─────────────────────────────────────────────────────────

function PdfViewerTab({
  documentId,
  documentName,
  fileType,
}: {
  documentId: string;
  documentName: string;
  fileType: string;
}) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const getDownloadUrl = useDocumentDownload();

  const isPdf = fileType?.toLowerCase() === "pdf";

  if (!isPdf) {
    return (
      <Card>
        <CardContent className="p-8 flex flex-col items-center justify-center gap-3">
          <FileText className="h-12 w-12 text-neutral-300" />
          <p className="text-sm text-neutral-500">
            PDF preview is only available for PDF documents. This document is a{" "}
            <span className="uppercase font-medium">{fileType}</span> file.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!pdfUrl) {
    return (
      <Card>
        <CardContent className="p-8 flex flex-col items-center justify-center gap-4">
          <FileText className="h-12 w-12 text-primary-400" />
          <p className="text-sm text-neutral-600">
            Click below to load the PDF viewer with annotation support.
          </p>
          <Button
            variant="default"
            disabled={loading}
            onClick={async () => {
              setLoading(true);
              try {
                const result = await getDownloadUrl.mutateAsync(documentId);
                setPdfUrl(result.download_url);
              } finally {
                setLoading(false);
              }
            }}
          >
            {loading ? "Loading..." : "Open PDF Viewer"}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div style={{ height: "75vh" }}>
      <PdfViewer
        documentId={documentId}
        documentUrl={pdfUrl}
        documentName={documentName}
      />
    </div>
  );
}

// ── Redaction tab ──────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  analyzing: "Analyzing...",
  review: "Ready for Review",
  applying: "Applying Redactions...",
  done: "Complete",
  failed: "Failed",
};

const STATUS_VARIANTS: Record<
  string,
  "neutral" | "info" | "warning" | "success" | "error"
> = {
  pending: "neutral",
  analyzing: "info",
  review: "warning",
  applying: "info",
  done: "success",
  failed: "error",
};

function entityTypeLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function EntityRow({
  entity,
  selected,
  onToggle,
}: {
  entity: DetectedEntity;
  selected: boolean;
  onToggle: (id: number) => void;
}) {
  return (
    <div
      className={`flex items-center gap-3 py-2.5 px-3 rounded-lg cursor-pointer transition-colors ${
        selected ? "bg-primary-50 border border-primary-200" : "hover:bg-neutral-50 border border-transparent"
      }`}
      onClick={() => onToggle(entity.id)}
    >
      <div className="flex-shrink-0 text-neutral-400">
        {selected ? (
          <CheckSquare className="h-4 w-4 text-primary-600" />
        ) : (
          <Square className="h-4 w-4" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={entity.is_high_sensitivity ? "error" : "neutral"} className="text-[10px]">
            {entityTypeLabel(entity.entity_type)}
          </Badge>
          {entity.is_high_sensitivity && (
            <span title="High sensitivity PII">
              <AlertTriangle className="h-3.5 w-3.5 text-error-500" />
            </span>
          )}
          <span className="text-xs text-neutral-500">p.{entity.page}</span>
          <span className="text-xs text-neutral-400">
            {Math.round(entity.confidence * 100)}% confidence
          </span>
        </div>
        <p className="text-sm text-neutral-800 mt-0.5 font-medium truncate" title={entity.text}>
          &ldquo;{entity.text}&rdquo;
        </p>
      </div>
    </div>
  );
}

function EntityGroup({
  type,
  entities,
  selectedIds,
  onToggle,
}: {
  type: string;
  entities: DetectedEntity[];
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
}) {
  return (
    <div className="mb-4">
      <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
        {entityTypeLabel(type)} ({entities.length})
      </p>
      <div className="space-y-1">
        {entities.map((e) => (
          <EntityRow
            key={e.id}
            entity={e}
            selected={selectedIds.has(e.id)}
            onToggle={onToggle}
          />
        ))}
      </div>
    </div>
  );
}

function ActiveJobPanel({
  job,
  onSelectAll,
  selectedIds,
  onToggle,
  onApprove,
  onApply,
  approving,
  applying,
}: {
  job: RedactionJob;
  onSelectAll: (highSensitivityOnly: boolean) => void;
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
  onApprove: () => void;
  onApply: () => void;
  approving: boolean;
  applying: boolean;
}) {
  const isRunning =
    job.status === "pending" ||
    job.status === "analyzing" ||
    job.status === "applying";

  // Group entities by type
  const entities: DetectedEntity[] = job.detected_entities ?? [];
  const groups = entities.reduce<Record<string, DetectedEntity[]>>((acc, e) => {
    if (!acc[e.entity_type]) acc[e.entity_type] = [];
    acc[e.entity_type].push(e);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {/* Status banner */}
      <div className="flex items-center gap-3 p-4 rounded-lg bg-neutral-50 border border-neutral-200">
        {isRunning ? (
          <Loader2 className="h-5 w-5 text-primary-600 animate-spin flex-shrink-0" />
        ) : (
          <Scissors className="h-5 w-5 text-primary-600 flex-shrink-0" />
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-neutral-800">
              {STATUS_LABELS[job.status] ?? job.status}
            </span>
            <Badge variant={STATUS_VARIANTS[job.status] ?? "neutral"}>
              {job.status}
            </Badge>
          </div>
          {job.status === "review" && (
            <p className="text-xs text-neutral-500 mt-0.5">
              {job.entity_count} entities detected — select those you want to
              redact, then click Approve.
            </p>
          )}
          {job.status === "done" && (
            <p className="text-xs text-neutral-500 mt-0.5">
              {job.approved_count} entities redacted successfully.
            </p>
          )}
          {job.error_message && (
            <p className="text-xs text-error-600 mt-0.5">{job.error_message}</p>
          )}
        </div>
      </div>

      {/* Review UI */}
      {job.status === "review" && entities.length > 0 && (
        <>
          {/* Quick select buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelectAll(false)}
            >
              Select All ({entities.length})
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelectAll(true)}
            >
              <AlertTriangle className="h-3.5 w-3.5 mr-1.5 text-error-500" />
              Select All High-Sensitivity
            </Button>
            <span className="text-xs text-neutral-400 ml-auto">
              {selectedIds.size} selected
            </span>
          </div>

          {/* Entity list grouped by type */}
          <Card>
            <CardContent className="p-4 max-h-[480px] overflow-y-auto">
              {Object.entries(groups).map(([type, items]) => (
                <EntityGroup
                  key={type}
                  type={type}
                  entities={items}
                  selectedIds={selectedIds}
                  onToggle={onToggle}
                />
              ))}
            </CardContent>
          </Card>

          {/* Approve button */}
          <div className="flex justify-end">
            <Button
              disabled={selectedIds.size === 0 || approving}
              onClick={onApprove}
            >
              {approving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Approve Selected & Redact ({selectedIds.size})
            </Button>
          </div>
        </>
      )}

      {/* No entities found */}
      {job.status === "review" && entities.length === 0 && (
        <EmptyState
          icon={<Shield className="h-10 w-10 text-neutral-400" />}
          title="No PII entities detected"
          description="The AI found no personally identifiable information in this document."
        />
      )}

      {/* Applying: show apply button */}
      {job.status === "applying" && !isRunning && (
        <div className="flex justify-end">
          <Button disabled={applying} onClick={onApply}>
            {applying && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Generate Redacted PDF
          </Button>
        </div>
      )}

      {/* Done: download link */}
      {job.status === "done" && job.redacted_s3_key && (
        <Card>
          <CardContent className="p-5 flex items-center gap-3">
            <Shield className="h-5 w-5 text-success-600 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-neutral-800">
                Redacted document ready
              </p>
              <p className="text-xs text-neutral-500 font-mono mt-0.5 truncate">
                {job.redacted_s3_key}
              </p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <a href="#" title="Download Redacted PDF">
                Download Redacted PDF
              </a>
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RedactionTab({ documentId }: { documentId: string }) {
  const { data: jobs, isLoading: jobsLoading } = useRedactionJobs(documentId);
  const analyzeDoc = useAnalyzeDocument();
  const approveMutation = useApproveRedactions();
  const applyMutation = useApplyRedaction();

  // Track which job the user is currently working with
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Poll if we have an active job
  const { data: polledJob } = useRedactionJob(activeJobId ?? "", !!activeJobId);

  // Resolve the job to display: prefer the polled job for the active one
  const latestJob: RedactionJob | null =
    polledJob ?? (jobs && jobs.length > 0 ? jobs[0] : null);

  // Selection state for entity approval
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  function toggleEntity(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll(highSensitivityOnly: boolean) {
    const entities: DetectedEntity[] = latestJob?.detected_entities ?? [];
    const ids = entities
      .filter((e) => !highSensitivityOnly || e.is_high_sensitivity)
      .map((e) => e.id);
    setSelectedIds(new Set(ids));
  }

  async function handleAnalyze() {
    const result = await analyzeDoc.mutateAsync({ document_id: documentId });
    setActiveJobId(result.job_id);
    setSelectedIds(new Set());
  }

  async function handleApprove() {
    if (!latestJob) return;
    await approveMutation.mutateAsync({
      job_id: latestJob.id,
      approved_entity_ids: Array.from(selectedIds),
    });
  }

  async function handleApply() {
    if (!latestJob) return;
    await applyMutation.mutateAsync({ job_id: latestJob.id });
  }

  // Sync activeJobId when jobs load for the first time
  if (!activeJobId && jobs && jobs.length > 0 && !jobsLoading) {
    setActiveJobId(jobs[0].id);
  }

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-neutral-900">
            AI Document Redaction
          </h2>
          <p className="text-xs text-neutral-500 mt-0.5">
            Detect and redact PII from this document using AI.
          </p>
        </div>
        <Button
          onClick={handleAnalyze}
          disabled={analyzeDoc.isPending}
          variant="default"
        >
          {analyzeDoc.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Scissors className="h-4 w-4 mr-2" />
          )}
          {latestJob ? "Re-analyze for PII" : "Analyze for PII"}
        </Button>
      </div>

      {/* Loading */}
      {jobsLoading && (
        <div className="flex h-24 items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
        </div>
      )}

      {/* No jobs yet */}
      {!jobsLoading && !latestJob && (
        <EmptyState
          icon={<Scissors className="h-10 w-10 text-neutral-400" />}
          title="No redaction jobs"
          description="Click 'Analyze for PII' to start a new AI-powered PII detection scan."
        />
      )}

      {/* Active job panel */}
      {latestJob && (
        <ActiveJobPanel
          job={latestJob}
          selectedIds={selectedIds}
          onSelectAll={selectAll}
          onToggle={toggleEntity}
          onApprove={handleApprove}
          onApply={handleApply}
          approving={approveMutation.isPending}
          applying={applyMutation.isPending}
        />
      )}

      {/* Past jobs */}
      {jobs && jobs.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Previous Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {jobs.slice(1).map((job) => (
                <div
                  key={job.id}
                  className="flex items-center gap-3 py-2 border-b last:border-0"
                >
                  <Badge variant={STATUS_VARIANTS[job.status] ?? "neutral"}>
                    {job.status}
                  </Badge>
                  <span className="text-xs text-neutral-500">
                    {job.entity_count} entities detected,{" "}
                    {job.approved_count} redacted
                  </span>
                  <span className="text-xs text-neutral-400 ml-auto">
                    {new Date(job.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setActiveJobId(job.id);
                      setSelectedIds(new Set());
                    }}
                  >
                    View
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

type Tab = "versions" | "access-log" | "viewer" | "redaction";

export default function DocumentVersionsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("versions");

  const { data: doc, isLoading: docLoading } = useDocument(id);
  const { data: versions, isLoading: versionsLoading } =
    useDocumentVersions(id);
  const { data: accessLog, isLoading: logLoading } = useAccessLog(id);

  const isLoading = docLoading || versionsLoading;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: "versions", label: "Version History" },
    { id: "access-log", label: "Access Log" },
    { id: "viewer", label: "PDF Viewer" },
    { id: "redaction", label: "Redaction" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Data Room
        </button>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <FileText className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">
                {doc?.name ?? "Document"}
              </h1>
              <p className="text-sm text-neutral-500 mt-0.5">
                Version history &mdash; {versions?.length ?? 0} version
                {versions?.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Upload New Version
          </Button>
        </div>
      </div>

      {/* Current version summary */}
      {doc && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">Current Version</p>
              <p className="text-2xl font-bold text-neutral-800">
                v{doc.version}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">File Size</p>
              <p className="text-2xl font-bold text-neutral-800">
                {formatBytes(doc.file_size_bytes)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">File Type</p>
              <p className="text-2xl font-bold text-neutral-800 uppercase">
                {doc.file_type}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-5">
              <p className="text-xs text-neutral-500">Status</p>
              <div className="mt-1">
                <Badge
                  variant={
                    doc.status === "ready"
                      ? "success"
                      : doc.status === "error"
                      ? "error"
                      : "neutral"
                  }
                >
                  {doc.status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-neutral-200 flex gap-6">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === t.id
                ? "border-b-2 border-primary-600 text-primary-600"
                : "text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Version list */}
      {activeTab === "versions" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Version History</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {!versions || versions.length === 0 ? (
              <EmptyState
                icon={<GitBranch className="h-10 w-10 text-neutral-400" />}
                title="No versions"
                description="Upload a new version to create a version history."
              />
            ) : (
              <div>
                {versions.map((v) => (
                  <VersionRow key={v.id} version={v} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Access log */}
      {activeTab === "access-log" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Access Log</CardTitle>
          </CardHeader>
          <CardContent>
            {logLoading ? (
              <div className="flex h-24 items-center justify-center">
                <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
              </div>
            ) : !accessLog?.items || accessLog.items.length === 0 ? (
              <EmptyState
                icon={<Eye className="h-10 w-10 text-neutral-400" />}
                title="No access events"
                description="Access events will appear here when this document is viewed."
              />
            ) : (
              <div>
                {accessLog.items.map((entry) => (
                  <AccessLogRow key={entry.id} entry={entry} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* PDF Viewer */}
      {activeTab === "viewer" && doc && (
        <PdfViewerTab
          documentId={id}
          documentName={doc.name}
          fileType={doc.file_type}
        />
      )}

      {/* Redaction */}
      {activeTab === "redaction" && <RedactionTab documentId={id} />}

      {/* Checksum verification note */}
      {activeTab === "versions" && versions && versions.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-primary-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-neutral-800">
                  Integrity Verification
                </p>
                <p className="text-xs text-neutral-500 mt-1">
                  Each version is stored with a SHA-256 checksum for tamper
                  detection. The checksum is verified on every download.
                </p>
                <p className="text-xs font-mono text-neutral-600 mt-2 bg-neutral-50 px-2 py-1 rounded">
                  Current: {versions[0]?.checksum_sha256}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
