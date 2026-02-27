"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Coins, Loader2, Plus } from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState } from "@scr/ui";

import {
  blockchainColor,
  statusBadgeVariant,
  useCreateTokenization,
  useTokenizations,
  type TokenizationRecord,
  type TokenizationRequest,
} from "@/lib/tokenization";

// ── Cap Table Bar ─────────────────────────────────────────────────────────────

function CapTableBar({
  record,
}: {
  record: TokenizationRecord;
}) {
  const colors = [
    "bg-blue-500",
    "bg-green-500",
    "bg-purple-500",
    "bg-amber-500",
    "bg-red-400",
  ];
  return (
    <div className="space-y-3">
      {/* Stacked bar */}
      <div className="flex h-4 rounded-full overflow-hidden gap-0.5">
        {record.cap_table.map((h, i) => (
          <div
            key={h.holder_name}
            title={`${h.holder_name}: ${h.percentage}%`}
            style={{ width: `${h.percentage}%` }}
            className={`${colors[i % colors.length]}`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {record.cap_table.map((h, i) => (
          <div key={h.holder_name} className="flex items-center gap-1.5 text-xs">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-sm ${colors[i % colors.length]}`}
            />
            <span className="text-neutral-600">
              {h.holder_name} ({h.percentage}%)
            </span>
            {h.locked_until && (
              <span className="text-neutral-400 text-[10px]">
                locked to {h.locked_until}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Transfer History ──────────────────────────────────────────────────────────

function TransferHistory({ record }: { record: TokenizationRecord }) {
  if (record.transfer_history.length === 0) {
    return (
      <p className="text-xs text-neutral-400 italic">No transfers recorded.</p>
    );
  }
  return (
    <table className="w-full text-xs text-left">
      <thead>
        <tr className="text-neutral-400 border-b border-neutral-100">
          <th className="pb-1 font-medium">From</th>
          <th className="pb-1 font-medium">To</th>
          <th className="pb-1 font-medium">Tokens</th>
          <th className="pb-1 font-medium">Date</th>
        </tr>
      </thead>
      <tbody>
        {record.transfer_history.map((t, i) => (
          <tr key={i} className="border-b border-neutral-50">
            <td className="py-1">{String(t.from_holder ?? "—")}</td>
            <td className="py-1">{String(t.to_holder ?? "—")}</td>
            <td className="py-1">
              {typeof t.tokens === "number"
                ? t.tokens.toLocaleString()
                : "—"}
            </td>
            <td className="py-1 text-neutral-400">
              {t.timestamp
                ? new Date(String(t.timestamp)).toLocaleDateString()
                : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ── Token Card ────────────────────────────────────────────────────────────────

function TokenCard({ record }: { record: TokenizationRecord }) {
  const [expanded, setExpanded] = useState(false);
  const marketCapM = (record.market_cap_usd / 1_000_000).toFixed(2);

  return (
    <Card>
      <CardContent className="pt-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-neutral-900">
                {record.token_name}
              </h3>
              <span className="text-xs font-mono text-neutral-500 bg-neutral-100 px-1.5 py-0.5 rounded">
                {record.token_symbol}
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-0.5">
              {record.total_supply.toLocaleString()} tokens @{" "}
              <span className="font-medium">
                ${record.token_price_usd.toFixed(4)}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={statusBadgeVariant(record.status)}>
              {record.status.replace("_", " ")}
            </Badge>
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-3 text-xs text-neutral-500">
          <span className={`font-medium ${blockchainColor(record.blockchain)}`}>
            {record.blockchain}
          </span>
          <span>{record.token_type}</span>
          <span>{record.regulatory_framework}</span>
          <span className="ml-auto font-semibold text-neutral-800">
            Market Cap: ${marketCapM}M
          </span>
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          {expanded ? (
            <>
              <ChevronUp size={14} /> Hide details
            </>
          ) : (
            <>
              <ChevronDown size={14} /> Cap table & transfers
            </>
          )}
        </button>

        {expanded && (
          <div className="pt-2 border-t border-neutral-100 space-y-4">
            <div>
              <p className="text-xs font-medium text-neutral-500 mb-2">
                Cap Table
              </p>
              <CapTableBar record={record} />
            </div>
            <div>
              <p className="text-xs font-medium text-neutral-500 mb-2">
                Transfer History
              </p>
              <TransferHistory record={record} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Create Form ───────────────────────────────────────────────────────────────

const DEFAULT_FORM: Partial<TokenizationRequest> = {
  blockchain: "Ethereum",
  token_type: "security",
  regulatory_framework: "Reg D",
  minimum_investment_usd: 1000,
  lock_up_period_days: 365,
};

function CreateTokenForm({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<Partial<TokenizationRequest>>(DEFAULT_FORM);
  const createMutation = useCreateTokenization();

  function set<K extends keyof TokenizationRequest>(
    key: K,
    value: TokenizationRequest[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (
      !form.project_id ||
      !form.token_name ||
      !form.token_symbol ||
      !form.total_supply ||
      !form.token_price_usd
    )
      return;
    createMutation.mutate(form as TokenizationRequest, {
      onSuccess: onClose,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardContent className="pt-5">
          <h2 className="text-lg font-semibold mb-4">Tokenize Project</h2>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {(
                [
                  { key: "project_id", label: "Project ID", type: "text", required: true },
                  { key: "token_name", label: "Token Name", type: "text", required: true },
                  { key: "token_symbol", label: "Symbol", type: "text", required: true },
                  { key: "total_supply", label: "Total Supply", type: "number", required: true },
                  { key: "token_price_usd", label: "Token Price (USD)", type: "number", required: true },
                  { key: "minimum_investment_usd", label: "Min. Investment (USD)", type: "number", required: false },
                  { key: "lock_up_period_days", label: "Lock-up (days)", type: "number", required: false },
                ] as Array<{ key: keyof TokenizationRequest; label: string; type: string; required: boolean }>
              ).map(({ key, label, type, required }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-neutral-500 mb-1">
                    {label}
                    {required && (
                      <span className="text-red-500 ml-0.5">*</span>
                    )}
                  </label>
                  <input
                    type={type}
                    step="any"
                    required={required}
                    onChange={(e) =>
                      set(
                        key,
                        type === "number"
                          ? (parseFloat(e.target.value) as never)
                          : (e.target.value as never),
                      )
                    }
                    className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>

            {/* Selects */}
            <div className="grid grid-cols-3 gap-3">
              {(
                [
                  {
                    key: "blockchain",
                    label: "Blockchain",
                    opts: ["Ethereum", "Polygon", "Solana"],
                  },
                  {
                    key: "token_type",
                    label: "Token Type",
                    opts: ["security", "utility", "equity"],
                  },
                  {
                    key: "regulatory_framework",
                    label: "Framework",
                    opts: ["Reg D", "Reg A+", "Reg CF", "ERC-3643"],
                  },
                ] as const
              ).map(({ key, label, opts }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-neutral-500 mb-1">
                    {label}
                  </label>
                  <select
                    value={(form[key] as string) ?? ""}
                    onChange={(e) => set(key, e.target.value as never)}
                    className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {opts.map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                type="submit"
                disabled={createMutation.isPending}
                className="flex-1"
              >
                {createMutation.isPending && (
                  <Loader2 size={14} className="mr-1.5 animate-spin" />
                )}
                Create Token
              </Button>
              <Button variant="outline" type="button" onClick={onClose}>
                Cancel
              </Button>
            </div>
            {createMutation.isError && (
              <p className="text-xs text-red-600">
                Failed to create tokenization. Check the project ID.
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function TokenizationPage() {
  const { data: records, isLoading } = useTokenizations();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-100">
            <Coins size={22} className="text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Token Management
            </h1>
            <p className="text-sm text-neutral-500">
              On-chain token issuance, cap tables and transfer registry
            </p>
          </div>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus size={16} className="mr-1.5" />
          Tokenize Project
        </Button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-indigo-600" />
        </div>
      )}

      {/* Empty */}
      {!isLoading && (!records || records.length === 0) && (
        <EmptyState
          icon={<Coins size={40} className="text-neutral-400" />}
          title="No tokenized projects"
          description="Click 'Tokenize Project' to create your first on-chain token offering."
        />
      )}

      {/* Token cards */}
      {!isLoading && records && records.length > 0 && (
        <div className="space-y-4">
          {records.map((record) => (
            <TokenCard key={record.id} record={record} />
          ))}
        </div>
      )}

      {showForm && <CreateTokenForm onClose={() => setShowForm(false)} />}
    </div>
  );
}
