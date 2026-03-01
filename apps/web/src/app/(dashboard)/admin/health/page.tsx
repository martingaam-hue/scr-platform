"use client";

import React from "react";
import {
  Activity,
  CheckCircle2,
  Database,
  RefreshCw,
  Server,
  XCircle,
} from "lucide-react";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from "@scr/ui";
import { useHealthStatus } from "@/lib/launch";

// ── Check row ──────────────────────────────────────────────────────────────────

function CheckRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-center gap-2">
        {ok ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500" />
        )}
        <span className="text-sm font-medium capitalize text-neutral-700 dark:text-neutral-300">
          {label}
        </span>
      </div>
      <Badge variant={ok ? "success" : "error"}>{ok ? "OK" : "FAIL"}</Badge>
    </div>
  );
}

// ── Status card ────────────────────────────────────────────────────────────────

function StatusCard({
  label,
  ok,
  icon: Icon,
}: {
  label: string;
  ok: boolean;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-full ${
            ok ? "bg-emerald-100 dark:bg-emerald-900/30" : "bg-red-100 dark:bg-red-900/30"
          }`}
        >
          <Icon
            className={`h-5 w-5 ${
              ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
            }`}
          />
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
            {label}
          </p>
          <p
            className={`text-sm font-semibold ${
              ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
            }`}
          >
            {ok ? "Operational" : "Degraded"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SystemHealthPage() {
  const { data: health, isLoading, refetch, dataUpdatedAt } = useHealthStatus();

  const lastChecked = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  const overallOk = health?.status === "healthy";

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
            System Health
          </h1>
          <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">
            Real-time status of all platform services.{" "}
            {lastChecked && (
              <span>Last checked at {lastChecked}. Auto-refreshes every 30 s.</span>
            )}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={`mr-2 h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Overall status banner */}
      <div
        className={`rounded-xl border px-5 py-4 ${
          isLoading
            ? "border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900"
            : overallOk
            ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30"
            : "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30"
        }`}
      >
        <div className="flex items-center gap-3">
          <Activity
            className={`h-5 w-5 ${
              isLoading
                ? "text-neutral-400"
                : overallOk
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}
          />
          <div>
            <p className="font-semibold text-neutral-900 dark:text-white">
              {isLoading
                ? "Checking..."
                : health?.status === "healthy"
                ? "All systems operational"
                : health?.status === "degraded"
                ? "Partial outage detected"
                : "System outage"}
            </p>
            {health && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                API version {health.version}
              </p>
            )}
          </div>
          {health && (
            <div className="ml-auto">
              <Badge
                variant={
                  health.status === "healthy"
                    ? "success"
                    : health.status === "degraded"
                    ? "warning"
                    : "error"
                }
              >
                {health.status.toUpperCase()}
              </Badge>
            </div>
          )}
        </div>
      </div>

      {/* Service cards */}
      {health && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatusCard label="Database" ok={health.db_ok} icon={Database} />
          <StatusCard label="Redis Cache" ok={health.redis_ok} icon={Server} />
        </div>
      )}

      {/* Detailed checks */}
      {health && Object.keys(health.checks).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Service Checks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(health.checks).map(([key, ok]) => (
              <CheckRow key={key} label={key} ok={ok} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Loading skeleton */}
      {isLoading && !health && (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800"
            />
          ))}
        </div>
      )}
    </div>
  );
}
