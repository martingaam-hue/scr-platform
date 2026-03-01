"use client";

import React, { useState } from "react";
import { Flag, Cpu, ToggleLeft, ToggleRight } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import { useFeatureFlags, useSetFlagOverride, useTokenUsage, type FeatureFlag } from "@/lib/launch";

// ── Token Usage Card ───────────────────────────────────────────────────────────

const TIER_LABELS: Record<string, string> = {
  foundation: "Foundation",
  professional: "Professional",
  enterprise: "Enterprise",
};

const TIER_BADGE_VARIANTS: Record<string, "neutral" | "info" | "gold"> = {
  foundation: "neutral",
  professional: "info",
  enterprise: "gold",
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

function getResetDate(): string {
  const now = new Date();
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return nextMonth.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function TokenUsageCard() {
  const { data, isLoading } = useTokenUsage();

  const tier = data?.tier ?? "foundation";
  const tierLabel = TIER_LABELS[tier] ?? tier;
  const tierVariant = TIER_BADGE_VARIANTS[tier] ?? "neutral";
  const usedPct = data?.usage_pct ?? 0;
  const isWarning = usedPct >= 80;
  const isCritical = usedPct >= 95;

  const barColor = isCritical
    ? "bg-red-500"
    : isWarning
      ? "bg-amber-500"
      : "bg-emerald-500";

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-neutral-500" />
          <CardTitle className="text-base">AI Token Usage This Month</CardTitle>
        </div>
        {data && (
          <Badge variant={tierVariant} className="text-xs">
            {tierLabel}
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && (
          <div className="h-16 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800" />
        )}

        {!isLoading && data && (
          <>
            {/* Progress bar */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-neutral-900 dark:text-white">
                  {formatTokens(data.tokens_used)} / {formatTokens(data.tokens_limit)} tokens
                </span>
                <span
                  className={
                    isCritical
                      ? "font-semibold text-red-600 dark:text-red-400"
                      : isWarning
                        ? "font-semibold text-amber-600 dark:text-amber-400"
                        : "text-neutral-500 dark:text-neutral-400"
                  }
                >
                  {data.usage_pct}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                  style={{ width: `${Math.min(usedPct, 100)}%` }}
                />
              </div>
            </div>

            {/* Details row */}
            <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400">
              <span>
                {formatTokens(data.tokens_remaining)} remaining
              </span>
              <span>Resets on {getResetDate()}</span>
            </div>

            {/* Warning banners */}
            {isCritical && (
              <div className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
                Token budget nearly exhausted. AI features will be blocked when the limit is reached.
              </div>
            )}
            {!isCritical && isWarning && (
              <div className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                Approaching monthly token limit. Consider upgrading your plan.
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ── Override badge ─────────────────────────────────────────────────────────────

function OverrideBadge({ override }: { override: boolean | null }) {
  if (override === null || override === undefined) {
    return (
      <Badge variant="neutral" className="text-xs">
        Global
      </Badge>
    );
  }
  return (
    <Badge variant={override ? "success" : "error"} className="text-xs">
      {override ? "Enabled" : "Disabled"} (org override)
    </Badge>
  );
}

// ── Flag row ───────────────────────────────────────────────────────────────────

function FlagRow({ flag }: { flag: FeatureFlag }) {
  const setOverride = useSetFlagOverride();

  const effectivelyEnabled =
    flag.org_override !== null && flag.org_override !== undefined
      ? flag.org_override
      : flag.enabled_globally;

  const handleToggle = () => {
    setOverride.mutate({
      flagName: flag.name,
      enabled: !effectivelyEnabled,
    });
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-neutral-900 dark:text-white">
            {flag.name}
          </span>
          <OverrideBadge override={flag.org_override} />
          {flag.rollout_pct < 100 && (
            <Badge variant="info" className="text-xs">
              {flag.rollout_pct}% rollout
            </Badge>
          )}
        </div>
        {flag.description && (
          <p className="mt-0.5 text-xs text-neutral-500 dark:text-neutral-400">
            {flag.description}
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          Global: {flag.enabled_globally ? "on" : "off"}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleToggle}
          disabled={setOverride.isPending}
          className="p-1"
          title={effectivelyEnabled ? "Disable for this org" : "Enable for this org"}
        >
          {effectivelyEnabled ? (
            <ToggleRight className="h-6 w-6 text-emerald-500" />
          ) : (
            <ToggleLeft className="h-6 w-6 text-neutral-400" />
          )}
        </Button>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function FeatureFlagsPage() {
  const { data: flags, isLoading } = useFeatureFlags();
  const [search, setSearch] = useState("");

  const filtered = (flags ?? []).filter(
    (f) =>
      f.name.includes(search.toLowerCase()) ||
      (f.description ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
          Feature Flags
        </h1>
        <p className="mt-0.5 text-sm text-neutral-500 dark:text-neutral-400">
          Manage global feature flags and per-org overrides.
        </p>
      </div>

      {/* AI Token Budget */}
      <TokenUsageCard />

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle>Flags ({filtered.length})</CardTitle>
          <input
            type="text"
            placeholder="Search flags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 w-56 rounded-md border border-neutral-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
          />
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading && (
            <div className="space-y-2">
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-14 animate-pulse rounded-lg bg-neutral-100 dark:bg-neutral-800"
                />
              ))}
            </div>
          )}

          {!isLoading && filtered.length === 0 && (
            <EmptyState
              icon={<Flag className="h-8 w-8" />}
              title="No feature flags found"
              description={
                search
                  ? "Try a different search term."
                  : "No feature flags have been configured yet."
              }
            />
          )}

          {!isLoading &&
            filtered.map((flag) => <FlagRow key={flag.name} flag={flag} />)}
        </CardContent>
      </Card>
    </div>
  );
}
