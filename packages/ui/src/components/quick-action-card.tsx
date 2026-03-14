import * as React from "react";
import { cn } from "../lib/utils";

export interface QuickActionCardProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  label: string;
  description?: string;
}

function QuickActionCard({
  icon,
  label,
  description,
  className,
  disabled,
  ...props
}: QuickActionCardProps) {
  return (
    <button
      disabled={disabled}
      className={cn(
        "flex w-full flex-col items-start gap-2 rounded-lg border border-neutral-200 bg-white p-4 text-left transition-all hover:border-primary-300 hover:bg-primary-50/50 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-primary-700",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
      {...props}
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary-50 text-primary-600 dark:bg-primary-950/50 dark:text-primary-400">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{label}</p>
        {description && (
          <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">{description}</p>
        )}
      </div>
    </button>
  );
}

export { QuickActionCard };
