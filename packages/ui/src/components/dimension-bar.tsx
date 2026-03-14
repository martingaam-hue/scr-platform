import * as React from "react";
import { cn } from "../lib/utils";
import { ProgressBar } from "./progress-bar";

export interface DimensionBarProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  name: string;
  score: number;
  maxScore?: number;
  weight?: number;
  /** Tailwind text class for score label */
  scoreColor?: string;
  /** Tailwind bg class for progress fill */
  fillColor?: string;
}

function DimensionBar({
  icon,
  name,
  score,
  maxScore = 100,
  weight,
  scoreColor,
  fillColor,
  className,
  ...props
}: DimensionBarProps) {
  return (
    <div className={cn("space-y-1.5", className)} {...props}>
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 font-medium text-neutral-700 dark:text-neutral-300">
          {icon}
          {name}
          {weight !== undefined && (
            <span className="text-xs font-normal text-neutral-400">({weight}%)</span>
          )}
        </span>
        <span
          className={cn(
            "font-semibold tabular-nums",
            scoreColor ?? "text-primary-700 dark:text-primary-400"
          )}
        >
          {Math.round(score)}
        </span>
      </div>
      <ProgressBar value={score} max={maxScore} fillColor={fillColor} />
    </div>
  );
}

export { DimensionBar };
