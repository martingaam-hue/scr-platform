"use client";

import { useState } from "react";
import {
  Receipt,
  Zap,
  TrendingUp,
  FileText,
  Loader2,
  CheckCircle,
  AlertCircle,
  Download,
  RefreshCw,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  DataTable,
  EmptyState,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
} from "@scr/ui";
import {
  useTaxCreditInventory,
  useIdentifyCredits,
  useRunOptimization,
  useGenerateTransferDocs,
  qualificationVariant,
  QUALIFICATION_LABELS,
  CREDIT_TYPE_DESCRIPTIONS,
  formatCreditValue,
  actionVariant,
  type TaxCreditResponse,
  type IdentificationResponse,
  type OptimizationResult,
  type OptimizationAction,
} from "@/lib/tax-credits";

// ── Inventory tab ─────────────────────────────────────────────────────────────

function InventoryTab({
  portfolioId,
  onPortfolioChange,
}: {
  portfolioId: string;
  onPortfolioChange: (id: string) => void;
}) {
  const { data, isLoading } = useTaxCreditInventory(portfolioId || undefined);

  const columns: ColumnDef<TaxCreditResponse>[] = [
    {
      accessorKey: "project_name",
      header: "Project",
      cell: ({ row }) => (
        <span className="font-medium">{row.original.project_name ?? "—"}</span>
      ),
    },
    {
      accessorKey: "credit_type",
      header: "Credit Type",
      cell: ({ row }) => (
        <div>
          <div className="font-medium text-sm">{row.original.credit_type}</div>
          <div className="text-xs text-neutral-500">
            {CREDIT_TYPE_DESCRIPTIONS[row.original.credit_type] ?? ""}
          </div>
        </div>
      ),
    },
    {
      accessorKey: "estimated_value",
      header: "Estimated Value",
      cell: ({ row }) =>
        formatCreditValue(row.original.estimated_value, row.original.currency),
    },
    {
      accessorKey: "claimed_value",
      header: "Claimed",
      cell: ({ row }) =>
        row.original.claimed_value
          ? formatCreditValue(row.original.claimed_value, row.original.currency)
          : "—",
    },
    {
      accessorKey: "qualification",
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={qualificationVariant(row.original.qualification)}>
          {QUALIFICATION_LABELS[row.original.qualification]}
        </Badge>
      ),
    },
    {
      accessorKey: "expiry_date",
      header: "Expiry",
      cell: ({ row }) =>
        row.original.expiry_date
          ? new Date(row.original.expiry_date).getFullYear()
          : "—",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Portfolio selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-neutral-700">Portfolio ID:</label>
        <input
          value={portfolioId}
          onChange={(e) => onPortfolioChange(e.target.value)}
          placeholder="Paste portfolio UUID"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
      </div>

      {!portfolioId ? (
        <EmptyState
          title="Select a portfolio"
          description="Enter a portfolio ID above to view its tax credit inventory."
          icon={<Receipt className="h-8 w-8 text-neutral-400" />}
        />
      ) : isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Summary cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-neutral-500 mb-1">
                  Total Estimated Value
                </div>
                <div className="text-2xl font-bold text-blue-700">
                  {formatCreditValue(
                    data?.total_estimated ?? 0,
                    data?.currency ?? "USD"
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-neutral-500 mb-1">Total Claimed</div>
                <div className="text-2xl font-bold text-green-700">
                  {formatCreditValue(
                    data?.total_claimed ?? 0,
                    data?.currency ?? "USD"
                  )}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-neutral-500 mb-1">Credit Types</div>
                <div className="text-2xl font-bold">
                  {Object.keys(data?.credits_by_type ?? {}).length}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* By type breakdown */}
          {data && Object.keys(data.credits_by_type).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">By Credit Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(data.credits_by_type).map(([type, value]) => {
                    const pct = data.total_estimated > 0
                      ? (value / data.total_estimated) * 100
                      : 0;
                    return (
                      <div key={type} className="flex items-center gap-3">
                        <div className="w-24 text-sm font-medium text-neutral-700 shrink-0">
                          {type}
                        </div>
                        <div className="flex-1 bg-neutral-100 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        </div>
                        <div className="w-28 text-sm text-right text-neutral-700 shrink-0">
                          {formatCreditValue(value, data.currency)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Credits table */}
          {data?.credits?.length ? (
            <DataTable data={data.credits} columns={columns} />
          ) : (
            <EmptyState
              title="No tax credits found"
              description="Use the Identify tab to find applicable credits for your projects."
              icon={<AlertCircle className="h-8 w-8 text-neutral-400" />}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ── Identify tab ──────────────────────────────────────────────────────────────

function IdentifyTab() {
  const identify = useIdentifyCredits();
  const [projectId, setProjectId] = useState("");
  const [result, setResult] = useState<IdentificationResponse | null>(null);

  async function handleIdentify() {
    if (!projectId.trim()) return;
    const res = await identify.mutateAsync(projectId.trim());
    setResult(res);
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <p className="text-sm text-neutral-600">
          AI-powered identification of applicable US federal and state tax credits
          based on project type, geography, and development stage.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <input
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          placeholder="Paste project UUID"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
        <Button onClick={handleIdentify} disabled={!projectId.trim() || identify.isPending}>
          {identify.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Zap className="h-4 w-4 mr-2" />
          )}
          Identify Credits
        </Button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-neutral-900">
                {result.project_name}
              </h3>
              <p className="text-sm text-neutral-500">
                {result.identified.length} credit
                {result.identified.length !== 1 ? "s" : ""} identified ·{" "}
                <span className="font-medium text-blue-700">
                  {formatCreditValue(result.total_estimated_value, result.currency)} total
                </span>
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {result.identified.map((credit, i) => (
              <Card key={i}>
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-sm">
                          {credit.credit_type}
                        </span>
                        <Badge
                          variant={
                            credit.qualification === "qualified"
                              ? "success"
                              : "warning"
                          }
                        >
                          {credit.qualification}
                        </Badge>
                        {credit.expiry_year && (
                          <span className="text-xs text-neutral-400">
                            Expires {credit.expiry_year}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-neutral-500">
                        {credit.program_name}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-sm font-bold text-neutral-900">
                        {formatCreditValue(credit.estimated_value, result.currency)}
                      </div>
                      <div className="text-xs text-neutral-400">estimated</div>
                    </div>
                  </div>

                  {credit.criteria_met.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-green-700 mb-1">
                        Criteria met:
                      </p>
                      <ul className="space-y-0.5">
                        {credit.criteria_met.map((c, j) => (
                          <li key={j} className="flex items-center gap-1.5 text-xs text-neutral-600">
                            <CheckCircle className="h-3 w-3 text-green-500 shrink-0" />
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {credit.criteria_missing.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-amber-700 mb-1">
                        Missing:
                      </p>
                      <ul className="space-y-0.5">
                        {credit.criteria_missing.map((c, j) => (
                          <li key={j} className="flex items-center gap-1.5 text-xs text-neutral-500">
                            <AlertCircle className="h-3 w-3 text-amber-500 shrink-0" />
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {credit.notes && (
                    <p className="text-xs text-neutral-500 mt-2 border-t border-neutral-100 pt-2">
                      {credit.notes}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Optimization tab ──────────────────────────────────────────────────────────

function OptimizationTab({ portfolioId }: { portfolioId: string }) {
  const optimize = useRunOptimization();
  const generateDocs = useGenerateTransferDocs();
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [docPortfolioId, setDocPortfolioId] = useState(portfolioId);
  const [transferForm, setTransferForm] = useState<{
    creditId: string;
    transfereeName: string;
  } | null>(null);

  async function handleOptimize() {
    const id = docPortfolioId.trim() || portfolioId;
    if (!id) return;
    const res = await optimize.mutateAsync(id);
    setResult(res);
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <p className="text-sm text-neutral-600">
          Deterministic optimization model: recommends whether to claim or
          transfer each credit, with timing guidance to maximize portfolio value.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <input
          value={docPortfolioId}
          onChange={(e) => setDocPortfolioId(e.target.value)}
          placeholder="Paste portfolio UUID"
          className="rounded-md border border-neutral-300 px-3 py-2 text-sm w-80 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
        />
        <Button
          onClick={handleOptimize}
          disabled={!docPortfolioId.trim() || optimize.isPending}
        >
          {optimize.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <TrendingUp className="h-4 w-4 mr-2" />
          )}
          Run Optimization
        </Button>
      </div>

      {result && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
            <p className="text-sm text-blue-800">{result.summary}</p>
          </div>

          {/* Value split */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-neutral-500 mb-1">Total Portfolio</div>
                <div className="text-xl font-bold">
                  {formatCreditValue(result.total_value, result.currency)}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-neutral-500 mb-1">
                  Claim Directly
                </div>
                <div className="text-xl font-bold text-green-700">
                  {formatCreditValue(result.claim_value, result.currency)}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4 pb-4">
                <div className="text-xs text-neutral-500 mb-1">
                  Transfer / Monetize
                </div>
                <div className="text-xl font-bold text-blue-700">
                  {formatCreditValue(result.transfer_value, result.currency)}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Action table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                Recommended Actions ({result.actions.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-100">
                      <th className="text-left py-2 pr-4 text-neutral-500 font-medium">
                        Project
                      </th>
                      <th className="text-left py-2 pr-4 text-neutral-500 font-medium">
                        Credit
                      </th>
                      <th className="text-right py-2 pr-4 text-neutral-500 font-medium">
                        Value
                      </th>
                      <th className="text-left py-2 pr-4 text-neutral-500 font-medium">
                        Action
                      </th>
                      <th className="text-left py-2 pr-4 text-neutral-500 font-medium">
                        Timing
                      </th>
                      <th className="text-left py-2 text-neutral-500 font-medium">
                        Reason
                      </th>
                      <th className="w-10" />
                    </tr>
                  </thead>
                  <tbody>
                    {result.actions.map((action: OptimizationAction, i) => (
                      <tr key={i} className="border-b border-neutral-50">
                        <td className="py-3 pr-4 font-medium">
                          {action.project_name}
                        </td>
                        <td className="py-3 pr-4">{action.credit_type}</td>
                        <td className="py-3 pr-4 text-right">
                          {formatCreditValue(action.estimated_value, result.currency)}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant={actionVariant(action.action)}>
                            {action.action}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4 text-neutral-500 text-xs">
                          {action.timing.replace(/_/g, " ")}
                        </td>
                        <td className="py-3 text-xs text-neutral-500 max-w-xs">
                          {action.reason}
                        </td>
                        <td className="py-3 pl-2">
                          {action.action === "transfer" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                setTransferForm({
                                  creditId: action.credit_id,
                                  transfereeName: "",
                                })
                              }
                            >
                              Docs
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Transfer doc modal */}
      {transferForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">
              Generate Transfer Documentation
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Transferee Name
                </label>
                <input
                  value={transferForm.transfereeName}
                  onChange={(e) =>
                    setTransferForm({
                      ...transferForm,
                      transfereeName: e.target.value,
                    })
                  }
                  placeholder="e.g. Acme Capital Fund II LLC"
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button
                variant="outline"
                onClick={() => setTransferForm(null)}
              >
                Cancel
              </Button>
              <Button
                disabled={
                  !transferForm.transfereeName.trim() ||
                  generateDocs.isPending
                }
                onClick={async () => {
                  await generateDocs.mutateAsync({
                    credit_id: transferForm.creditId,
                    transferee_name: transferForm.transfereeName,
                  });
                  setTransferForm(null);
                }}
              >
                {generateDocs.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Generate
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Transfer Docs tab ─────────────────────────────────────────────────────────

function TransferDocsTab() {
  const generateDocs = useGenerateTransferDocs();
  const [form, setForm] = useState({
    credit_id: "",
    transferee_name: "",
    transferee_ein: "",
    transfer_price: "",
  });
  const [submitted, setSubmitted] = useState<{
    report_id: string;
    message: string;
  } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const result = await generateDocs.mutateAsync({
      credit_id: form.credit_id,
      transferee_name: form.transferee_name,
      transferee_ein: form.transferee_ein || undefined,
      transfer_price: form.transfer_price ? Number(form.transfer_price) : undefined,
    });
    setSubmitted(result);
  }

  if (submitted) {
    return (
      <div className="max-w-lg space-y-4">
        <div className="rounded-lg bg-green-50 border border-green-200 p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <h3 className="font-semibold text-green-800">Document Queued</h3>
          </div>
          <p className="text-sm text-green-700">{submitted.message}</p>
          <p className="text-xs text-green-600 mt-1 font-mono">
            Report ID: {submitted.report_id}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => {
            setSubmitted(null);
            setForm({ credit_id: "", transferee_name: "", transferee_ein: "", transfer_price: "" });
          }}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Generate Another
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <p className="text-sm text-neutral-600">
          Generate IRC §6418 transfer election documentation. The document will be
          AI-drafted and must be reviewed by qualified tax counsel before execution.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Tax Credit ID</label>
          <input
            value={form.credit_id}
            onChange={(e) => setForm({ ...form, credit_id: e.target.value })}
            placeholder="Paste tax credit UUID"
            required
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">
            Transferee Name
          </label>
          <input
            value={form.transferee_name}
            onChange={(e) =>
              setForm({ ...form, transferee_name: e.target.value })
            }
            placeholder="e.g. Acme Capital Fund II LLC"
            required
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">
              Transferee EIN (optional)
            </label>
            <input
              value={form.transferee_ein}
              onChange={(e) =>
                setForm({ ...form, transferee_ein: e.target.value })
              }
              placeholder="XX-XXXXXXX"
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">
              Transfer Price (optional)
            </label>
            <input
              type="number"
              value={form.transfer_price}
              onChange={(e) =>
                setForm({ ...form, transfer_price: e.target.value })
              }
              placeholder="USD amount"
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <Button
          type="submit"
          disabled={generateDocs.isPending}
          className="w-full"
        >
          {generateDocs.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <FileText className="h-4 w-4 mr-2" />
          )}
          Generate Transfer Documentation
        </Button>
      </form>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TaxCreditsPage() {
  const [portfolioId, setPortfolioId] = useState("");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">
          Tax Credit Orchestrator
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Identify, optimize, and transfer ITC, PTC, NMTC, and other energy
          tax credits across your portfolio
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="inventory">
        <TabsList>
          <TabsTrigger value="inventory">
            <Receipt className="h-4 w-4 mr-2" />
            Inventory
          </TabsTrigger>
          <TabsTrigger value="identify">
            <Zap className="h-4 w-4 mr-2" />
            Identify
          </TabsTrigger>
          <TabsTrigger value="optimize">
            <TrendingUp className="h-4 w-4 mr-2" />
            Optimize
          </TabsTrigger>
          <TabsTrigger value="transfer-docs">
            <FileText className="h-4 w-4 mr-2" />
            Transfer Docs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="inventory" className="mt-6">
          <InventoryTab
            portfolioId={portfolioId}
            onPortfolioChange={setPortfolioId}
          />
        </TabsContent>
        <TabsContent value="identify" className="mt-6">
          <IdentifyTab />
        </TabsContent>
        <TabsContent value="optimize" className="mt-6">
          <OptimizationTab portfolioId={portfolioId} />
        </TabsContent>
        <TabsContent value="transfer-docs" className="mt-6">
          <TransferDocsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
