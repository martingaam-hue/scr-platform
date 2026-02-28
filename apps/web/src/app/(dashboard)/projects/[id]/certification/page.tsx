"use client";

import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Award,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  ScoreGauge,
} from "@scr/ui";
import { useProject } from "@/lib/projects";
import { usePermission } from "@/lib/auth";
import {
  useCertification,
  useCertificationRequirements,
  useEvaluateCertification,
  TIER_LABELS,
  TIER_COLORS,
  STATUS_LABELS,
  tierVariant,
  type CertificationGap,
} from "@/lib/certification";

// ── Sub-components ────────────────────────────────────────────────────────────

function TierBadge({ tier }: { tier: string | null }) {
  if (!tier) return null;
  const color = TIER_COLORS[tier] ?? "#6b7280";
  const label = TIER_LABELS[tier] ?? tier;
  return (
    <div
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold text-white"
      style={{ backgroundColor: color }}
    >
      <Award className="h-4 w-4" />
      {label}
    </div>
  );
}

function GapRow({ gap }: { gap: CertificationGap }) {
  const label = gap.type === "dimension_score"
    ? `${gap.dimension} score`
    : gap.type.replace(/_/g, " ");

  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <div className="flex items-center gap-2">
        <XCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
        <span className="text-sm text-neutral-700 capitalize">{label}</span>
      </div>
      <div className="text-right text-sm">
        <span className="text-neutral-400">
          {typeof gap.current === "number" ? gap.current.toFixed(0) : gap.current}
        </span>
        <span className="mx-1 text-neutral-300">/</span>
        <span className="font-medium text-neutral-700">
          {typeof gap.needed === "number" ? gap.needed.toFixed(0) : gap.needed}{" "}
          needed
        </span>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CertificationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const canAnalyze = usePermission("run_analysis", "analysis");

  const { data: project } = useProject(id);
  const { data: cert, isLoading: certLoading } = useCertification(id);
  const { data: requirements, isLoading: reqLoading } =
    useCertificationRequirements(id);
  const evaluate = useEvaluateCertification(id);

  const isLoading = certLoading || reqLoading;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  const isCertified = cert?.status === "certified";
  const score = cert?.certification_score ?? requirements?.current_score ?? null;

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
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <ShieldCheck className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">
                Investor Readiness Certification
              </h1>
              <p className="text-sm text-neutral-500 mt-0.5">
                Official certification confirming this project meets investment standards
              </p>
            </div>
          </div>
          {canAnalyze && (
            <Button
              variant="outline"
              onClick={() => evaluate.mutate()}
              disabled={evaluate.isPending}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${evaluate.isPending ? "animate-spin" : ""}`}
              />
              Re-evaluate
            </Button>
          )}
        </div>
      </div>

      {/* Status card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-1">
          <CardContent className="flex flex-col items-center justify-center p-8 gap-4">
            {score !== null ? (
              <ScoreGauge score={score} size={140} strokeWidth={12} />
            ) : (
              <div className="h-32 w-32 rounded-full border-4 border-neutral-200 flex items-center justify-center">
                <span className="text-neutral-400 text-sm">No score</span>
              </div>
            )}
            {isCertified ? (
              <>
                <TierBadge tier={cert!.tier} />
                <div className="text-center">
                  <p className="text-sm font-semibold text-green-700 flex items-center gap-1 justify-center">
                    <CheckCircle2 className="h-4 w-4" />
                    Certified
                  </p>
                  {cert!.certified_at && (
                    <p className="text-xs text-neutral-400 mt-1">
                      Since{" "}
                      {new Date(cert!.certified_at).toLocaleDateString(
                        undefined,
                        { year: "numeric", month: "long", day: "numeric" }
                      )}
                    </p>
                  )}
                  {cert!.consecutive_months_certified > 0 && (
                    <p className="text-xs text-neutral-400">
                      {cert!.consecutive_months_certified} consecutive months
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className="text-center">
                <Badge variant="neutral">
                  {STATUS_LABELS[cert?.status ?? "not_certified"] ?? "Not Certified"}
                </Badge>
                {cert?.status === "expired" && cert.last_verified_at && (
                  <p className="text-xs text-neutral-400 mt-1">
                    Expired{" "}
                    {new Date(cert.last_verified_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Dimension scores */}
        {cert?.dimension_scores &&
          Object.keys(cert.dimension_scores).length > 0 && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-sm">Dimension Scores</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(cert.dimension_scores).map(([dim, val]) => {
                    const pct = Math.min(100, Math.max(0, val));
                    const color =
                      pct >= 80
                        ? "bg-green-500"
                        : pct >= 60
                        ? "bg-amber-500"
                        : "bg-red-500";
                    return (
                      <div key={dim}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-neutral-600 capitalize">
                            {dim.replace(/_/g, " ")}
                          </span>
                          <span className="font-semibold text-neutral-800">
                            {pct.toFixed(0)}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
                          <div
                            className={`h-2 rounded-full transition-all ${color}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
      </div>

      {/* Requirements / gaps */}
      {requirements && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Certification Requirements</CardTitle>
              <Badge variant={requirements.eligible ? "success" : "neutral"}>
                {requirements.eligible ? "Eligible" : "Not yet eligible"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {requirements.gaps.length === 0 ? (
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle2 className="h-5 w-5" />
                <p className="text-sm font-medium">
                  All requirements met — you qualify for certification!
                </p>
              </div>
            ) : (
              <div>
                <p className="text-xs text-neutral-500 mb-3">
                  {requirements.gaps.length} gap
                  {requirements.gaps.length !== 1 ? "s" : ""} to address
                  before certification:
                </p>
                <div>
                  {requirements.gaps.map((gap, i) => (
                    <GapRow key={i} gap={gap} />
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* No data yet */}
      {!cert && !requirements && (
        <EmptyState
          icon={<ShieldCheck className="h-12 w-12 text-neutral-400" />}
          title="No certification data"
          description="Run a Signal Score analysis first. Certification is evaluated automatically once your score is computed."
          action={
            canAnalyze ? (
              <Button onClick={() => evaluate.mutate()} disabled={evaluate.isPending}>
                <RefreshCw className={`mr-2 h-4 w-4 ${evaluate.isPending ? "animate-spin" : ""}`} />
                Evaluate Now
              </Button>
            ) : undefined
          }
        />
      )}
    </div>
  );
}
