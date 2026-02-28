"use client";

import { useState } from "react";
import { CheckCircle, ChevronRight, Loader2, ShieldCheck } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  cn,
} from "@scr/ui";
import {
  useRiskProfile,
  useSubmitRiskAssessment,
  RISK_CATEGORY_LABELS,
  RISK_CATEGORY_COLORS,
  EXPERIENCE_LABELS,
  LIQUIDITY_LABELS,
  type AssessmentRequest,
} from "@/lib/risk-profile";

// ── Question step ─────────────────────────────────────────────────────────────

function OptionButton({
  label,
  description,
  selected,
  onClick,
}: {
  label: string;
  description?: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left p-4 rounded-lg border-2 transition-all",
        selected
          ? "border-indigo-500 bg-indigo-50"
          : "border-gray-200 hover:border-gray-300 bg-white"
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "w-5 h-5 rounded-full border-2 mt-0.5 flex-shrink-0 flex items-center justify-center",
            selected ? "border-indigo-500 bg-indigo-500" : "border-gray-300"
          )}
        >
          {selected && <div className="w-2 h-2 bg-white rounded-full" />}
        </div>
        <div>
          <p className={cn("font-medium text-sm", selected ? "text-indigo-700" : "text-gray-900")}>
            {label}
          </p>
          {description && (
            <p className="text-xs text-gray-500 mt-0.5">{description}</p>
          )}
        </div>
      </div>
    </button>
  );
}

// ── Slider ────────────────────────────────────────────────────────────────────

function SliderQuestion({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold text-indigo-700">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full accent-indigo-600"
      />
      <div className="flex justify-between text-xs text-gray-400">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}

// ── Profile Display ───────────────────────────────────────────────────────────

function ProfileDisplay({ profile }: { profile: NonNullable<ReturnType<typeof useRiskProfile>["data"]> }) {
  const category = profile.risk_category ?? "moderate";
  const color = RISK_CATEGORY_COLORS[category] ?? "#6366f1";

  return (
    <div className="space-y-6">
      {/* Category */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-bold"
              style={{ backgroundColor: color }}
            >
              <ShieldCheck className="h-8 w-8" />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Risk Category</p>
              <p className="text-2xl font-bold text-gray-900">
                {RISK_CATEGORY_LABELS[category] ?? category}
              </p>
              <div className="flex gap-3 mt-1 text-sm text-gray-500">
                <span>Sophistication: {((profile.sophistication_score ?? 0) * 100).toFixed(0)}%</span>
                <span>Risk Appetite: {((profile.risk_appetite_score ?? 0) * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recommended allocation */}
      {profile.recommended_allocation && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm font-medium text-gray-700 mb-4">Recommended Allocation</p>
            <div className="space-y-3">
              {Object.entries(profile.recommended_allocation)
                .sort(([, a], [, b]) => b - a)
                .map(([asset, pct]) => (
                  <div key={asset}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="capitalize text-gray-700">
                        {asset.replace(/_/g, " ")}
                      </span>
                      <span className="font-medium tabular-nums">{pct}%</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${pct}%`, backgroundColor: color }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Profile summary */}
      <Card>
        <CardContent className="p-4">
          <p className="text-sm font-medium text-gray-700 mb-3">Profile Summary</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              { label: "Experience", value: EXPERIENCE_LABELS[profile.experience_level ?? ""] ?? profile.experience_level },
              { label: "Investment Horizon", value: profile.investment_horizon_years ? `${profile.investment_horizon_years} years` : "—" },
              { label: "Loss Tolerance", value: profile.loss_tolerance_percentage ? `${profile.loss_tolerance_percentage}%` : "—" },
              { label: "Liquidity Needs", value: LIQUIDITY_LABELS[profile.liquidity_needs ?? ""] ?? profile.liquidity_needs },
              { label: "Max Concentration", value: profile.concentration_max_percentage ? `${profile.concentration_max_percentage}%` : "—" },
              { label: "Max Drawdown", value: profile.max_drawdown_tolerance ? `${profile.max_drawdown_tolerance}%` : "—" },
            ].map(({ label, value }) => (
              <div key={label} className="border rounded-lg p-3">
                <p className="text-gray-500 text-xs">{label}</p>
                <p className="font-medium text-gray-900 mt-0.5">{value ?? "—"}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Questionnaire ─────────────────────────────────────────────────────────────

const STEPS = ["Experience", "Horizon", "Risk Tolerance", "Liquidity", "Limits"];

export default function RiskProfilePage() {
  const { data: profile, isLoading } = useRiskProfile();
  const { mutate: submit, isPending } = useSubmitRiskAssessment();
  const [showQuestionnaire, setShowQuestionnaire] = useState(false);
  const [step, setStep] = useState(0);

  const [form, setForm] = useState<AssessmentRequest>({
    experience_level: "moderate",
    investment_horizon_years: 7,
    loss_tolerance_percentage: 20,
    liquidity_needs: "moderate",
    concentration_max_percentage: 25,
    max_drawdown_tolerance: 20,
  });

  const handleSubmit = () => {
    submit(form, { onSuccess: () => setShowQuestionnaire(false) });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Risk Profile</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Investor risk assessment and recommended allocation
          </p>
        </div>
        {profile?.has_profile && (
          <Button variant="outline" onClick={() => setShowQuestionnaire(true)}>
            Retake Assessment
          </Button>
        )}
      </div>

      {/* Profile exists */}
      {profile?.has_profile && !showQuestionnaire && (
        <ProfileDisplay profile={profile} />
      )}

      {/* Questionnaire */}
      {(!profile?.has_profile || showQuestionnaire) && (
        <Card>
          <CardContent className="p-6 space-y-6">
            {/* Progress */}
            <div className="flex items-center gap-1">
              {STEPS.map((s, i) => (
                <div key={s} className="flex items-center gap-1 flex-1">
                  <div
                    className={cn(
                      "h-2 flex-1 rounded-full transition-all",
                      i < step ? "bg-indigo-500" : i === step ? "bg-indigo-300" : "bg-gray-200"
                    )}
                  />
                  {i === step && (
                    <span className="text-xs text-indigo-600 font-medium whitespace-nowrap">{s}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Step 0: Experience */}
            {step === 0 && (
              <div className="space-y-3">
                <p className="font-medium text-gray-900">What is your investment experience level?</p>
                {(["none", "limited", "moderate", "extensive"] as const).map((level) => (
                  <OptionButton
                    key={level}
                    label={EXPERIENCE_LABELS[level]}
                    selected={form.experience_level === level}
                    onClick={() => setForm((f) => ({ ...f, experience_level: level }))}
                  />
                ))}
              </div>
            )}

            {/* Step 1: Horizon */}
            {step === 1 && (
              <div className="space-y-6">
                <p className="font-medium text-gray-900">What is your investment time horizon?</p>
                <SliderQuestion
                  label="Years"
                  value={form.investment_horizon_years}
                  min={1}
                  max={20}
                  step={1}
                  format={(v) => `${v} year${v !== 1 ? "s" : ""}`}
                  onChange={(v) => setForm((f) => ({ ...f, investment_horizon_years: v }))}
                />
              </div>
            )}

            {/* Step 2: Risk Tolerance */}
            {step === 2 && (
              <div className="space-y-6">
                <p className="font-medium text-gray-900">How much portfolio loss could you tolerate in a single year?</p>
                <SliderQuestion
                  label="Maximum annual loss"
                  value={form.loss_tolerance_percentage}
                  min={5}
                  max={60}
                  step={5}
                  format={(v) => `${v}%`}
                  onChange={(v) => setForm((f) => ({ ...f, loss_tolerance_percentage: v }))}
                />
                <p className="font-medium text-gray-900 mt-4">Maximum drawdown tolerance?</p>
                <SliderQuestion
                  label="Peak-to-trough drawdown"
                  value={form.max_drawdown_tolerance}
                  min={5}
                  max={60}
                  step={5}
                  format={(v) => `${v}%`}
                  onChange={(v) => setForm((f) => ({ ...f, max_drawdown_tolerance: v }))}
                />
              </div>
            )}

            {/* Step 3: Liquidity */}
            {step === 3 && (
              <div className="space-y-3">
                <p className="font-medium text-gray-900">What are your liquidity needs?</p>
                {(["high", "moderate", "low"] as const).map((level) => (
                  <OptionButton
                    key={level}
                    label={level.charAt(0).toUpperCase() + level.slice(1)}
                    description={LIQUIDITY_LABELS[level]}
                    selected={form.liquidity_needs === level}
                    onClick={() => setForm((f) => ({ ...f, liquidity_needs: level }))}
                  />
                ))}
              </div>
            )}

            {/* Step 4: Concentration */}
            {step === 4 && (
              <div className="space-y-6">
                <p className="font-medium text-gray-900">Maximum allocation to a single investment?</p>
                <SliderQuestion
                  label="Max concentration per investment"
                  value={form.concentration_max_percentage}
                  min={5}
                  max={50}
                  step={5}
                  format={(v) => `${v}%`}
                  onChange={(v) => setForm((f) => ({ ...f, concentration_max_percentage: v }))}
                />
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between pt-2">
              <Button
                variant="outline"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
              >
                Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button onClick={() => setStep((s) => s + 1)}>
                  Next <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              ) : (
                <Button onClick={handleSubmit} disabled={isPending}>
                  {isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  Submit Assessment
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
