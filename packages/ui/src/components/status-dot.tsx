import * as React from "react";
import { cn } from "../lib/utils";

const dotColorMap = {
  success: "bg-success-500",
  warning: "bg-warning-500",
  error: "bg-error-500",
  info: "bg-primary-500",
  neutral: "bg-neutral-400",
} as const;

export interface StatusDotProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: keyof typeof dotColorMap;
  label?: string;
  pulse?: boolean;
}

function StatusDot({
  status,
  label,
  pulse = false,
  className,
  ...props
}: StatusDotProps) {
  return (
    <span
      className={cn("inline-flex items-center gap-1.5", className)}
      {...props}
    >
      <span className="relative flex h-2.5 w-2.5">
        {pulse && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              dotColorMap[status]
            )}
          />
        )}
        <span
          className={cn(
            "relative inline-flex h-2.5 w-2.5 rounded-full",
            dotColorMap[status]
          )}
        />
      </span>
      {label && (
        <span className="text-sm text-neutral-700 dark:text-neutral-300">
          {label}
        </span>
      )}
    </span>
  );
}

export { StatusDot };
