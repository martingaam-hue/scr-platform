"use client";

import React from "react";
import {
  Brain,
  TrendingUp,
  Calendar,
  FileText,
  Scale,
  DollarSign,
  RefreshCw,
  Loader2,
} from "lucide-react";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  MetricCard,
  Badge,
  Timeline,
  Button,
  cn,
} from "@scr/ui";
import type { TimelineItem } from "@scr/ui";
import type { ExtractionResponse, ExtractionType } from "@/lib/dataroom";

// ── Types ──────────────────────────────────────────────────────────────────

interface ExtractionPanelProps {
  extractions: ExtractionResponse[];
  loading?: boolean;
  onReExtract?: (types?: ExtractionType[]) => void;
  reExtracting?: boolean;
}

// ── Confidence indicator ───────────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const variant =
    pct >= 80 ? "success" : pct >= 50 ? "warning" : "error";
  return <Badge variant={variant}>{pct}% confidence</Badge>;
}

// ── KPI display ────────────────────────────────────────────────────────────

function KPISection({ extraction }: { extraction: ExtractionResponse }) {
  const kpis = Array.isArray(extraction.result.kpis)
    ? (extraction.result.kpis as Array<{
        name?: string;
        value?: string | number;
        unit?: string;
      }>)
    : [];

  if (kpis.length === 0) {
    return (
      <p className="text-sm text-neutral-500">No KPIs extracted yet.</p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {kpis.map((kpi, i) => (
        <MetricCard
          key={i}
          label={kpi.name ?? `KPI ${i + 1}`}
          value={`${kpi.value ?? "—"}${kpi.unit ? ` ${kpi.unit}` : ""}`}
        />
      ))}
    </div>
  );
}

// ── Financial display ──────────────────────────────────────────────────────

function FinancialSection({
  extraction,
}: {
  extraction: ExtractionResponse;
}) {
  const items = Array.isArray(extraction.result.items)
    ? (extraction.result.items as Array<{
        label?: string;
        amount?: string | number;
        currency?: string;
        period?: string;
      }>)
    : [];

  if (items.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        No financial data extracted yet.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div
          key={i}
          className="flex items-center justify-between rounded-md border border-neutral-200 px-3 py-2 dark:border-neutral-700"
        >
          <div>
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              {item.label ?? `Item ${i + 1}`}
            </p>
            {item.period && (
              <p className="text-xs text-neutral-500">{item.period}</p>
            )}
          </div>
          <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            {item.currency ?? "$"}
            {item.amount ?? "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Clauses display ────────────────────────────────────────────────────────

function ClauseSection({ extraction }: { extraction: ExtractionResponse }) {
  const clauses = Array.isArray(extraction.result.clauses)
    ? (extraction.result.clauses as Array<{
        title?: string;
        text?: string;
        risk_level?: string;
      }>)
    : [];

  if (clauses.length === 0) {
    return (
      <p className="text-sm text-neutral-500">No clauses extracted yet.</p>
    );
  }

  return (
    <div className="space-y-2">
      {clauses.map((clause, i) => (
        <Card key={i}>
          <CardContent className="py-3">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {clause.title ?? `Clause ${i + 1}`}
                </p>
                {clause.text && (
                  <p className="mt-1 text-xs text-neutral-500 line-clamp-3">
                    {clause.text}
                  </p>
                )}
              </div>
              {clause.risk_level && (
                <Badge
                  variant={
                    clause.risk_level === "high"
                      ? "error"
                      : clause.risk_level === "medium"
                        ? "warning"
                        : "neutral"
                  }
                >
                  {clause.risk_level}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Deadline display ───────────────────────────────────────────────────────

function DeadlineSection({
  extraction,
}: {
  extraction: ExtractionResponse;
}) {
  const deadlines = Array.isArray(extraction.result.deadlines)
    ? (extraction.result.deadlines as Array<{
        title?: string;
        date?: string;
        description?: string;
      }>)
    : [];

  if (deadlines.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        No deadlines extracted yet.
      </p>
    );
  }

  const timelineItems: TimelineItem[] = deadlines.map((d, i) => ({
    id: String(i),
    icon: <Calendar className="h-3.5 w-3.5" />,
    title: d.title ?? `Deadline ${i + 1}`,
    description: d.description,
    timestamp: d.date ?? "",
  }));

  return <Timeline items={timelineItems} />;
}

// ── Summary display ────────────────────────────────────────────────────────

function SummarySection({
  extraction,
}: {
  extraction: ExtractionResponse;
}) {
  const text =
    typeof extraction.result.summary === "string"
      ? extraction.result.summary
      : typeof extraction.result.text === "string"
        ? extraction.result.text
        : null;

  if (!text) {
    return (
      <p className="text-sm text-neutral-500">No summary available yet.</p>
    );
  }

  return (
    <div className="rounded-md border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-700 dark:bg-neutral-900">
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
        {text}
      </p>
    </div>
  );
}

// ── Tab config ─────────────────────────────────────────────────────────────

const TAB_CONFIG: {
  type: ExtractionType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  Component: React.ComponentType<{ extraction: ExtractionResponse }>;
}[] = [
  { type: "kpi", label: "KPIs", icon: TrendingUp, Component: KPISection },
  {
    type: "financial",
    label: "Financials",
    icon: DollarSign,
    Component: FinancialSection,
  },
  { type: "clause", label: "Clauses", icon: Scale, Component: ClauseSection },
  {
    type: "deadline",
    label: "Deadlines",
    icon: Calendar,
    Component: DeadlineSection,
  },
  {
    type: "summary",
    label: "Summary",
    icon: FileText,
    Component: SummarySection,
  },
];

// ── Main component ─────────────────────────────────────────────────────────

export function ExtractionPanel({
  extractions,
  loading,
  onReExtract,
  reExtracting,
}: ExtractionPanelProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (extractions.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <Brain className="h-10 w-10 text-neutral-300 dark:text-neutral-600" />
        <div>
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            No AI extractions yet
          </p>
          <p className="mt-0.5 text-xs text-neutral-500">
            Extractions run automatically after upload, or trigger manually.
          </p>
        </div>
        {onReExtract && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onReExtract()}
            loading={reExtracting}
            iconLeft={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Run extraction
          </Button>
        )}
      </div>
    );
  }

  // Build a map by type for quick lookup
  const byType = new Map<ExtractionType, ExtractionResponse>();
  for (const e of extractions) {
    byType.set(e.extraction_type, e);
  }

  // Filter to only tabs that have data
  const availableTabs = TAB_CONFIG.filter((t) => byType.has(t.type));
  const defaultTab = availableTabs[0]?.type ?? "kpi";

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary-500" />
          <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
            AI Extractions
          </span>
          <Badge variant="info">{extractions.length}</Badge>
        </div>
        {onReExtract && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onReExtract()}
            loading={reExtracting}
            iconLeft={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Re-extract
          </Button>
        )}
      </div>

      {/* Tabbed extraction results */}
      <Tabs defaultValue={defaultTab}>
        <TabsList>
          {availableTabs.map((tab) => (
            <TabsTrigger key={tab.type} value={tab.type}>
              <tab.icon className="mr-1.5 h-3.5 w-3.5" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {availableTabs.map((tab) => {
          const extraction = byType.get(tab.type)!;
          return (
            <TabsContent key={tab.type} value={tab.type}>
              <div className="space-y-3">
                {/* Confidence + metadata */}
                <div className="flex flex-wrap items-center gap-2">
                  <ConfidenceBadge score={extraction.confidence_score} />
                  <span className="text-xs text-neutral-400">
                    {extraction.model_used} &middot;{" "}
                    {extraction.processing_time_ms}ms
                  </span>
                </div>
                {/* Content */}
                <tab.Component extraction={extraction} />
              </div>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
