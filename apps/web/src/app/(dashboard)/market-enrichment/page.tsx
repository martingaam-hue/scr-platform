"use client";

import { useState } from "react";
import {
  Database,
  Plus,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Activity,
} from "lucide-react";
import {
  useMarketEnrichmentDashboard,
  useMarketDataSources,
  useMarketData,
  useReviewQueue,
  useCreateSource,
  useTriggerFetch,
  useCreateManualEntry,
  useReviewEntry,
  DATA_TYPES,
  TIER_LABELS,
  LEGAL_BASIS_LABELS,
  REVIEW_STATUS_BADGE,
  FETCH_STATUS_BADGE,
  type MarketDataSource,
  type MarketDataProcessed,
  type ReviewQueueItem,
} from "@/lib/market-enrichment";

type Tab = "overview" | "data" | "sources" | "review";

export default function MarketEnrichmentPage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [dataFilters, setDataFilters] = useState({
    data_type: "",
    category: "",
    region: "",
    technology: "",
    review_status: "",
  });
  const [sourceFilters, setSourceFilters] = useState<{ tier?: number; is_active?: boolean }>({});
  const [showAddSource, setShowAddSource] = useState(false);
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [newSource, setNewSource] = useState({
    name: "",
    slug: "",
    source_type: "official_api",
    tier: "1",
    base_url: "",
    legal_basis: "public_data",
    description: "",
  });
  const [newEntry, setNewEntry] = useState({
    data_type: "price",
    category: "",
    region: "",
    technology: "",
    effective_date: "",
    value_numeric: "",
    value_text: "",
    unit: "",
    source_url: "",
  });

  const { data: dashboard, isLoading: dashLoading } = useMarketEnrichmentDashboard();
  const { data: sources } = useMarketDataSources(sourceFilters);
  const { data: dataRows, isLoading: dataLoading } = useMarketData(
    Object.fromEntries(Object.entries(dataFilters).filter(([, v]) => v !== ""))
  );
  const { data: reviewItems } = useReviewQueue();

  const createSource = useCreateSource();
  const triggerFetch = useTriggerFetch();
  const createEntry = useCreateManualEntry();
  const reviewEntry = useReviewEntry();

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "data", label: "Data Browser" },
    { id: "sources", label: "Sources" },
    { id: "review", label: `Review Queue${(reviewItems?.length ?? 0) > 0 ? ` (${reviewItems!.length})` : ""}` },
  ];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Database className="h-6 w-6 text-primary-600" />
            Market Data Enrichment
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Structured, auditable market data from official APIs, RSS feeds, and manual entry
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowManualEntry(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
          >
            <Plus className="h-4 w-4" />
            Manual Entry
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex -mb-px gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-primary-600 text-primary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Overview Tab ── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {dashLoading ? (
            <div className="text-gray-400 text-sm">Loading...</div>
          ) : dashboard ? (
            <>
              {/* Stats cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  icon={<Database className="h-5 w-5 text-blue-500" />}
                  label="Data Sources"
                  value={`${dashboard.active_sources_count} / ${dashboard.sources_count}`}
                  sub="active / total"
                />
                <StatCard
                  icon={<Activity className="h-5 w-5 text-green-500" />}
                  label="Records Today"
                  value={String(dashboard.records_today)}
                  sub="new processed records"
                />
                <StatCard
                  icon={<AlertTriangle className="h-5 w-5 text-yellow-500" />}
                  label="Pending Review"
                  value={String(dashboard.pending_review_count)}
                  sub="need human review"
                />
                <StatCard
                  icon={<Clock className="h-5 w-5 text-gray-400" />}
                  label="Recent Fetches"
                  value={String(dashboard.recent_fetches.length)}
                  sub="last 10 fetch runs"
                />
              </div>

              {/* Recent fetch log */}
              <div className="bg-white rounded-xl border border-gray-200">
                <div className="p-4 border-b border-gray-100">
                  <h2 className="text-sm font-semibold text-gray-700">Recent Fetch Activity</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-left text-xs text-gray-500">
                        <th className="px-4 py-2">Source</th>
                        <th className="px-4 py-2">Status</th>
                        <th className="px-4 py-2">Fetched</th>
                        <th className="px-4 py-2">New</th>
                        <th className="px-4 py-2">Completed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboard.recent_fetches.map((log) => (
                        <tr key={log.id} className="border-t border-gray-100 hover:bg-gray-50">
                          <td className="px-4 py-2 font-mono text-xs text-gray-500">
                            {log.source_id.slice(0, 8)}…
                          </td>
                          <td className="px-4 py-2">
                            <span
                              className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${FETCH_STATUS_BADGE[log.status] ?? ""}`}
                            >
                              {log.status}
                            </span>
                          </td>
                          <td className="px-4 py-2">{log.records_fetched}</td>
                          <td className="px-4 py-2">{log.records_new}</td>
                          <td className="px-4 py-2 text-gray-400 text-xs">
                            {log.completed_at
                              ? new Date(log.completed_at).toLocaleString()
                              : "—"}
                          </td>
                        </tr>
                      ))}
                      {dashboard.recent_fetches.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">
                            No fetch activity yet
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* ── Data Browser Tab ── */}
      {activeTab === "data" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3 p-4 bg-gray-50 rounded-xl border border-gray-200">
            <select
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
              value={dataFilters.data_type}
              onChange={(e) => setDataFilters((f) => ({ ...f, data_type: e.target.value }))}
            >
              <option value="">All Types</option>
              {DATA_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <input
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-36"
              placeholder="Category"
              value={dataFilters.category}
              onChange={(e) => setDataFilters((f) => ({ ...f, category: e.target.value }))}
            />
            <input
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-32"
              placeholder="Region"
              value={dataFilters.region}
              onChange={(e) => setDataFilters((f) => ({ ...f, region: e.target.value }))}
            />
            <input
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-32"
              placeholder="Technology"
              value={dataFilters.technology}
              onChange={(e) => setDataFilters((f) => ({ ...f, technology: e.target.value }))}
            />
            <select
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
              value={dataFilters.review_status}
              onChange={(e) => setDataFilters((f) => ({ ...f, review_status: e.target.value }))}
            >
              <option value="">All Statuses</option>
              <option value="pending_review">Pending Review</option>
              <option value="auto_accepted">Auto Accepted</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <DataTable rows={dataRows ?? []} isLoading={dataLoading} />
        </div>
      )}

      {/* ── Sources Tab ── */}
      {activeTab === "sources" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex gap-3">
              <select
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                value={sourceFilters.tier ?? ""}
                onChange={(e) =>
                  setSourceFilters((f) => ({
                    ...f,
                    tier: e.target.value ? Number(e.target.value) : undefined,
                  }))
                }
              >
                <option value="">All Tiers</option>
                {Object.entries(TIER_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    Tier {k}: {v}
                  </option>
                ))}
              </select>
              <select
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
                value={sourceFilters.is_active === undefined ? "" : String(sourceFilters.is_active)}
                onChange={(e) =>
                  setSourceFilters((f) => ({
                    ...f,
                    is_active: e.target.value === "" ? undefined : e.target.value === "true",
                  }))
                }
              >
                <option value="">Active & Inactive</option>
                <option value="true">Active only</option>
                <option value="false">Inactive only</option>
              </select>
            </div>
            <button
              onClick={() => setShowAddSource(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
            >
              <Plus className="h-4 w-4" />
              Add Source
            </button>
          </div>

          <div className="grid gap-4">
            {(sources ?? []).map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                onFetch={() => triggerFetch.mutate(source.id)}
                fetchPending={triggerFetch.isPending && triggerFetch.variables === source.id}
              />
            ))}
            {(sources ?? []).length === 0 && (
              <div className="text-center py-12 text-gray-400 text-sm">
                No sources configured yet. Add your first data source.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Review Queue Tab ── */}
      {activeTab === "review" && (
        <div className="space-y-4">
          {(reviewItems ?? []).length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="h-10 w-10 text-green-400 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No items pending review</p>
            </div>
          ) : (
            <div className="space-y-3">
              {(reviewItems ?? []).map((item) => (
                <ReviewCard
                  key={item.id}
                  item={item}
                  onApprove={() =>
                    reviewEntry.mutate({ processedId: item.processed_id, action: "approve" })
                  }
                  onReject={() =>
                    reviewEntry.mutate({ processedId: item.processed_id, action: "reject" })
                  }
                  isPending={reviewEntry.isPending}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Add Source Modal ── */}
      {showAddSource && (
        <Modal title="Add Data Source" onClose={() => setShowAddSource(false)}>
          <div className="space-y-4">
            <Field label="Name">
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={newSource.name}
                onChange={(e) => setNewSource((s) => ({ ...s, name: e.target.value }))}
              />
            </Field>
            <Field label="Slug (unique ID)">
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
                placeholder="e.g. eia_electricity_prices"
                value={newSource.slug}
                onChange={(e) => setNewSource((s) => ({ ...s, slug: e.target.value }))}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Source Type">
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newSource.source_type}
                  onChange={(e) => setNewSource((s) => ({ ...s, source_type: e.target.value }))}
                >
                  <option value="official_api">Official API</option>
                  <option value="rss_feed">RSS Feed</option>
                  <option value="document">Document</option>
                  <option value="manual">Manual</option>
                </select>
              </Field>
              <Field label="Tier">
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newSource.tier}
                  onChange={(e) => setNewSource((s) => ({ ...s, tier: e.target.value }))}
                >
                  <option value="1">Tier 1 — Official API</option>
                  <option value="2">Tier 2 — RSS Feed</option>
                  <option value="3">Tier 3 — Document</option>
                  <option value="4">Tier 4 — Manual</option>
                </select>
              </Field>
            </div>
            <Field label="Base URL">
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="https://api.example.com/data"
                value={newSource.base_url}
                onChange={(e) => setNewSource((s) => ({ ...s, base_url: e.target.value }))}
              />
            </Field>
            <Field label="Legal Basis">
              <select
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                value={newSource.legal_basis}
                onChange={(e) => setNewSource((s) => ({ ...s, legal_basis: e.target.value }))}
              >
                {Object.entries(LEGAL_BASIS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Description">
              <textarea
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                rows={2}
                value={newSource.description}
                onChange={(e) => setNewSource((s) => ({ ...s, description: e.target.value }))}
              />
            </Field>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowAddSource(false)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  createSource.mutate(
                    {
                      ...newSource,
                      tier: Number(newSource.tier),
                    },
                    { onSuccess: () => setShowAddSource(false) }
                  );
                }}
                disabled={createSource.isPending || !newSource.name || !newSource.slug}
                className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {createSource.isPending ? "Adding…" : "Add Source"}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Manual Entry Modal ── */}
      {showManualEntry && (
        <Modal title="Manual Data Entry" onClose={() => setShowManualEntry(false)}>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Data Type">
                <select
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newEntry.data_type}
                  onChange={(e) => setNewEntry((s) => ({ ...s, data_type: e.target.value }))}
                >
                  {DATA_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Category">
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="e.g. solar_ppa_price"
                  value={newEntry.category}
                  onChange={(e) => setNewEntry((s) => ({ ...s, category: e.target.value }))}
                />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Region">
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="e.g. EU, US, UK"
                  value={newEntry.region}
                  onChange={(e) => setNewEntry((s) => ({ ...s, region: e.target.value }))}
                />
              </Field>
              <Field label="Technology">
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="e.g. solar, wind"
                  value={newEntry.technology}
                  onChange={(e) => setNewEntry((s) => ({ ...s, technology: e.target.value }))}
                />
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Value">
                <input
                  type="number"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="0.00"
                  value={newEntry.value_numeric}
                  onChange={(e) => setNewEntry((s) => ({ ...s, value_numeric: e.target.value }))}
                />
              </Field>
              <Field label="Unit">
                <input
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="USD/MWh"
                  value={newEntry.unit}
                  onChange={(e) => setNewEntry((s) => ({ ...s, unit: e.target.value }))}
                />
              </Field>
              <Field label="Effective Date">
                <input
                  type="date"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={newEntry.effective_date}
                  onChange={(e) => setNewEntry((s) => ({ ...s, effective_date: e.target.value }))}
                />
              </Field>
            </div>
            <Field label="Text Value (optional)">
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="Descriptive text or note"
                value={newEntry.value_text}
                onChange={(e) => setNewEntry((s) => ({ ...s, value_text: e.target.value }))}
              />
            </Field>
            <Field label="Source URL (optional)">
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                placeholder="https://..."
                value={newEntry.source_url}
                onChange={(e) => setNewEntry((s) => ({ ...s, source_url: e.target.value }))}
              />
            </Field>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowManualEntry(false)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const payload: Record<string, unknown> = {
                    data_type: newEntry.data_type,
                    category: newEntry.category,
                  };
                  if (newEntry.region) payload.region = newEntry.region;
                  if (newEntry.technology) payload.technology = newEntry.technology;
                  if (newEntry.effective_date) payload.effective_date = newEntry.effective_date;
                  if (newEntry.value_numeric) payload.value_numeric = Number(newEntry.value_numeric);
                  if (newEntry.value_text) payload.value_text = newEntry.value_text;
                  if (newEntry.unit) payload.unit = newEntry.unit;
                  if (newEntry.source_url) payload.source_url = newEntry.source_url;
                  createEntry.mutate(payload, { onSuccess: () => setShowManualEntry(false) });
                }}
                disabled={createEntry.isPending || !newEntry.category}
                className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {createEntry.isPending ? "Saving…" : "Save Entry"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-400 mt-1">{sub}</div>
    </div>
  );
}

function DataTable({
  rows,
  isLoading,
}: {
  rows: MarketDataProcessed[];
  isLoading: boolean;
}) {
  if (isLoading) return <div className="text-gray-400 text-sm py-8 text-center">Loading…</div>;
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs text-gray-500">
            <th className="px-4 py-2">Type</th>
            <th className="px-4 py-2">Category</th>
            <th className="px-4 py-2">Region</th>
            <th className="px-4 py-2">Technology</th>
            <th className="px-4 py-2">Date</th>
            <th className="px-4 py-2">Value</th>
            <th className="px-4 py-2">Confidence</th>
            <th className="px-4 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-2">
                <span className="inline-block px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                  {row.data_type}
                </span>
              </td>
              <td className="px-4 py-2 font-medium">{row.category}</td>
              <td className="px-4 py-2 text-gray-500">{row.region ?? "—"}</td>
              <td className="px-4 py-2 text-gray-500">{row.technology ?? "—"}</td>
              <td className="px-4 py-2 text-gray-500">{row.effective_date ?? "—"}</td>
              <td className="px-4 py-2">
                {row.value_numeric != null
                  ? `${row.value_numeric}${row.unit ? ` ${row.unit}` : ""}`
                  : row.value_text?.slice(0, 40) ?? "—"}
              </td>
              <td className="px-4 py-2">
                <ConfidenceBar value={row.confidence} />
              </td>
              <td className="px-4 py-2">
                <span
                  className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${REVIEW_STATUS_BADGE[row.review_status] ?? ""}`}
                >
                  {row.review_status.replace("_", " ")}
                </span>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={8} className="px-4 py-8 text-center text-gray-400 text-sm">
                No data records found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-green-400" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct}%</span>
    </div>
  );
}

function SourceCard({
  source,
  onFetch,
  fetchPending,
}: {
  source: MarketDataSource;
  onFetch: () => void;
  fetchPending: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-900">{source.name}</span>
          <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
            Tier {source.tier} — {TIER_LABELS[source.tier]}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded ${source.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
          >
            {source.is_active ? "Active" : "Inactive"}
          </span>
        </div>
        <div className="flex gap-4 text-xs text-gray-500">
          <span>Slug: <code className="font-mono">{source.slug}</code></span>
          <span>Legal: {LEGAL_BASIS_LABELS[source.legal_basis]}</span>
          {source.base_url && (
            <span className="truncate max-w-xs">{source.base_url}</span>
          )}
        </div>
        {source.description && (
          <p className="text-xs text-gray-400">{source.description}</p>
        )}
      </div>
      <button
        onClick={onFetch}
        disabled={fetchPending || !source.is_active}
        className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
      >
        <RefreshCw className={`h-4 w-4 ${fetchPending ? "animate-spin" : ""}`} />
        Fetch Now
      </button>
    </div>
  );
}

function ReviewCard({
  item,
  onApprove,
  onReject,
  isPending,
}: {
  item: ReviewQueueItem;
  onApprove: () => void;
  onReject: () => void;
  isPending: boolean;
}) {
  const p = item.processed;
  return (
    <div className="bg-white rounded-xl border border-yellow-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
            <span className="text-sm font-medium text-gray-900">{item.reason}</span>
            {item.priority > 0 && (
              <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded">
                High Priority
              </span>
            )}
          </div>
          {p && (
            <div className="text-xs text-gray-500 space-y-0.5">
              <div>
                <strong>{p.category}</strong> · {p.data_type} · {p.region ?? "—"} · {p.technology ?? "—"}
              </div>
              <div>
                Value:{" "}
                {p.value_numeric != null
                  ? `${p.value_numeric} ${p.unit ?? ""}`
                  : p.value_text?.slice(0, 60) ?? "—"}
              </div>
              <div>Effective: {p.effective_date ?? "—"}</div>
              <div>Confidence: {Math.round(p.confidence * 100)}%</div>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={onApprove}
            disabled={isPending}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            <CheckCircle className="h-4 w-4" />
            Approve
          </button>
          <button
            onClick={onReject}
            disabled={isPending}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            <XCircle className="h-4 w-4" />
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <XCircle className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
