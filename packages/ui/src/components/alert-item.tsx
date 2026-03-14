import * as React from "react";
import { cn } from "../lib/utils";
import { Badge, type BadgeProps } from "./badge";

export type AlertSeverity = "critical" | "high" | "medium" | "low" | "info";

const SEVERITY_VARIANT: Record<AlertSeverity, BadgeProps["variant"]> = {
  critical: "error",
  high: "error",
  medium: "warning",
  low: "info",
  info: "info",
};

export interface AlertItemProps extends React.HTMLAttributes<HTMLDivElement> {
  severity: AlertSeverity;
  title: string;
  description?: string;
  entities?: string[];
  action?: React.ReactNode;
}

function AlertItem({
  severity,
  title,
  description,
  entities,
  action,
  className,
  ...props
}: AlertItemProps) {
  const label = severity.charAt(0).toUpperCase() + severity.slice(1);
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-900",
        className
      )}
      {...props}
    >
      <Badge variant={SEVERITY_VARIANT[severity]} className="mt-0.5 shrink-0">
        {label}
      </Badge>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{title}</p>
        {description && (
          <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{description}</p>
        )}
        {entities && entities.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {entities.map((e) => (
              <Badge key={e} variant="neutral" className="text-xs">
                {e}
              </Badge>
            ))}
          </div>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export { AlertItem };
