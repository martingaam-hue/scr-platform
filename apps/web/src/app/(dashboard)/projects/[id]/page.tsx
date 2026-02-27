"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Copy,
  DollarSign,
  FileText,
  Globe,
  MapPin,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@scr/ui";
import {
  useCalculateScore,
} from "@/lib/signal-score";
import {
  useGenerateBusinessPlan,
  useBusinessPlanResult,
  BUSINESS_PLAN_ACTIONS,
  type BusinessPlanActionKey,
} from "@/lib/business-plan";
import { usePermission } from "@/lib/auth";
import {
  useProject,
  useMilestones,
  useBudgetItems,
  usePublishProject,
  useDeleteProject,
  projectTypeLabel,
  projectStatusColor,
  stageLabel,
  formatCurrency,
  type MilestoneResponse,
  type BudgetItemResponse,
  type BusinessPlanResultResponse,
} from "@/lib/projects";

// ── AI Tools Tab ─────────────────────────────────────────────────────────────

function AIToolResultCard({
  projectId,
  actionKey,
}: {
  projectId: string;
  actionKey: BusinessPlanActionKey;
}) {
  const action = BUSINESS_PLAN_ACTIONS[actionKey];
  const [taskLogId, setTaskLogId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const generate = useGenerateBusinessPlan(projectId);
  const { data: result } = useBusinessPlanResult(projectId, taskLogId ?? undefined);

  const handleGenerate = async () => {
    const res = await generate.mutateAsync(actionKey);
    setTaskLogId(res.task_log_id);
  };

  const handleCopy = () => {
    if (result?.content) {
      navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isPending = result?.status === "pending" || result?.status === "processing";
  const isComplete = result?.status === "completed";
  const isFailed = result?.status === "failed";

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">{action.icon}</span>
            <div>
              <h4 className="font-semibold text-neutral-900 text-sm">{action.label}</h4>
              <p className="text-xs text-neutral-500">{action.description}</p>
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            {isComplete && result.content && (
              <Button size="sm" variant="outline" onClick={handleCopy}>
                <Copy className="h-3.5 w-3.5 mr-1" />
                {copied ? "Copied!" : "Copy"}
              </Button>
            )}
            <Button
              size="sm"
              onClick={handleGenerate}
              disabled={generate.isPending || isPending}
            >
              {isPending ? (
                <RefreshCw className="h-3.5 w-3.5 mr-1 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5 mr-1" />
              )}
              {isComplete ? "Regenerate" : isPending ? "Generating…" : "Generate"}
            </Button>
          </div>
        </div>

        {isFailed && (
          <p className="mt-3 text-xs text-red-600 bg-red-50 rounded p-2">
            Generation failed. Please try again.
          </p>
        )}

        {isComplete && result.content && (
          <div className="mt-4 border-t pt-4">
            <p className="text-sm text-neutral-700 whitespace-pre-wrap leading-relaxed">
              {result.content}
            </p>
            {result.model_used && (
              <p className="mt-2 text-xs text-neutral-400">{result.model_used}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AIToolsTab({ projectId }: { projectId: string }) {
  const actionKeys = Object.keys(BUSINESS_PLAN_ACTIONS) as BusinessPlanActionKey[];
  return (
    <div className="space-y-4">
      <p className="text-sm text-neutral-500">
        Generate AI-powered content for your project. Each action uses your project data to produce relevant, investment-ready text.
      </p>
      <div className="grid grid-cols-1 gap-4">
        {actionKeys.map((key) => (
          <AIToolResultCard key={key} projectId={projectId} actionKey={key} />
        ))}
      </div>
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function MilestoneStatusBadge({ status }: { status: string }) {
  const color =
    status === "completed"
      ? "success"
      : status === "in_progress"
        ? "warning"
        : status === "delayed" || status === "blocked"
          ? "error"
          : "neutral";
  return <Badge variant={color}>{status.replace("_", " ")}</Badge>;
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const canEdit = usePermission("edit", "project");
  const canDelete = usePermission("delete", "project");
  const canAnalyze = usePermission("run_analysis", "analysis");

  const { data: project, isLoading } = useProject(id);
  const { data: milestones } = useMilestones(id);
  const { data: budgetItems } = useBudgetItems(id);
  const publishMutation = usePublishProject();
  const deleteMutation = useDeleteProject();
  const calculateScore = useCalculateScore();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!project) {
    return (
      <EmptyState
        icon={<FileText className="h-12 w-12 text-neutral-400" />}
        title="Project not found"
        description="This project may have been deleted or you don't have access."
        action={
          <Button variant="outline" onClick={() => router.push("/projects")}>
            Back to Projects
          </Button>
        }
      />
    );
  }

  const handlePublish = () => {
    publishMutation.mutate(id);
  };

  const handleDelete = () => {
    if (confirm("Are you sure you want to delete this project?")) {
      deleteMutation.mutate(id, {
        onSuccess: () => router.push("/projects"),
      });
    }
  };

  const totalBudgetEstimated = budgetItems?.reduce(
    (sum, b) => sum + parseFloat(b.estimated_amount),
    0
  ) ?? 0;
  const totalBudgetActual = budgetItems?.reduce(
    (sum, b) => sum + (b.actual_amount ? parseFloat(b.actual_amount) : 0),
    0
  ) ?? 0;

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <button
          onClick={() => router.push("/projects")}
          className="mb-4 flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Projects
        </button>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-900">
                {project.name}
              </h1>
              <Badge variant={projectStatusColor(project.status)}>
                {project.status.replace("_", " ")}
              </Badge>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-neutral-500">
              <span className="flex items-center gap-1">
                <Zap className="h-4 w-4" />
                {projectTypeLabel(project.project_type)}
              </span>
              <span className="flex items-center gap-1">
                <TrendingUp className="h-4 w-4" />
                {stageLabel(project.stage)}
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="h-4 w-4" />
                {project.geography_country}
                {project.geography_region && `, ${project.geography_region}`}
              </span>
              <span className="flex items-center gap-1">
                <DollarSign className="h-4 w-4" />
                {formatCurrency(
                  project.total_investment_required,
                  project.currency
                )}
              </span>
            </div>
          </div>
          <div className="flex gap-2">
            {canEdit && !project.is_published && (
              <Button
                variant="outline"
                onClick={handlePublish}
                disabled={publishMutation.isPending}
              >
                <Globe className="mr-2 h-4 w-4" />
                Publish
              </Button>
            )}
            {canDelete && (
              <Button
                variant="outline"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="text-red-600 hover:bg-red-50"
              >
                Delete
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="milestones">
            Milestones ({project.milestone_count})
          </TabsTrigger>
          <TabsTrigger value="financials">
            Financials ({project.budget_item_count})
          </TabsTrigger>
          <TabsTrigger value="signal">Signal Score</TabsTrigger>
          {canAnalyze && (
            <TabsTrigger value="ai-tools">AI Tools</TabsTrigger>
          )}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-6 space-y-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Description */}
            <Card className="lg:col-span-2">
              <CardContent className="p-6">
                <h3 className="mb-3 font-semibold text-neutral-900">Description</h3>
                <p className="text-sm text-neutral-600 whitespace-pre-wrap">
                  {project.description || "No description provided."}
                </p>
              </CardContent>
            </Card>

            {/* Quick stats */}
            <Card>
              <CardContent className="space-y-4 p-6">
                <h3 className="font-semibold text-neutral-900">Details</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Signal Score</span>
                    <span className="font-medium">
                      {project.latest_signal_score ?? "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Documents</span>
                    <span className="font-medium">{project.document_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Capacity</span>
                    <span className="font-medium">
                      {project.capacity_mw
                        ? `${project.capacity_mw} MW`
                        : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Currency</span>
                    <span className="font-medium">{project.currency}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Published</span>
                    <span className="font-medium">
                      {project.is_published ? "Yes" : "No"}
                    </span>
                  </div>
                  {project.target_close_date && (
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Target Close</span>
                      <span className="font-medium">
                        {new Date(project.target_close_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Funding progress */}
          <Card>
            <CardContent className="p-6">
              <h3 className="mb-3 font-semibold text-neutral-900">
                Funding Required
              </h3>
              <div className="text-3xl font-bold text-neutral-900">
                {formatCurrency(
                  project.total_investment_required,
                  project.currency
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Milestones Tab */}
        <TabsContent value="milestones" className="mt-6">
          {!milestones?.length ? (
            <EmptyState
              icon={<CheckCircle2 className="h-12 w-12 text-neutral-400" />}
              title="No milestones"
              description="Add milestones to track project progress."
            />
          ) : (
            <div className="space-y-3">
              {milestones.map((m: MilestoneResponse) => (
                <Card key={m.id}>
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-3">
                        <p className="font-medium text-neutral-900">
                          {m.name}
                        </p>
                        <MilestoneStatusBadge status={m.status} />
                      </div>
                      {m.description && (
                        <p className="mt-1 text-sm text-neutral-500 truncate">
                          {m.description}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-6 text-sm text-neutral-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {new Date(m.target_date).toLocaleDateString()}
                      </div>
                      <div className="w-32">
                        <div className="flex justify-between text-xs mb-1">
                          <span>{m.completion_pct}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-neutral-200">
                          <div
                            className="h-2 rounded-full bg-primary-600"
                            style={{ width: `${m.completion_pct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Financials Tab */}
        <TabsContent value="financials" className="mt-6 space-y-6">
          {/* Budget summary */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-neutral-500">Estimated Total</p>
                <p className="text-2xl font-semibold text-neutral-900">
                  {formatCurrency(totalBudgetEstimated)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-neutral-500">Actual Spent</p>
                <p className="text-2xl font-semibold text-neutral-900">
                  {formatCurrency(totalBudgetActual)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-sm text-neutral-500">Utilization</p>
                <p className="text-2xl font-semibold text-neutral-900">
                  {totalBudgetEstimated > 0
                    ? `${((totalBudgetActual / totalBudgetEstimated) * 100).toFixed(1)}%`
                    : "—"}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Budget items table */}
          {!budgetItems?.length ? (
            <EmptyState
              icon={<DollarSign className="h-12 w-12 text-neutral-400" />}
              title="No budget items"
              description="Add budget items to track project financials."
            />
          ) : (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-neutral-500">
                      <th className="px-4 py-3 font-medium">Category</th>
                      <th className="px-4 py-3 font-medium">Description</th>
                      <th className="px-4 py-3 font-medium text-right">
                        Estimated
                      </th>
                      <th className="px-4 py-3 font-medium text-right">
                        Actual
                      </th>
                      <th className="px-4 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {budgetItems.map((b: BudgetItemResponse) => (
                      <tr key={b.id} className="border-b last:border-0">
                        <td className="px-4 py-3 font-medium text-neutral-900">
                          {b.category}
                        </td>
                        <td className="px-4 py-3 text-neutral-600">
                          {b.description || "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-neutral-700">
                          {formatCurrency(b.estimated_amount, b.currency)}
                        </td>
                        <td className="px-4 py-3 text-right text-neutral-700">
                          {b.actual_amount
                            ? formatCurrency(b.actual_amount, b.currency)
                            : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant={
                              b.status === "spent"
                                ? "success"
                                : b.status === "committed"
                                  ? "warning"
                                  : b.status === "over_budget"
                                    ? "error"
                                    : "neutral"
                            }
                          >
                            {b.status.replace("_", " ")}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </TabsContent>

        {/* AI Tools Tab */}
        {canAnalyze && (
          <TabsContent value="ai-tools" className="mt-6">
            <AIToolsTab projectId={id} />
          </TabsContent>
        )}

        {/* Signal Score Tab */}
        <TabsContent value="signal" className="mt-6">
          {!project.latest_signal ? (
            <EmptyState
              icon={<Target className="h-12 w-12 text-neutral-400" />}
              title="No Signal Score"
              description="Signal Score analysis hasn't been run for this project yet."
              action={
                canAnalyze ? (
                  <Button
                    onClick={() => calculateScore.mutate(id)}
                    disabled={calculateScore.isPending}
                  >
                    Calculate Signal Score
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                {/* Overall score gauge */}
                <Card className="lg:col-span-1">
                  <CardContent className="flex flex-col items-center p-6">
                    <ScoreGauge
                      score={project.latest_signal.overall_score}
                      size={120}
                      strokeWidth={10}
                    />
                    <p className="mt-2 text-xs text-neutral-400">
                      v{project.latest_signal.version} &middot;{" "}
                      {project.latest_signal.model_used}
                    </p>
                  </CardContent>
                </Card>

                {/* Dimension gauges */}
                <Card className="lg:col-span-2">
                  <CardContent className="p-6">
                    <h3 className="mb-4 font-semibold text-neutral-900">
                      Breakdown
                    </h3>
                    <div className="grid grid-cols-3 sm:grid-cols-6 gap-4">
                      <ScoreGauge
                        score={project.latest_signal.project_viability_score}
                        size={72}
                        strokeWidth={7}
                        label="Viability"
                      />
                      <ScoreGauge
                        score={project.latest_signal.financial_planning_score}
                        size={72}
                        strokeWidth={7}
                        label="Financial"
                      />
                      <ScoreGauge
                        score={project.latest_signal.esg_score}
                        size={72}
                        strokeWidth={7}
                        label="ESG"
                      />
                      <ScoreGauge
                        score={project.latest_signal.risk_assessment_score}
                        size={72}
                        strokeWidth={7}
                        label="Risk"
                      />
                      <ScoreGauge
                        score={project.latest_signal.team_strength_score}
                        size={72}
                        strokeWidth={7}
                        label="Team"
                      />
                      <ScoreGauge
                        score={project.latest_signal.market_opportunity_score}
                        size={72}
                        strokeWidth={7}
                        label="Market"
                      />
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="flex justify-center">
                <Button
                  variant="outline"
                  onClick={() => router.push(`/projects/${id}/signal-score`)}
                >
                  View Full Analysis
                  <ArrowLeft className="ml-2 h-4 w-4 rotate-180" />
                </Button>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
