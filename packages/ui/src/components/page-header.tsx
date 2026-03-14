import * as React from "react";
import { cn } from "../lib/utils";

export interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  /** Tailwind bg class for icon background, e.g. "bg-primary-50" */
  iconBg?: string;
  action?: React.ReactNode;
}

function PageHeader({ icon, title, description, iconBg = "bg-primary-50", action, className, ...props }: PageHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between gap-3", className)} {...props}>
      <div className="flex items-center gap-3">
        {icon && (
          <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", iconBg)}>
            {icon}
          </div>
        )}
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{title}</h1>
          {description && (
            <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">{description}</p>
          )}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export { PageHeader };
