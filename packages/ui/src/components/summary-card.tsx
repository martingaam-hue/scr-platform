import * as React from "react";
import { cn } from "../lib/utils";
import { Card, CardContent } from "./card";

export interface SummaryCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: React.ReactNode;
  /** Tailwind text class for the value */
  valueColor?: string;
  /** Optional sub-value or hint below the main value */
  hint?: React.ReactNode;
}

function SummaryCard({ label, value, valueColor, hint, className, ...props }: SummaryCardProps) {
  return (
    <Card className={cn(className)} {...props}>
      <CardContent className="p-4">
        <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400">{label}</p>
        <p
          className={cn(
            "mt-0.5 text-lg font-semibold tabular-nums text-neutral-900 dark:text-neutral-100",
            valueColor
          )}
        >
          {value}
        </p>
        {hint && <p className="mt-0.5 text-xs text-neutral-400 dark:text-neutral-500">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export { SummaryCard };
