"use client";

import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Leaf,
  RefreshCw,
  ShoppingCart,
  TrendingUp,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  LineChart,
} from "@scr/ui";
import { useProject } from "@/lib/projects";
import { usePermission } from "@/lib/auth";
import {
  useCarbonCredit,
  useEstimateCarbonCredits,
  useSubmitVerification,
  usePricingTrends,
  useMethodologies,
  verificationStatusBadge,
  confidenceColor,
  VERIFICATION_STATUS_LABELS,
  SCENARIO_LABELS,
  type CarbonCreditResponse,
} from "@/lib/carbon-credits";

// ── Verification timeline ─────────────────────────────────────────────────────

const VERIFICATION_STAGES = [
  "estimated",
  "submitted",
  "verified",
  "issued",
  "retired",
];

function VerificationTimeline({ status }: { status: string }) {
  const current = VERIFICATION_STAGES.indexOf(status);
  return (
    <div className="flex items-center gap-0">
      {VERIFICATION_STAGES.map((stage, i) => {
        const done = i <= current;
        const active = i === current;
        return (
          <div key={stage} className="flex items-center">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                done
                  ? "bg-green-500 text-white"
                  : "bg-neutral-200 text-neutral-400"
              } ${active ? "ring-2 ring-green-400 ring-offset-1" : ""}`}
            >
              {done ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
            </div>
            {i < VERIFICATION_STAGES.length - 1 && (
              <div
                className={`h-1 w-8 transition-colors ${
                  i < current ? "bg-green-400" : "bg-neutral-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Revenue Projection Table ──────────────────────────────────────────────────

function RevenueProjection({
  projection,
}: {
  projection: NonNullable<CarbonCreditResponse["revenue_projection"]>;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-200">
            <th className="py-2 px-3 text-left text-xs font-semibold text-neutral-500">
              Scenario
            </th>
            <th className="py-2 px-3 text-right text-xs font-semibold text-neutral-500">
              Price/t CO₂e
            </th>
            <th className="py-2 px-3 text-right text-xs font-semibold text-neutral-500">
              Annual Revenue
            </th>
            <th className="py-2 px-3 text-right text-xs font-semibold text-neutral-500">
              10-Year Revenue
            </th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(projection.scenarios).map(([key, s]) => (
            <tr key={key} className="border-b border-neutral-100 hover:bg-neutral-50">
              <td className="py-2 px-3 font-medium text-neutral-700 capitalize">
                {SCENARIO_LABELS[key] ?? key.replace("_", " ")}
              </td>
              <td className="py-2 px-3 text-right text-neutral-600">
                ${s.price_per_ton_usd.toFixed(2)}
              </td>
              <td className="py-2 px-3 text-right font-semibold text-neutral-800">
                ${s.annual_revenue_usd.toLocaleString()}
              </td>
              <td className="py-2 px-3 text-right text-neutral-600">
                ${s["10yr_revenue_usd"].toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CarbonPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const canEdit = usePermission("edit", "project");

  const { data: project } = useProject(id);
  const { data: cc, isLoading } = useCarbonCredit(id);
  const estimate = useEstimateCarbonCredits(id);
  const submitVerification = useSubmitVerification(id);
  const { data: trends } = usePricingTrends();
  const { data: methodologies } = useMethodologies();

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
          Back to {project?.name ?? "Project"}
        </button>
        <div className="flex items-start justify-between">
          <h1 className="text-2xl font-bold text-neutral-900">
            Carbon Credits
          </h1>
          {canEdit && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => estimate.mutate()}
                disabled={estimate.isPending}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${estimate.isPending ? "animate-spin" : ""}`}
                />
                Recalculate
              </Button>
              {cc && cc.verification_status === "estimated" && (
                <Button
                  onClick={() => submitVerification.mutate()}
                  disabled={submitVerification.isPending}
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Submit for Verification
                </Button>
              )}
              {cc && cc.verification_status === "verified" && (
                <Button variant="outline">
                  <ShoppingCart className="mr-2 h-4 w-4" />
                  List on Marketplace
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {!cc ? (
        <EmptyState
          icon={<Leaf className="h-12 w-12 text-neutral-400" />}
          title="No carbon credit estimate"
          description="Run a carbon credit estimation to see the potential for this project."
          action={
            canEdit ? (
              <Button
                onClick={() => estimate.mutate()}
                disabled={estimate.isPending}
              >
                <Leaf className="mr-2 h-4 w-4" />
                Estimate Carbon Credits
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-5">
                <p className="text-xs text-neutral-500">Estimated Annual</p>
                <p className="text-2xl font-bold text-green-600">
                  {cc.quantity_tons.toLocaleString()}
                </p>
                <p className="text-xs text-neutral-400">tCO₂e / year</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs text-neutral-500">Methodology</p>
                <p className="text-sm font-semibold text-neutral-800 mt-1">
                  {cc.methodology}
                </p>
                <p className="text-xs text-neutral-400">
                  {cc.registry}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs text-neutral-500">Verification Status</p>
                <div className="mt-1">
                  <Badge variant={verificationStatusBadge(cc.verification_status)}>
                    {VERIFICATION_STATUS_LABELS[cc.verification_status] ?? cc.verification_status}
                  </Badge>
                </div>
                {cc.verification_body && (
                  <p className="text-xs text-neutral-400 mt-1">
                    {cc.verification_body}
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <p className="text-xs text-neutral-500">Base Case Revenue</p>
                <p className="text-2xl font-bold text-neutral-800">
                  $
                  {(
                    cc.revenue_projection?.scenarios?.base_case?.annual_revenue_usd ?? 0
                  ).toLocaleString()}
                </p>
                <p className="text-xs text-neutral-400">per year @ $15/t</p>
              </CardContent>
            </Card>
          </div>

          {/* Verification timeline */}
          <Card>
            <CardContent className="p-5">
              <p className="text-sm font-semibold text-neutral-700 mb-4">
                Verification Progress
              </p>
              <VerificationTimeline status={cc.verification_status} />
              <div className="flex justify-between mt-2">
                {["Estimated", "Submitted", "Verified", "Issued", "Retired"].map(
                  (label) => (
                    <span key={label} className="text-xs text-neutral-400">
                      {label}
                    </span>
                  )
                )}
              </div>
            </CardContent>
          </Card>

          {/* Revenue projection */}
          {cc.revenue_projection && (
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <p className="text-sm font-semibold text-neutral-700">
                    Revenue Projection ({cc.quantity_tons.toLocaleString()} tCO₂e/yr)
                  </p>
                </div>
                <RevenueProjection projection={cc.revenue_projection} />
              </CardContent>
            </Card>
          )}

          {/* Pricing trends */}
          {trends && trends.length > 0 && (
            <Card>
              <CardContent className="p-5">
                <p className="text-sm font-semibold text-neutral-700 mb-4">
                  Carbon Market Price Trends (USD/t)
                </p>
                <LineChart
                  data={trends.slice(-12).map((t) => ({
                    date: t.date.slice(0, 7),
                    "VCS/Verra": t.vcs_price,
                    "Gold Standard": t.gold_standard_price,
                    "EU ETS": t.eu_ets_price,
                  }))}
                  xKey="date"
                  yKeys={["VCS/Verra", "Gold Standard", "EU ETS"]}
                  height={220}
                />
              </CardContent>
            </Card>
          )}

          {/* Methodology selector */}
          {methodologies && (
            <Card>
              <CardContent className="p-5">
                <p className="text-sm font-semibold text-neutral-700 mb-3">
                  Available Methodologies
                </p>
                <div className="space-y-3">
                  {methodologies.map((m) => (
                    <div
                      key={m.id}
                      className={`p-3 rounded-lg border ${
                        m.id === cc.methodology
                          ? "border-green-300 bg-green-50"
                          : "border-neutral-200"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-neutral-800">
                            {m.id} — {m.registry}
                          </p>
                          <p className="text-xs text-neutral-500">{m.name}</p>
                        </div>
                        <Badge
                          variant={
                            m.verification_complexity === "low"
                              ? "success"
                              : m.verification_complexity === "medium"
                                ? "warning"
                                : "error"
                          }
                        >
                          {m.verification_complexity} complexity
                        </Badge>
                      </div>
                      <p className="text-xs text-neutral-600 mt-1">{m.description}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
