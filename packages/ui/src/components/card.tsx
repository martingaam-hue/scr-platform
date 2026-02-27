import * as React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "../lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

function Card({ hover = false, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900",
        hover &&
          "transition-shadow hover:shadow-md hover:border-neutral-300 dark:hover:border-neutral-700",
        className
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center justify-between border-b border-neutral-100 px-6 py-4 dark:border-neutral-800",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-sm font-semibold text-neutral-900 dark:text-neutral-100",
        className
      )}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 py-4", className)} {...props} />;
}

function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center border-t border-neutral-100 px-6 py-3 dark:border-neutral-800",
        className
      )}
      {...props}
    />
  );
}

// ── Metric Card variant ─────────────────────────────────────────────────

export type TrendDirection = "up" | "down" | "neutral";

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string;
  trend?: { direction: TrendDirection; value: string };
  sparkline?: React.ReactNode;
}

function MetricCard({
  label,
  value,
  trend,
  sparkline,
  className,
  ...props
}: MetricCardProps) {
  return (
    <Card className={cn("overflow-hidden", className)} {...props}>
      <CardContent className="py-5">
        <p className="text-xs font-medium uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
          {label}
        </p>
        <div className="mt-2 flex items-end justify-between">
          <p className="text-2xl font-bold tabular-nums text-neutral-900 dark:text-neutral-100">
            {value}
          </p>
          {sparkline && <div className="h-10 w-20">{sparkline}</div>}
        </div>
        {trend && (
          <div className="mt-2 flex items-center gap-1">
            {trend.direction === "up" && (
              <TrendingUp className="h-3.5 w-3.5 text-success-500" />
            )}
            {trend.direction === "down" && (
              <TrendingDown className="h-3.5 w-3.5 text-error-500" />
            )}
            {trend.direction === "neutral" && (
              <Minus className="h-3.5 w-3.5 text-neutral-400" />
            )}
            <span
              className={cn(
                "text-xs font-medium",
                trend.direction === "up" && "text-success-600",
                trend.direction === "down" && "text-error-600",
                trend.direction === "neutral" && "text-neutral-500"
              )}
            >
              {trend.value}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export { Card, CardHeader, CardTitle, CardContent, CardFooter, MetricCard };
