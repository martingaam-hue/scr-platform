"use client";

import * as React from "react";
import { cn } from "../lib/utils";

function scoreColor(score: number): string {
  if (score < 40) return "#C62828";
  if (score < 60) return "#F57C00";
  if (score < 80) return "#4EB457";
  return "#2E7D32";
}

export interface ScoreGaugeProps extends React.HTMLAttributes<HTMLDivElement> {
  score: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  /** Optimise for dark/coloured backgrounds: white score text and label */
  inverted?: boolean;
  /** Hide the score number rendered inside the arc (useful when the number is shown externally) */
  showScore?: boolean;
  /** Render as a full circle (360°) instead of a semicircle (180°) */
  fullCircle?: boolean;
}

function ScoreGauge({
  score,
  size = 120,
  strokeWidth = 10,
  label = "Signal Score",
  inverted = false,
  showScore = true,
  fullCircle = false,
  className,
  ...props
}: ScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const color = scoreColor(clamped);

  if (fullCircle) {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (clamped / 100) * circumference;
    const cx = size / 2;
    const cy = size / 2;

    return (
      <div className={cn("flex flex-col items-center", className)} {...props}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="overflow-visible"
        >
          {/* Background circle */}
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke={inverted ? "rgba(255,255,255,0.22)" : "currentColor"}
            strokeWidth={strokeWidth}
            className={inverted ? undefined : "text-neutral-200 dark:text-neutral-700"}
          />
          {/* Score arc — starts from top (-90°) */}
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${cx} ${cy})`}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
          {/* Center text */}
          {showScore && (
            <text
              x={cx}
              y={cy}
              textAnchor="middle"
              dominantBaseline="central"
              className={cn(
                "font-bold",
                inverted ? "fill-white" : "fill-neutral-900 dark:fill-neutral-100"
              )}
              style={{ fontSize: size * 0.28 }}
            >
              {clamped}
            </text>
          )}
        </svg>
        {label && (
          <p className={cn(
            "mt-1 text-xs font-medium",
            inverted ? "text-white/75" : "text-neutral-500 dark:text-neutral-400"
          )}>
            {label}
          </p>
        )}
      </div>
    );
  }

  // ── Semicircle (legacy default) ─────────────────────────────────────────
  const radius = (size - strokeWidth) / 2;

  return (
    <div
      className={cn("flex flex-col items-center", className)}
      {...props}
    >
      <svg
        width={size}
        height={size / 2 + strokeWidth}
        viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}
        className="overflow-visible"
      >
        {/* Background arc */}
        <path
          d={describeArc(size / 2, size / 2, radius, 180, 360)}
          fill="none"
          stroke={inverted ? "rgba(255,255,255,0.22)" : "currentColor"}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className={inverted ? undefined : "text-neutral-200 dark:text-neutral-700"}
        />
        {/* Score arc */}
        <path
          d={describeArc(size / 2, size / 2, radius, 180, 180 + (clamped / 100) * 180)}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          style={{
            transition: "stroke-dashoffset 0.6s ease",
          }}
        />
        {/* Center text */}
        {showScore && (
          <text
            x={size / 2}
            y={size / 2 - 4}
            textAnchor="middle"
            dominantBaseline="middle"
            className={cn(
              "font-bold",
              inverted ? "fill-white" : "fill-neutral-900 dark:fill-neutral-100"
            )}
            style={{ fontSize: size * 0.28 }}
          >
            {clamped}
          </text>
        )}
      </svg>
      {label && (
        <p className={cn(
          "mt-1 text-xs font-medium",
          inverted ? "text-white/75" : "text-neutral-500 dark:text-neutral-400"
        )}>
          {label}
        </p>
      )}
    </div>
  );
}

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number
) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export { ScoreGauge };
