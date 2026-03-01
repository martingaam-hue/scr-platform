"use client";

import { useState } from "react";
import {
  BarChart2,
  Target,
  TrendingUp,
  CheckCircle,
  Loader2,
  Plus,
  X,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@scr/ui";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  useBacktestSummary,
  useBacktestRuns,
  useDealOutcomes,
  useRunBacktest,
  useRecordOutcome,
  type BacktestRun,
  type DealOutcome,
  type BacktestRunRequest,
  type RecordOutcomeRequest,
} from "@/lib/backtesting";

// ── Helpers ─────────────────────────────────────────────────────────────────

function pct(v: string | number | null | undefined): string {
  if (v == null) return "—";
  return (parseFloat(String(v)) * 100).toFixed(1) + "%";
}

function fmt2(v: string | number | null | undefined): string {
  if (v == null) return "—";
  return parseFloat(String(v)).toFixed(2);
}

function outcomeVariant(
  t: string
): "success" | "error" | "warning" | "neutral" {
  switch (t) {
    case "funded":
      return "success";
    case "passed":
      return "error";
    case "closed_lost":
      return "warning";
    default:
      return "neutral";
  }
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4">
        <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">
          {label}
        </p>
        <p className="text-2xl font-bold text-neutral-900">{value}</p>
        {sub && <p className="text-xs text-neutral-400 mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── Summary Tab ──────────────────────────────────────────────────────────────

function SummaryTab() {
  const { data, isLoading } = useBacktestSummary();

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!data) {
    return (
      <EmptyState
        icon={<BarChart2 className="h-8 w-8" />}
        title="No backtesting data"
        description="Record deal outcomes to start tracking score performance."
      />
    );
  }

  const latest = data.latest_run;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          label="Total Outcomes"
          value={String(data.total_outcomes)}
          sub="Recorded deals"
        />
        <KpiCard
          label="Funded Rate"
          value={data.funded_rate != null ? pct(data.funded_rate) : "—"}
          sub={`${data.funded_count} funded`}
        />
        <KpiCard
          label="Avg Score (Funded)"
          value={
            data.avg_score_of_funded != null
              ? fmt2(data.avg_score_of_funded)
              : "—"
          }
          sub="Signal score at decision"
        />
        <KpiCard
          label="Latest AUC-ROC"
          value={latest?.auc_roc != null ? fmt2(latest.auc_roc) : "—"}
          sub={latest ? `Run ${latest.id.slice(0, 8)}…` : "No runs yet"}
        />
      </div>

      {latest && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Latest Backtest Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center sm:grid-cols-5">
              {(
                [
                  ["Accuracy", pct(latest.accuracy)],
                  ["Precision", pct(latest.precision)],
                  ["Recall", pct(latest.recall)],
                  ["F1 Score", pct(latest.f1_score)],
                  ["AUC-ROC", fmt2(latest.auc_roc)],
                ] as [string, string][]
              ).map(([lbl, val]) => (
                <div key={lbl}>
                  <p className="text-xs text-neutral-500 mb-1">{lbl}</p>
                  <p className="text-lg font-semibold text-neutral-900">{val}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          label="Funded"
          value={String(data.funded_count)}
          sub="outcome_type = funded"
        />
        <KpiCard
          label="Passed"
          value={String(data.pass_count)}
          sub="outcome_type = passed"
        />
        <KpiCard
          label="Closed Lost"
          value={String(data.closed_lost_count)}
          sub="outcome_type = closed_lost"
        />
        <KpiCard
          label="In Progress"
          value={String(data.in_progress_count)}
          sub="outcome_type = in_progress"
        />
      </div>
    </div>
  );
}

// ── Backtest Tab ─────────────────────────────────────────────────────────────

function BacktestTab() {
  const { data: runs, isLoading: loadingRuns } = useBacktestRuns();
  const runBacktest = useRunBacktest();

  const [form, setForm] = useState<BacktestRunRequest>({
    methodology: "threshold",
    min_score_threshold: 50,
    date_from: undefined,
    date_to: undefined,
  });
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const selectedRun =
    runs?.find((r) => r.id === selectedRunId) ?? runs?.[0] ?? null;

  const cohortData =
    selectedRun?.results?.cohort_analysis?.quartiles?.map((q) => ({
      name: q.quartile,
      funded_rate: q.funded_rate != null ? +(q.funded_rate * 100).toFixed(1) : 0,
      count: q.count,
    })) ?? [];

  const calibrationData =
    selectedRun?.results?.metrics?.calibration?.map((b) => ({
      name: b.score_band,
      funded_rate:
        b.funded_rate != null ? +(b.funded_rate * 100).toFixed(1) : 0,
      count: b.count,
    })) ?? [];

  async function handleRun() {
    const result = await runBacktest.mutateAsync(form);
    setSelectedRunId(result.id);
  }

  return (
    <div className="space-y-6">
      {/* Run form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Run Backtest</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Methodology
              </label>
              <select
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                value={form.methodology}
                onChange={(e) =>
                  setForm((f) => ({ ...f, methodology: e.target.value }))
                }
              >
                <option value="threshold">Threshold</option>
                <option value="cohort">Cohort</option>
                <option value="time_series">Time Series</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Score Threshold: {form.min_score_threshold}
              </label>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={form.min_score_threshold ?? 50}
                className="w-full"
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    min_score_threshold: parseInt(e.target.value),
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Date From
              </label>
              <input
                type="date"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                value={form.date_from ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    date_from: e.target.value || undefined,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Date To
              </label>
              <input
                type="date"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                value={form.date_to ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    date_to: e.target.value || undefined,
                  }))
                }
              />
            </div>
          </div>
          <Button
            onClick={handleRun}
            disabled={runBacktest.isPending}
            size="sm"
          >
            {runBacktest.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <TrendingUp className="h-4 w-4 mr-2" />
            )}
            Run Backtest
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {loadingRuns ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : !runs?.length ? (
        <EmptyState
          icon={<BarChart2 className="h-8 w-8" />}
          title="No backtest runs yet"
          description="Configure and run your first backtest above."
        />
      ) : (
        <>
          {/* Run selector */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-neutral-500">Run:</span>
            {runs.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedRunId(r.id)}
                className={`text-xs px-2 py-1 rounded border transition-colors ${
                  (selectedRunId ?? runs[0]?.id) === r.id
                    ? "bg-blue-50 border-blue-300 text-blue-700"
                    : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                }`}
              >
                {r.methodology} &mdash;{" "}
                {new Date(r.created_at).toLocaleDateString()}
              </button>
            ))}
          </div>

          {selectedRun && (
            <>
              {/* Metrics table */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Performance Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-neutral-100">
                        {[
                          "Metric",
                          "Value",
                          "Threshold",
                          "Sample Size",
                          "TP",
                          "FP",
                          "TN",
                          "FN",
                        ].map((h) => (
                          <th
                            key={h}
                            className="pb-2 text-left text-xs font-medium text-neutral-500"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        [
                          ["Accuracy", pct(selectedRun.accuracy)],
                          ["Precision", pct(selectedRun.precision)],
                          ["Recall", pct(selectedRun.recall)],
                          ["F1 Score", pct(selectedRun.f1_score)],
                          ["AUC-ROC", fmt2(selectedRun.auc_roc)],
                        ] as [string, string][]
                      ).map(([metric, value], i) => (
                        <tr
                          key={metric}
                          className="border-b border-neutral-50 last:border-0"
                        >
                          <td className="py-2 font-medium">{metric}</td>
                          <td className="py-2 text-blue-700 font-semibold">
                            {value}
                          </td>
                          {i === 0 ? (
                            <>
                              <td
                                className="py-2"
                                rowSpan={5}
                              >
                                {selectedRun.min_score_threshold ?? "—"}
                              </td>
                              <td className="py-2" rowSpan={5}>
                                {selectedRun.sample_size ?? "—"}
                              </td>
                              <td className="py-2" rowSpan={5}>
                                {selectedRun.results?.metrics?.tp ?? "—"}
                              </td>
                              <td className="py-2" rowSpan={5}>
                                {selectedRun.results?.metrics?.fp ?? "—"}
                              </td>
                              <td className="py-2" rowSpan={5}>
                                {selectedRun.results?.metrics?.tn ?? "—"}
                              </td>
                              <td className="py-2" rowSpan={5}>
                                {selectedRun.results?.metrics?.fn ?? "—"}
                              </td>
                            </>
                          ) : null}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>

              {/* Cohort chart */}
              {cohortData.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">
                      Funded Rate by Score Quartile
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={cohortData} margin={{ left: 0, right: 8 }}>
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#f0f0f0"
                        />
                        <XAxis
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                        />
                        <YAxis
                          tickFormatter={(v: number) => `${v}%`}
                          tick={{ fontSize: 11 }}
                        />
                        <Tooltip
                          formatter={(v: number | string | undefined) =>
                            v != null ? [`${v}%`, "Funded Rate"] : ["—", "Funded Rate"]
                          }
                        />
                        <Bar
                          dataKey="funded_rate"
                          fill="#3b82f6"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}

              {/* Calibration chart */}
              {calibrationData.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">
                      Score Calibration (Funded Rate by Score Band)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart
                        data={calibrationData}
                        margin={{ left: 0, right: 8 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="#f0f0f0"
                        />
                        <XAxis
                          dataKey="name"
                          tick={{ fontSize: 11 }}
                        />
                        <YAxis
                          tickFormatter={(v: number) => `${v}%`}
                          tick={{ fontSize: 11 }}
                        />
                        <Tooltip
                          formatter={(v: number | string | undefined) =>
                            v != null ? [`${v}%`, "Funded Rate"] : ["—", "Funded Rate"]
                          }
                        />
                        <Bar
                          dataKey="funded_rate"
                          fill="#10b981"
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

// ── Record Outcome Inline Form ────────────────────────────────────────────────

function RecordOutcomeForm({ onClose }: { onClose: () => void }) {
  const recordOutcome = useRecordOutcome();
  const [form, setForm] = useState<RecordOutcomeRequest>({
    outcome_type: "funded",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await recordOutcome.mutateAsync(form);
    onClose();
  }

  return (
    <Card className="border-blue-200 bg-blue-50/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Record Deal Outcome</CardTitle>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600">
            <X className="h-4 w-4" />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Outcome Type *
              </label>
              <select
                required
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                value={form.outcome_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, outcome_type: e.target.value }))
                }
              >
                <option value="funded">Funded</option>
                <option value="passed">Passed</option>
                <option value="closed_lost">Closed Lost</option>
                <option value="in_progress">In Progress</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Score at Decision
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                placeholder="e.g. 72.5"
                value={form.signal_score_at_decision ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    signal_score_at_decision: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Score at Evaluation
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                placeholder="e.g. 65.0"
                value={form.signal_score_at_evaluation ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    signal_score_at_evaluation: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Actual IRR
              </label>
              <input
                type="number"
                step="0.0001"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                placeholder="e.g. 0.18"
                value={form.actual_irr ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    actual_irr: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Actual MOIC
              </label>
              <input
                type="number"
                step="0.01"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                placeholder="e.g. 2.5"
                value={form.actual_moic ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    actual_moic: e.target.value
                      ? parseFloat(e.target.value)
                      : undefined,
                  }))
                }
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600 block mb-1">
                Decision Date
              </label>
              <input
                type="date"
                className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white"
                value={form.decision_date ?? ""}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    decision_date: e.target.value || undefined,
                  }))
                }
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-neutral-600 block mb-1">
              Notes
            </label>
            <textarea
              rows={2}
              className="w-full text-sm border border-neutral-200 rounded px-2 py-1.5 bg-white resize-none"
              placeholder="Optional notes..."
              value={form.notes ?? ""}
              onChange={(e) =>
                setForm((f) => ({ ...f, notes: e.target.value || undefined }))
              }
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={recordOutcome.isPending}>
              {recordOutcome.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Save Outcome
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onClose}
            >
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

// ── Outcomes Tab ─────────────────────────────────────────────────────────────

function OutcomesTab() {
  const { data: outcomes, isLoading } = useDealOutcomes();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-neutral-500">
          {outcomes?.length ?? 0} outcomes recorded
        </p>
        {!showForm && (
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Record Outcome
          </Button>
        )}
      </div>

      {showForm && (
        <RecordOutcomeForm onClose={() => setShowForm(false)} />
      )}

      {isLoading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : !outcomes?.length ? (
        <EmptyState
          icon={<Target className="h-8 w-8" />}
          title="No outcomes recorded"
          description="Record your first deal outcome to start tracking score accuracy."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-neutral-50 border-b border-neutral-100">
                  <tr>
                    {[
                      "Project",
                      "Outcome",
                      "Score at Decision",
                      "IRR",
                      "MOIC",
                      "Decision Date",
                      "Outcome Date",
                    ].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-left text-xs font-medium text-neutral-500"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {outcomes.map((o) => (
                    <tr
                      key={o.id}
                      className="border-b border-neutral-50 last:border-0 hover:bg-neutral-50/50 transition-colors"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-neutral-500">
                        {o.project_id ? o.project_id.slice(0, 8) + "…" : "—"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={outcomeVariant(o.outcome_type)}>
                          {o.outcome_type.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 font-semibold">
                        {o.signal_score_at_decision
                          ? parseFloat(o.signal_score_at_decision).toFixed(1)
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {o.actual_irr
                          ? (
                              parseFloat(o.actual_irr) * 100
                            ).toFixed(1) + "%"
                          : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {o.actual_moic
                          ? parseFloat(o.actual_moic).toFixed(2) + "x"
                          : "—"}
                      </td>
                      <td className="px-4 py-3 text-neutral-500">
                        {o.decision_date ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-neutral-500">
                        {o.outcome_date ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function ScorePerformancePage() {
  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <BarChart2 className="h-6 w-6 text-blue-600" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">
            Score Performance
          </h1>
          <p className="text-sm text-neutral-500">
            Backtest signal score accuracy against actual deal outcomes
          </p>
        </div>
      </div>

      <Tabs defaultValue="summary">
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="backtest">Backtest</TabsTrigger>
          <TabsTrigger value="outcomes">Outcomes</TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="mt-6">
          <SummaryTab />
        </TabsContent>

        <TabsContent value="backtest" className="mt-6">
          <BacktestTab />
        </TabsContent>

        <TabsContent value="outcomes" className="mt-6">
          <OutcomesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
