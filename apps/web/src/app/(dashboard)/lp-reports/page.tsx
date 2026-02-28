"use client";

import { useState } from "react";
import {
  BarChart3,
  Calendar,
  CheckCircle,
  Download,
  FileText,
  Loader2,
  Plus,
  TrendingUp,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  DataTable,
  EmptyState,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  type ColumnDef,
  cn,
} from "@scr/ui";
import {
  useLPReports,
  useCreateLPReport,
  useApproveLPReport,
  useGenerateLPReportPDF,
  formatMultiple,
  formatIRR,
  lpReportStatusColor,
  type LPReport,
  type CreateLPReportRequest,
} from "@/lib/lp-reports";

// ── Metric Card ─────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  icon: Icon,
  highlight,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  highlight?: boolean;
}) {
  return (
    <Card className={cn(highlight && "border-indigo-200 bg-indigo-50/50")}>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={cn("p-2 rounded-lg", highlight ? "bg-indigo-100" : "bg-gray-100")}>
            <Icon className={cn("h-4 w-4", highlight ? "text-indigo-600" : "text-gray-600")} />
          </div>
          <div>
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-lg font-semibold text-gray-900">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Create Report Modal ──────────────────────────────────────────────────────

function CreateReportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { mutate: create, isPending } = useCreateLPReport();
  const [form, setForm] = useState<Partial<CreateLPReportRequest>>({
    report_period: "",
    period_start: "",
    period_end: "",
    total_committed: undefined,
    total_invested: undefined,
    total_returned: undefined,
    total_nav: undefined,
  });

  if (!open) return null;

  const handleSubmit = () => {
    if (!form.report_period || !form.period_start || !form.period_end) return;
    create(
      {
        report_period: form.report_period!,
        period_start: form.period_start!,
        period_end: form.period_end!,
        total_committed: form.total_committed ?? null,
        total_invested: form.total_invested ?? null,
        total_returned: form.total_returned ?? null,
        total_nav: form.total_nav ?? null,
      },
      { onSuccess: onClose }
    );
  };

  const field = (key: keyof typeof form, label: string, type: string = "text") => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={(form[key] as string | number | undefined) ?? ""}
        onChange={(e) =>
          setForm((f) => ({
            ...f,
            [key]: type === "number" ? (e.target.value ? parseFloat(e.target.value) : undefined) : e.target.value,
          }))
        }
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">New LP Report</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        {field("report_period", "Report Period (e.g. Q1 2025)")}
        {field("period_start", "Period Start", "date")}
        {field("period_end", "Period End", "date")}
        <div className="border-t pt-4 grid grid-cols-2 gap-3">
          {field("total_committed", "Total Committed (€)", "number")}
          {field("total_invested", "Total Invested (€)", "number")}
          {field("total_returned", "Total Returned (€)", "number")}
          {field("total_nav", "Total NAV (€)", "number")}
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={isPending}>
            {isPending && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            Generate Report
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Report Row Actions ───────────────────────────────────────────────────────

function ReportActions({ report }: { report: LPReport }) {
  const { mutate: approve, isPending: approving } = useApproveLPReport();
  const { mutate: generatePDF, isPending: generating } = useGenerateLPReportPDF();

  return (
    <div className="flex items-center gap-2">
      {report.status === "draft" && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => approve(report.id)}
          disabled={approving}
        >
          {approving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3 mr-1" />}
          Approve
        </Button>
      )}
      {report.status !== "draft" && !report.pdf_s3_key && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => generatePDF(report.id)}
          disabled={generating}
        >
          {generating ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileText className="h-3 w-3 mr-1" />}
          Generate PDF
        </Button>
      )}
      {report.download_url && (
        <Button size="sm" variant="outline" asChild>
          <a href={report.download_url} target="_blank" rel="noreferrer">
            <Download className="h-3 w-3 mr-1" />
            Download
          </a>
        </Button>
      )}
    </div>
  );
}

// ── Columns ──────────────────────────────────────────────────────────────────

const columns: ColumnDef<LPReport>[] = [
  {
    accessorKey: "report_period",
    header: "Period",
    cell: ({ row }) => (
      <span className="font-medium text-gray-900">{row.original.report_period}</span>
    ),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={lpReportStatusColor(row.original.status) as "success" | "neutral" | "info"}>
        {row.original.status}
      </Badge>
    ),
  },
  {
    id: "irr",
    header: "Net IRR",
    cell: ({ row }) => <span className="tabular-nums">{formatIRR(row.original.net_irr)}</span>,
  },
  {
    id: "tvpi",
    header: "TVPI",
    cell: ({ row }) => <span className="tabular-nums">{formatMultiple(row.original.tvpi)}</span>,
  },
  {
    id: "dpi",
    header: "DPI",
    cell: ({ row }) => <span className="tabular-nums">{formatMultiple(row.original.dpi)}</span>,
  },
  {
    id: "moic",
    header: "MOIC",
    cell: ({ row }) => <span className="tabular-nums">{formatMultiple(row.original.moic)}</span>,
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => (
      <span className="text-sm text-gray-500">
        {new Date(row.original.created_at).toLocaleDateString()}
      </span>
    ),
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => <ReportActions report={row.original} />,
  },
];

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LPReportsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState("all");

  const { data: allData, isLoading } = useLPReports();
  const { data: draftData } = useLPReports({ status: "draft" });
  const { data: approvedData } = useLPReports({ status: "approved" });

  const reports = allData?.items ?? [];
  const latestApproved = approvedData?.items?.[0];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">LP Reports</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Quarterly investor reporting with AI-generated narrative sections
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Report
        </Button>
      </div>

      {/* KPI bar */}
      {latestApproved && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MetricCard
            label="Net IRR"
            value={formatIRR(latestApproved.net_irr)}
            icon={TrendingUp}
            highlight
          />
          <MetricCard
            label="TVPI"
            value={formatMultiple(latestApproved.tvpi)}
            icon={BarChart3}
          />
          <MetricCard
            label="DPI"
            value={formatMultiple(latestApproved.dpi)}
            icon={TrendingUp}
          />
          <MetricCard
            label="MOIC"
            value={formatMultiple(latestApproved.moic)}
            icon={BarChart3}
          />
        </div>
      )}

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Tabs value={tab} onValueChange={setTab}>
            <div className="px-4 pt-4">
              <TabsList>
                <TabsTrigger value="all">
                  All ({allData?.total ?? 0})
                </TabsTrigger>
                <TabsTrigger value="draft">
                  Draft ({draftData?.total ?? 0})
                </TabsTrigger>
                <TabsTrigger value="approved">
                  Approved ({approvedData?.total ?? 0})
                </TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="all" className="mt-0">
              {isLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : reports.length === 0 ? (
                <EmptyState
                  title="No LP reports yet"
                  description="Create your first LP report to share performance metrics and AI-generated narrative with your investors."
                  action={<Button onClick={() => setShowCreate(true)}>New Report</Button>}
                />
              ) : (
                <DataTable columns={columns} data={reports} />
              )}
            </TabsContent>
            <TabsContent value="draft" className="mt-0">
              <DataTable columns={columns} data={draftData?.items ?? []} />
            </TabsContent>
            <TabsContent value="approved" className="mt-0">
              <DataTable columns={columns} data={approvedData?.items ?? []} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <CreateReportModal open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}
