"use client";

import { useRef, useState } from "react";
import {
  BarChart3,
  Clock,
  Database,
  Loader2,
  RefreshCw,
  Upload,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  cn,
} from "@scr/ui";
import {
  useBenchmarkList,
  useComputeBenchmarks,
  useImportBenchmarks,
  type BenchmarkEntry,
} from "@/lib/metrics";

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary-100 text-primary-600">
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-neutral-500">{label}</p>
          <p className="text-2xl font-semibold text-neutral-900 truncate">
            {value}
          </p>
          {sub && <p className="text-xs text-neutral-400">{sub}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Benchmark table row ───────────────────────────────────────────────────────

function BenchmarkRow({ entry }: { entry: BenchmarkEntry }) {
  return (
    <tr className="border-b last:border-0 hover:bg-neutral-50">
      <td className="px-4 py-3 text-sm text-neutral-700 capitalize">
        {entry.asset_class.replace(/_/g, " ")}
      </td>
      <td className="px-4 py-3 text-sm text-neutral-700">
        {entry.geography || "—"}
      </td>
      <td className="px-4 py-3 text-sm text-neutral-700 capitalize">
        {entry.stage.replace(/_/g, " ") || "—"}
      </td>
      <td className="px-4 py-3 text-sm font-medium text-neutral-900">
        {entry.metric_name.replace(/_/g, " ")}
      </td>
      <td className="px-4 py-3 text-right text-sm text-neutral-700">
        {entry.median.toFixed(1)}
      </td>
      <td className="px-4 py-3 text-right text-sm text-neutral-500">
        {entry.p25.toFixed(1)}
      </td>
      <td className="px-4 py-3 text-right text-sm text-neutral-500">
        {entry.p75.toFixed(1)}
      </td>
      <td className="px-4 py-3 text-right text-sm text-neutral-500">
        {entry.sample_count}
      </td>
    </tr>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BenchmarksAdminPage() {
  const { data: list, isLoading: listLoading } = useBenchmarkList();
  const computeMutation = useComputeBenchmarks();
  const importMutation = useImportBenchmarks();

  const fileRef = useRef<HTMLInputElement>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const [computeSuccess, setComputeSuccess] = useState<string | null>(null);

  const benchmarks = list?.items ?? [];

  // Derive stats
  const assetClasses = new Set(benchmarks.map((b) => b.asset_class)).size;
  const geographies = new Set(benchmarks.map((b) => b.geography)).size;
  const lastComputed =
    benchmarks
      .map((b) => b.computed_at)
      .filter(Boolean)
      .sort()
      .at(-1) ?? null;

  const handleCompute = async () => {
    setComputeSuccess(null);
    try {
      const result = await computeMutation.mutateAsync(undefined);
      setComputeSuccess(`Computed ${result.computed} benchmarks.`);
    } catch {
      // error shown via mutation state
    }
  };

  const handleFileChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setImportError(null);
    setImportSuccess(null);
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await importMutation.mutateAsync(file);
      setImportSuccess(
        `Imported ${result.imported} benchmarks (${result.skipped} skipped).`
      );
    } catch {
      setImportError("Import failed. Check the CSV format and try again.");
    } finally {
      // reset input so the same file can be re-selected
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">
          Benchmark Management
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Manage peer benchmarks used for signal-score comparison across the
          platform.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Total Benchmarks"
          value={listLoading ? "—" : benchmarks.length}
          icon={Database}
        />
        <StatCard
          label="Last Computed"
          value={
            lastComputed
              ? new Date(lastComputed).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })
              : "Never"
          }
          icon={Clock}
        />
        <StatCard
          label="Coverage"
          value={
            listLoading
              ? "—"
              : `${assetClasses} asset class${assetClasses !== 1 ? "es" : ""}`
          }
          sub={`${geographies} geograph${geographies !== 1 ? "ies" : "y"}`}
          icon={BarChart3}
        />
      </div>

      {/* Actions row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recompute card */}
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-1 text-sm font-semibold text-neutral-900">
              Recompute Benchmarks
            </h3>
            <p className="mb-4 text-xs text-neutral-500">
              Recalculates all benchmark statistics from current platform data.
              This may take a few seconds.
            </p>
            {computeSuccess && (
              <p className="mb-3 text-xs text-green-600">{computeSuccess}</p>
            )}
            {computeMutation.isError && (
              <p className="mb-3 text-xs text-red-600">
                Compute failed. Please try again.
              </p>
            )}
            <Button
              onClick={handleCompute}
              disabled={computeMutation.isPending}
            >
              {computeMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              {computeMutation.isPending ? "Computing..." : "Recompute"}
            </Button>
          </CardContent>
        </Card>

        {/* CSV import card */}
        <Card>
          <CardContent className="p-5">
            <h3 className="mb-1 text-sm font-semibold text-neutral-900">
              Import from CSV
            </h3>
            <p className="mb-4 text-xs text-neutral-500">
              Upload a CSV file with columns: asset_class, geography, stage,
              metric_name, median, p25, p75, sample_count.
            </p>
            {importSuccess && (
              <p className="mb-3 text-xs text-green-600">{importSuccess}</p>
            )}
            {importError && (
              <p className="mb-3 text-xs text-red-600">{importError}</p>
            )}
            <label
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-lg border-2 border-dashed border-neutral-300 px-4 py-3 text-sm text-neutral-600 transition hover:border-primary-400 hover:text-primary-600",
                importMutation.isPending && "pointer-events-none opacity-60"
              )}
            >
              {importMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {importMutation.isPending
                ? "Uploading..."
                : "Choose CSV file to import"}
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                className="sr-only"
                onChange={handleFileChange}
                disabled={importMutation.isPending}
              />
            </label>
          </CardContent>
        </Card>
      </div>

      {/* Benchmark table */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-neutral-900">
          Existing Benchmarks
          {!listLoading && (
            <span className="ml-2 font-normal text-neutral-400">
              ({benchmarks.length})
            </span>
          )}
        </h2>

        {listLoading ? (
          <Card>
            <CardContent className="p-6">
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className="h-10 animate-pulse rounded bg-neutral-100"
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        ) : !benchmarks.length ? (
          <EmptyState
            icon={<Database className="h-12 w-12 text-neutral-400" />}
            title="No benchmarks yet"
            description="Recompute or import a CSV to populate benchmark data."
          />
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-neutral-500">
                    <th className="px-4 py-3 font-medium">Asset Class</th>
                    <th className="px-4 py-3 font-medium">Geography</th>
                    <th className="px-4 py-3 font-medium">Stage</th>
                    <th className="px-4 py-3 font-medium">Metric</th>
                    <th className="px-4 py-3 text-right font-medium">
                      Median
                    </th>
                    <th className="px-4 py-3 text-right font-medium">P25</th>
                    <th className="px-4 py-3 text-right font-medium">P75</th>
                    <th className="px-4 py-3 text-right font-medium">
                      Sample N
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {benchmarks.map((entry) => (
                    <BenchmarkRow key={entry.id} entry={entry} />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
