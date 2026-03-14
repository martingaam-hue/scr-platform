import * as React from "react";
import { cn } from "../lib/utils";

export interface SectionHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
}

function SectionHeader({ title, subtitle, className, ...props }: SectionHeaderProps) {
  return (
    <div className={cn("mb-4", className)} {...props}>
      <div className="flex items-center gap-2">
        <div className="h-4 w-1 rounded-full bg-primary-500" />
        <h2 className="text-xs font-semibold uppercase tracking-widest text-neutral-500 dark:text-neutral-400">
          {title}
        </h2>
      </div>
      {subtitle && (
        <p className="mt-1 pl-3 text-sm text-neutral-600 dark:text-neutral-400">{subtitle}</p>
      )}
    </div>
  );
}

export { SectionHeader };
