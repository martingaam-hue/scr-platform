import * as React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "../lib/utils";
import { type TrendDirection } from "./card";

export interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  value: React.ReactNode;
  label: string;
  trend?: string;
  trendDirection?: TrendDirection;
  /** Tailwind text class for the value */
  valueColor?: string;
  size?: "sm" | "md" | "lg";
}

function StatCard({
  value,
  label,
  trend,
  trendDirection = "neutral",
  valueColor,
  size = "md",
  className,
  ...props
}: StatCardProps) {
  const valueSizes = { sm: "text-xl", md: "text-2xl", lg: "text-3xl" };
  return (
    <div className={cn("flex flex-col", className)} {...props}>
      <p
        className={cn(
          "font-bold tabular-nums text-neutral-900 dark:text-neutral-100",
          valueSizes[size],
          valueColor
        )}
      >
        {value}
      </p>
      <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{label}</p>
      {trend && (
        <div className="mt-1 flex items-center gap-1">
          {trendDirection === "up" && (
            <TrendingUp className="h-3 w-3 text-success-500" />
          )}
          {trendDirection === "down" && (
            <TrendingDown className="h-3 w-3 text-error-500" />
          )}
          {trendDirection === "neutral" && (
            <Minus className="h-3 w-3 text-neutral-400" />
          )}
          <span
            className={cn(
              "text-xs font-medium",
              trendDirection === "up" && "text-success-600",
              trendDirection === "down" && "text-error-600",
              trendDirection === "neutral" && "text-neutral-500"
            )}
          >
            {trend}
          </span>
        </div>
      )}
    </div>
  );
}

export { StatCard };
