import * as React from "react";
import { cn } from "../lib/utils";

export interface LoadingSpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "xs" | "sm" | "md" | "lg";
  color?: string;
}

function LoadingSpinner({ size = "md", color, className, ...props }: LoadingSpinnerProps) {
  const sizes = {
    xs: "h-3 w-3 border-2",
    sm: "h-4 w-4 border-2",
    md: "h-8 w-8 border-4",
    lg: "h-12 w-12 border-4",
  };
  return (
    <div
      className={cn(
        "animate-spin rounded-full border-t-transparent",
        sizes[size],
        color ?? "border-primary-600",
        className
      )}
      {...props}
    />
  );
}

export { LoadingSpinner };
