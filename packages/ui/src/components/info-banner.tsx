import * as React from "react";
import { Info } from "lucide-react";
import { cn } from "../lib/utils";

export interface InfoBannerProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Override the default Info icon */
  icon?: React.ReactNode;
}

function InfoBanner({ icon, children, className, ...props }: InfoBannerProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-sm text-primary-800 dark:border-primary-900/50 dark:bg-primary-950/30 dark:text-primary-300",
        className
      )}
      {...props}
    >
      <span className="mt-0.5 shrink-0 text-primary-500">
        {icon ?? <Info className="h-4 w-4" />}
      </span>
      <span>{children}</span>
    </div>
  );
}

export { InfoBanner };
