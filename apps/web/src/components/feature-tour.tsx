"use client";

import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { Button, cn } from "@scr/ui";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────

export interface TourStep {
  target: string; // data-tour attribute value
  title: string;
  description: string;
  placement?: "top" | "bottom" | "left" | "right";
}

interface TourProps {
  steps: TourStep[];
  onComplete: () => void;
}

// ── Component ──────────────────────────────────────────────────────────

export function FeatureTour({ steps, onComplete }: TourProps) {
  const [current, setCurrent] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Find the target element and update rect
  const updateRect = useCallback(() => {
    if (current >= steps.length) return;
    const el = document.querySelector(
      `[data-tour="${steps[current].target}"]`
    );
    if (el) {
      setRect(el.getBoundingClientRect());
    } else {
      setRect(null);
    }
  }, [current, steps]);

  useEffect(() => {
    updateRect();
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [updateRect]);

  const finish = useCallback(async () => {
    try {
      await api.put("/auth/me/preferences", {
        preferences: { tour_completed: true },
      });
    } catch {
      // non-critical, continue
    }
    onComplete();
  }, [onComplete]);

  const next = () => {
    if (current < steps.length - 1) {
      setCurrent((c) => c + 1);
    } else {
      finish();
    }
  };

  if (!mounted || current >= steps.length) return null;

  const step = steps[current];
  const placement = step.placement ?? "right";

  // Calculate tooltip position
  const tooltipStyle: React.CSSProperties = {};
  if (rect) {
    const GAP = 12;
    switch (placement) {
      case "right":
        tooltipStyle.top = rect.top + rect.height / 2;
        tooltipStyle.left = rect.right + GAP;
        tooltipStyle.transform = "translateY(-50%)";
        break;
      case "left":
        tooltipStyle.top = rect.top + rect.height / 2;
        tooltipStyle.right = window.innerWidth - rect.left + GAP;
        tooltipStyle.transform = "translateY(-50%)";
        break;
      case "bottom":
        tooltipStyle.top = rect.bottom + GAP;
        tooltipStyle.left = rect.left + rect.width / 2;
        tooltipStyle.transform = "translateX(-50%)";
        break;
      case "top":
        tooltipStyle.bottom = window.innerHeight - rect.top + GAP;
        tooltipStyle.left = rect.left + rect.width / 2;
        tooltipStyle.transform = "translateX(-50%)";
        break;
    }
  }

  return createPortal(
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-[60] bg-black/30" />

      {/* Spotlight cutout */}
      {rect && (
        <div
          className="fixed z-[61] rounded-lg ring-4 ring-primary-400/50"
          style={{
            top: rect.top - 4,
            left: rect.left - 4,
            width: rect.width + 8,
            height: rect.height + 8,
            boxShadow: "0 0 0 9999px rgba(0,0,0,0.3)",
          }}
        />
      )}

      {/* Tooltip */}
      <div
        className="fixed z-[62] w-72 rounded-xl bg-white p-4 shadow-xl"
        style={tooltipStyle}
      >
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-medium text-primary-600">
            {current + 1} of {steps.length}
          </span>
          <button
            onClick={finish}
            className="rounded p-0.5 text-neutral-400 hover:text-neutral-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3 className="text-sm font-semibold text-neutral-900">
          {step.title}
        </h3>
        <p className="mt-1 text-xs text-neutral-500">{step.description}</p>
        <div className="mt-3 flex items-center justify-between">
          <button
            onClick={finish}
            className="text-xs text-neutral-400 hover:text-neutral-600"
          >
            Skip tour
          </button>
          <Button size="sm" onClick={next}>
            {current < steps.length - 1 ? "Next" : "Done"}
          </Button>
        </div>
      </div>
    </>,
    document.body
  );
}

// ── Tour step presets ──────────────────────────────────────────────────

export const INVESTOR_TOUR_STEPS: TourStep[] = [
  {
    target: "nav-portfolio",
    title: "Your portfolio overview",
    description:
      "Track your investments, view performance metrics, and manage holdings all in one place.",
    placement: "right",
  },
  {
    target: "nav-deals",
    title: "Browse investment opportunities",
    description:
      "Discover curated renewable energy projects that match your investment mandate.",
    placement: "right",
  },
  {
    target: "nav-data-room",
    title: "Secure document sharing",
    description:
      "Access due diligence documents, financial models, and legal agreements securely.",
    placement: "right",
  },
  {
    target: "nav-ralph",
    title: "AI-powered analysis",
    description:
      "Ask Ralph AI to analyze documents, score projects, and generate investment reports.",
    placement: "right",
  },
];

export const ALLY_TOUR_STEPS: TourStep[] = [
  {
    target: "nav-projects",
    title: "Manage your projects",
    description:
      "Track milestones, budgets, and signal scores for all your renewable energy projects.",
    placement: "right",
  },
  {
    target: "nav-data-room",
    title: "Upload project documents",
    description:
      "Share technical studies, financial models, and permits with potential investors.",
    placement: "right",
  },
  {
    target: "nav-funding",
    title: "Track funding progress",
    description:
      "Monitor fundraising status, investor interest, and capital commitments.",
    placement: "right",
  },
  {
    target: "nav-ralph",
    title: "AI-powered insights",
    description:
      "Use Ralph AI to improve your project scoring, analyze gaps, and prepare for investors.",
    placement: "right",
  },
];
