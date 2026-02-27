import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        success:
          "bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-400",
        warning:
          "bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400",
        error:
          "bg-error-50 text-error-700 dark:bg-error-900/30 dark:text-error-400",
        info: "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400",
        neutral:
          "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
        gold: "bg-secondary-50 text-secondary-700 dark:bg-secondary-900/30 dark:text-secondary-400",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

function scoreToColor(score: number): string {
  if (score < 40) return "text-error-500";
  if (score < 60) return "text-warning-500";
  if (score < 80) return "text-success-400";
  return "text-success-600";
}

function scoreToBg(score: number): string {
  if (score < 40) return "bg-error-50 dark:bg-error-900/30";
  if (score < 60) return "bg-warning-50 dark:bg-warning-900/30";
  if (score < 80) return "bg-success-50/60 dark:bg-success-900/20";
  return "bg-success-50 dark:bg-success-900/30";
}

interface ScoreBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  score: number;
}

function ScoreBadge({ score, className, ...props }: ScoreBadgeProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold tabular-nums",
        scoreToBg(clamped),
        scoreToColor(clamped),
        className
      )}
      {...props}
    >
      {clamped}
    </span>
  );
}

export { Badge, badgeVariants, ScoreBadge };
