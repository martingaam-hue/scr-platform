import * as React from "react";
import { Badge, type BadgeProps } from "./badge";

const STATUS_VARIANTS: Record<string, BadgeProps["variant"]> = {
  // success states
  active: "success",
  completed: "success",
  approved: "success",
  on_track: "success",
  ready: "success",
  ready_to_build: "success",
  verified: "success",
  healthy: "success",
  passed: "success",
  // warning states
  pending: "warning",
  processing: "warning",
  at_risk: "warning",
  review: "warning",
  degraded: "warning",
  in_progress: "warning",
  // error states
  failed: "error",
  rejected: "error",
  blocked: "error",
  error: "error",
  overdue: "error",
  // neutral states
  draft: "neutral",
  inactive: "neutral",
  archived: "neutral",
  unknown: "neutral",
  not_started: "neutral",
  // info states
  info: "info",
  planned: "info",
  scheduled: "info",
};

const STATUS_LABELS: Record<string, string> = {
  on_track: "On Track",
  at_risk: "At Risk",
  ready_to_build: "Ready to Build",
  in_progress: "In Progress",
  not_started: "Not Started",
};

export interface StatusBadgeProps {
  status: string;
  className?: string;
}

function StatusBadge({ status, className }: StatusBadgeProps) {
  const variant = STATUS_VARIANTS[status.toLowerCase()] ?? "neutral";
  const label =
    STATUS_LABELS[status.toLowerCase()] ??
    status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}

export { StatusBadge };
