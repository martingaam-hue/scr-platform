"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  XCircle,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  ScoreGauge,
} from "@scr/ui";
import {
  useScreeningReport,
  useTriggerScreening,
  useTriggerMemo,
  useMemo,
  recommendationColor,
  type ScreeningReport,
  type MemoAcceptedResponse,
} from "@/lib/deals";

// ── Recommendation badge ──────────────────────────────────────────────────

function RecommendationBadge({ rec }: { rec: string }) {
  const color = recommendationColor(rec);
  const label =
    rec === "proceed"
      ? "Proceed"
      : rec === "pass"
        ? "Pass"
        : "Need More Info";
  const Icon =
    rec === "proceed"
      ? CheckCircle2
      : rec === "pass"
        ? XCircle
        : AlertTriangle;
  return (
    <Badge variant={color} className="flex items-center gap-1 text-sm px-3 py-1">
      <Icon className="h-4 w-4" />
      {label}
    </Badge>
  );
}

// ── Screening report ──────────────────────────────────────────────────────

function ScreeningReportView({
  report,
  projectId,
}: {
  report: ScreeningReport;
  projectId: string;
}) {
  const [memoId, setMemoId] = useState<string | undefined>();
  const triggerMemo = useTriggerMemo();
  const { data: memo } = useMemo(projectId, memoId);

  const handleGenerateMemo = async () => {
    const result = await triggerMemo.mutateAsync(projectId);
    setMemoId(result.memo_id);
  };

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-shrink-0">
          <ScoreGauge score={report.fit_score} size={120} label="Fit Score" />
        </div>
        <Card className="flex-1">
          <CardContent className="p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">
                  Recommendation
                </p>
                <RecommendationBadge rec={report.recommendation} />
              </div>
              <p className="text-xs text-neutral-400">
                {new Date(report.created_at).toLocaleDateString()}
              </p>
            </div>
            <p className="text-sm text-neutral-700 leading-relaxed">
              {report.executive_summary}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Strengths & Risks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm text-neutral-700 mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              Strengths
            </h3>
            <ul className="space-y-2">
              {report.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-neutral-700">{s}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm text-neutral-700 mb-3 flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              Risks
            </h3>
            <ul className="space-y-2">
              {report.risks.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <XCircle className="h-3.5 w-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                  <span className="text-neutral-700">{r}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Key Metrics & Mandate Alignment */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {report.key_metrics.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <h3 className="font-semibold text-sm text-neutral-700 mb-3">
                Key Metrics
              </h3>
              <table className="w-full text-sm">
                <tbody>
                  {report.key_metrics.map((m, i) => (
                    <tr key={i} className="border-b border-neutral-100 last:border-0">
                      <td className="py-1.5 text-neutral-500">{m.label}</td>
                      <td className="py-1.5 font-medium text-neutral-800 text-right">
                        {m.value}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
        {report.mandate_alignment.length > 0 && (
          <Card>
            <CardContent className="p-4">
              <h3 className="font-semibold text-sm text-neutral-700 mb-3">
                Mandate Alignment
              </h3>
              <ul className="space-y-2">
                {report.mandate_alignment.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    {a.met ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                    )}
                    <div>
                      <span className="font-medium text-neutral-700">
                        {a.criterion}
                      </span>
                      {a.notes && (
                        <span className="text-neutral-500 ml-1">— {a.notes}</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Questions to ask */}
      {report.questions_to_ask.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm text-neutral-700 mb-3">
              Questions to Ask
            </h3>
            <ol className="space-y-2">
              {report.questions_to_ask.map((q, i) => (
                <li key={i} className="flex gap-2 text-sm text-neutral-700">
                  <span className="font-semibold text-neutral-400 flex-shrink-0">
                    {i + 1}.
                  </span>
                  <span>{q}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {/* Memo section */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-sm text-neutral-700">
                Investment Memo
              </h3>
              <p className="text-xs text-neutral-500 mt-0.5">
                Generate a professional investment memorandum for this project.
              </p>
            </div>
            <div className="flex gap-2">
              {!memoId && !memo && (
                <Button
                  onClick={handleGenerateMemo}
                  disabled={triggerMemo.isPending}
                >
                  <FileText className="h-4 w-4 mr-1" />
                  {triggerMemo.isPending ? "Starting..." : "Generate Memo"}
                </Button>
              )}
              {memo && memo.status === "generating" && (
                <div className="flex items-center gap-2 text-sm text-neutral-500">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-600 border-t-transparent" />
                  Generating memo...
                </div>
              )}
              {memo && memo.status === "ready" && memo.download_url && (
                <Button asChild>
                  <a href={memo.download_url} target="_blank" rel="noopener noreferrer">
                    <Download className="h-4 w-4 mr-1" />
                    Download Memo
                  </a>
                </Button>
              )}
              {memo && memo.status === "error" && (
                <div className="flex items-center gap-2 text-sm text-red-600">
                  <XCircle className="h-4 w-4" />
                  Generation failed.{" "}
                  <button
                    className="underline"
                    onClick={() => {
                      setMemoId(undefined);
                      handleGenerateMemo();
                    }}
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DealScreeningPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();

  const {
    data: report,
    isLoading,
    error,
    refetch,
  } = useScreeningReport(projectId);

  const triggerScreening = useTriggerScreening();

  const handleRunScreening = async () => {
    await triggerScreening.mutateAsync(projectId);
    // Start polling
    refetch();
  };

  const isPolling =
    report && (report.status === "pending" || report.status === "processing");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/deals")}
        >
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Deals
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Screening Report</h1>
        <p className="text-neutral-500 mt-1">
          AI-powered deal analysis and mandate alignment review
        </p>
      </div>

      {isLoading && (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      )}

      {!isLoading && (error || !report) && (
        <EmptyState
          icon={<FileText className="h-12 w-12 text-neutral-400" />}
          title="No screening report yet"
          description="Run an AI screening to analyse this deal against your mandate."
          action={
            <Button
              onClick={handleRunScreening}
              disabled={triggerScreening.isPending}
            >
              {triggerScreening.isPending ? "Starting..." : "Run Screening"}
            </Button>
          }
        />
      )}

      {!isLoading && report && isPolling && (
        <Card>
          <CardContent className="p-8 flex flex-col items-center gap-4">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            <div className="text-center">
              <p className="font-medium text-neutral-700">
                Screening in progress...
              </p>
              <p className="text-sm text-neutral-500 mt-1">
                Our AI is analysing this deal against your mandate. This takes 30–60 seconds.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {!isLoading && report && report.status === "failed" && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <XCircle className="h-6 w-6 text-red-500" />
              <div>
                <p className="font-medium text-neutral-700">Screening failed</p>
                <p className="text-sm text-neutral-500">
                  An error occurred during analysis.
                </p>
              </div>
              <Button
                variant="outline"
                className="ml-auto"
                onClick={handleRunScreening}
                disabled={triggerScreening.isPending}
              >
                Retry Screening
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!isLoading && report && report.status === "completed" && (
        <ScreeningReportView report={report} projectId={projectId} />
      )}
    </div>
  );
}
