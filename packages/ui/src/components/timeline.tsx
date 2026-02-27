import * as React from "react";
import { cn } from "../lib/utils";

export interface TimelineItem {
  id: string;
  icon?: React.ReactNode;
  title: string;
  description?: string;
  timestamp: string;
  meta?: React.ReactNode;
}

export interface TimelineProps extends React.HTMLAttributes<HTMLDivElement> {
  items: TimelineItem[];
}

function Timeline({ items, className, ...props }: TimelineProps) {
  return (
    <div className={cn("relative", className)} {...props}>
      {items.map((item, i) => (
        <div key={item.id} className="relative flex gap-4 pb-8 last:pb-0">
          {/* Vertical line */}
          {i < items.length - 1 && (
            <div className="absolute left-[15px] top-8 h-[calc(100%-16px)] w-px bg-neutral-200 dark:bg-neutral-700" />
          )}
          {/* Icon */}
          <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-neutral-200 bg-white text-neutral-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-400">
            {item.icon || (
              <div className="h-2 w-2 rounded-full bg-neutral-400 dark:bg-neutral-500" />
            )}
          </div>
          {/* Content */}
          <div className="flex-1 pt-0.5">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                {item.title}
              </p>
              <time className="shrink-0 text-xs text-neutral-400 dark:text-neutral-500">
                {item.timestamp}
              </time>
            </div>
            {item.description && (
              <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">
                {item.description}
              </p>
            )}
            {item.meta && <div className="mt-2">{item.meta}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export { Timeline };
