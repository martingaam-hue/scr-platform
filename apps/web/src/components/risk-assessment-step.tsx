"use client";

import React, { useState } from "react";
import { Button, Card, CardContent } from "@scr/ui";
import { api } from "@/lib/api";

interface RiskResult {
  risk_category: string;
  sophistication_score: number;
  risk_appetite_score: number;
  recommended_allocation: Record<string, number>;
}

const QUESTIONS = [
  {
    id: "experience_level",
    question: "How much experience do you have with alternative investments?",
    options: [
      { value: "none", label: "None — I'm new to alternatives" },
      { value: "limited", label: "Limited — 1–3 years" },
      { value: "moderate", label: "Moderate — 3–7 years" },
      { value: "extensive", label: "Extensive — 7+ years" },
    ],
  },
  {
    id: "investment_horizon_years",
    question: "What is your typical investment horizon?",
    options: [
      { value: 1, label: "1–3 years" },
      { value: 3, label: "3–5 years" },
      { value: 5, label: "5–10 years" },
      { value: 10, label: "10+ years" },
    ],
  },
  {
    id: "loss_tolerance_percentage",
    question: "Maximum loss you could tolerate on a single investment?",
    options: [
      { value: 5, label: "5% — Capital preservation" },
      { value: 10, label: "10% — Some loss acceptable" },
      { value: 20, label: "20% — Moderate losses" },
      { value: 30, label: "30% — Higher risk / higher returns" },
      { value: 50, label: "50% — High volatility comfortable" },
    ],
  },
  {
    id: "liquidity_needs",
    question: "How important is liquidity to you?",
    options: [
      { value: "high", label: "High — may need capital within 1–2 years" },
      { value: "moderate", label: "Moderate — 3–5 year lock-up is fine" },
      { value: "low", label: "Low — comfortable with 7+ year commitments" },
    ],
  },
  {
    id: "concentration_max_percentage",
    question: "Maximum allocation to a single investment?",
    options: [
      { value: 5, label: "5% of portfolio" },
      { value: 10, label: "10% of portfolio" },
      { value: 20, label: "20% of portfolio" },
      { value: 30, label: "30% of portfolio" },
    ],
  },
  {
    id: "max_drawdown_tolerance",
    question: "Maximum portfolio drawdown you could tolerate?",
    options: [
      { value: 5, label: "5% — Very conservative" },
      { value: 10, label: "10% — Moderate" },
      { value: 20, label: "20% — Balanced" },
      { value: 30, label: "30% — Growth-oriented" },
      { value: 50, label: "50% — Aggressive" },
    ],
  },
] as const;

const CATEGORY_COLORS: Record<string, string> = {
  conservative: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  moderate: "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-300",
  balanced: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  growth: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  aggressive: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

export function RiskAssessmentStep({
  onComplete,
}: {
  onComplete: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, string | number>>({});
  const [result, setResult] = useState<RiskResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const allAnswered = QUESTIONS.every((q) => answers[q.id] !== undefined);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const { data } = await api.post<RiskResult>("/risk-profile/assess", answers);
      setResult(data);
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    const colorClass = CATEGORY_COLORS[result.risk_category] ?? CATEGORY_COLORS.balanced;
    return (
      <div className="space-y-6">
        <div className="text-center">
          <span className={`inline-block rounded-full px-4 py-1.5 text-lg font-bold capitalize ${colorClass}`}>
            {result.risk_category} Investor
          </span>
          <p className="mt-2 text-sm text-neutral-500">
            Risk appetite score: {result.risk_appetite_score.toFixed(0)}/100
          </p>
        </div>

        <Card>
          <CardContent className="p-4">
            <p className="mb-3 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
              Recommended Allocation
            </p>
            <div className="space-y-2">
              {Object.entries(result.recommended_allocation).map(([key, pct]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="w-32 text-xs capitalize text-neutral-600 dark:text-neutral-400">
                    {key.replace(/_/g, " ")}
                  </span>
                  <div className="flex-1 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800 h-2">
                    <div
                      className="h-full rounded-full bg-primary-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs font-medium text-neutral-700 dark:text-neutral-300">
                    {pct}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Button className="w-full" onClick={onComplete}>
          Continue
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">
          Risk Assessment
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Help us understand your investment profile to personalise your experience.
        </p>
      </div>

      {QUESTIONS.map((q) => (
        <div key={q.id}>
          <p className="mb-2 text-sm font-medium text-neutral-800 dark:text-neutral-200">
            {q.question}
          </p>
          <div className="space-y-2">
            {q.options.map((opt) => (
              <label
                key={String(opt.value)}
                className={[
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition-colors",
                  answers[q.id] === opt.value
                    ? "border-primary-500 bg-primary-50 dark:border-primary-700 dark:bg-primary-950/30"
                    : "border-neutral-200 hover:border-neutral-300 dark:border-neutral-700",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name={q.id}
                  value={String(opt.value)}
                  checked={answers[q.id] === opt.value}
                  onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt.value }))}
                  className="shrink-0"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>
      ))}

      <Button
        className="w-full"
        disabled={!allAnswered || submitting}
        onClick={handleSubmit}
      >
        {submitting ? "Calculating..." : "See my risk profile"}
      </Button>
    </div>
  );
}
