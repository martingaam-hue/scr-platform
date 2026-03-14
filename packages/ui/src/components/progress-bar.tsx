import * as React from "react";
import { cn } from "../lib/utils";

export interface ProgressBarProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  /** Tailwind bg class for the fill, e.g. "bg-success-500" */
  fillColor?: string;
  size?: "sm" | "md" | "lg";
  /** Show percentage label */
  showLabel?: boolean;
}

function ProgressBar({
  value,
  max = 100,
  fillColor,
  size = "md",
  showLabel = false,
  className,
  ...props
}: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, max > 0 ? (value / max) * 100 : 0));
  const heights = { sm: "h-1.5", md: "h-2", lg: "h-3" };
  return (
    <div className={cn("w-full", className)} {...props}>
      <div
        className={cn(
          "w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800",
          heights[size]
        )}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            fillColor ?? "bg-primary-600"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <p className="mt-1 text-right text-xs text-neutral-500">{Math.round(pct)}%</p>
      )}
    </div>
  );
}

export { ProgressBar };
