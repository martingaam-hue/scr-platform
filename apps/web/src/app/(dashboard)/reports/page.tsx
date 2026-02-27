"use client";

import { useState } from "react";
import {
  BarChart3,
  Calendar,
  Clock,
  Download,
  FileText,
  Loader2,
  Plus,
  Trash2,
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
import { usePermission } from "@/lib/auth";
import {
  useReportTemplates,
  useReports,
  useSchedules,
  useDeleteReport,
  useDeleteSchedule,
  type ReportTemplateResponse,
  type GeneratedReportResponse,
  type ScheduledReportResponse,
  type ReportCategory,
  reportStatusColor,
  reportCategoryLabel,
  frequencyLabel,
  formatLabel,
  type OutputFormat,
} from "@/lib/reports";
import { GenerateDialog } from "@/components/reports/generate-dialog";

// ── Category filter ────────────────────────────────────────────────────────

const CATEGORIES: { value: ReportCategory | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "performance", label: "Performance" },
  { value: "esg", label: "ESG" },
  { value: "compliance", label: "Compliance" },
  { value: "portfolio", label: "Portfolio" },
  { value: "project", label: "Project" },
];

// ── Template card ──────────────────────────────────────────────────────────

function TemplateCard({
  template,
  canGenerate,
  onGenerate,
}: {
  template: ReportTemplateResponse;
  canGenerate: boolean;
  onGenerate: () => void;
}) {
  const formats = (template.template_config?.supported_formats as string[]) ?? [];
  const audience = template.template_config?.audience as string | undefined;

  return (
    <Card className="flex h-full flex-col">
      <CardContent className="flex flex-1 flex-col p-5">
        <div className="mb-2 flex items-center gap-2">
          <Badge variant="info">{reportCategoryLabel(template.category)}</Badge>
          {template.is_system && (
            <Badge variant="neutral">System</Badge>
          )}
          {audience && (
            <Badge variant="neutral" className="capitalize">
              {audience}
            </Badge>
          )}
        </div>
        <h3 className="text-base font-semibold text-neutral-900">
          {template.name}
        </h3>
        <p className="mt-1 flex-1 text-sm text-neutral-500 line-clamp-2">
          {template.description}
        </p>
        <div className="mt-3 flex items-center justify-between">
          <div className="flex gap-1">
            {formats.map((f) => (
              <span
                key={f}
                className="rounded bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-neutral-500"
              >
                {f}
              </span>
            ))}
          </div>
          {canGenerate && (
            <Button size="sm" onClick={onGenerate}>
              Generate
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Reports table columns ──────────────────────────────────────────────────

const reportColumns: ColumnDef<GeneratedReportResponse, unknown>[] = [
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <span className="font-medium text-neutral-900">{row.original.title}</span>
    ),
  },
  {
    accessorKey: "template_name",
    header: "Template",
    cell: ({ row }) => row.original.template_name ?? "—",
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={reportStatusColor(row.original.status)}>
        {row.original.status}
      </Badge>
    ),
  },
  {
    id: "format",
    header: "Format",
    cell: ({ row }) => {
      const fmt = row.original.parameters?.output_format as OutputFormat | undefined;
      return fmt ? formatLabel(fmt) : "—";
    },
  },
  {
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => new Date(row.original.created_at).toLocaleDateString(),
  },
];

// ── Schedules table columns ────────────────────────────────────────────────

const scheduleColumns: ColumnDef<ScheduledReportResponse, unknown>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium text-neutral-900">{row.original.name}</span>
    ),
  },
  {
    accessorKey: "template_name",
    header: "Template",
    cell: ({ row }) => row.original.template_name ?? "—",
  },
  {
    accessorKey: "frequency",
    header: "Frequency",
    cell: ({ row }) => (
      <Badge variant="info">{frequencyLabel(row.original.frequency)}</Badge>
    ),
  },
  {
    accessorKey: "is_active",
    header: "Active",
    cell: ({ row }) => (
      <Badge variant={row.original.is_active ? "success" : "neutral"}>
        {row.original.is_active ? "Active" : "Inactive"}
      </Badge>
    ),
  },
  {
    accessorKey: "last_run_at",
    header: "Last Run",
    cell: ({ row }) =>
      row.original.last_run_at
        ? new Date(row.original.last_run_at).toLocaleDateString()
        : "Never",
  },
  {
    accessorKey: "next_run_at",
    header: "Next Run",
    cell: ({ row }) =>
      row.original.next_run_at
        ? new Date(row.original.next_run_at).toLocaleDateString()
        : "—",
  },
];

// ── Page component ─────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState("templates");
  const [categoryFilter, setCategoryFilter] = useState<ReportCategory | "all">("all");
  const [page, setPage] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplateResponse | null>(null);
  const [generateOpen, setGenerateOpen] = useState(false);

  const canCreate = usePermission("create", "report");
  const canDelete = usePermission("delete", "report");

  // Queries
  const category = categoryFilter === "all" ? undefined : categoryFilter;
  const { data: templatesData, isLoading: templatesLoading } = useReportTemplates(category);
  const { data: reportsData, isLoading: reportsLoading } = useReports({
    page,
    page_size: 20,
  });
  const { data: schedulesData, isLoading: schedulesLoading } = useSchedules();
  const deleteMutation = useDeleteReport();
  const deleteScheduleMutation = useDeleteSchedule();

  // Poll when reports are pending
  const hasPending = reportsData?.items.some(
    (r) => r.status === "queued" || r.status === "generating"
  );

  // Add actions column to reports
  const reportColumnsWithActions: ColumnDef<GeneratedReportResponse, unknown>[] = [
    ...reportColumns,
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          {row.original.download_url && (
            <a
              href={row.original.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
            >
              <Download className="h-4 w-4" />
            </a>
          )}
          {canDelete && (
            <button
              onClick={() => deleteMutation.mutate(row.original.id)}
              className="rounded-md p-1.5 text-neutral-400 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      ),
    },
  ];

  // Add actions column to schedules
  const scheduleColumnsWithActions: ColumnDef<ScheduledReportResponse, unknown>[] = [
    ...scheduleColumns,
    {
      id: "actions",
      header: "",
      cell: ({ row }) =>
        canDelete ? (
          <button
            onClick={() => deleteScheduleMutation.mutate(row.original.id)}
            className="rounded-md p-1.5 text-neutral-400 hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        ) : null,
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Reports</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Generate, view, and schedule reports
          </p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="templates">
            <FileText className="mr-1.5 h-4 w-4" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="reports">
            <BarChart3 className="mr-1.5 h-4 w-4" />
            Generated
            {reportsData && reportsData.total > 0 && (
              <span className="ml-1.5 rounded-full bg-neutral-200 px-1.5 text-[10px] font-bold">
                {reportsData.total}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="schedules">
            <Calendar className="mr-1.5 h-4 w-4" />
            Scheduled
          </TabsTrigger>
        </TabsList>

        {/* Templates tab */}
        <TabsContent value="templates" className="mt-4">
          {/* Category filter */}
          <div className="mb-4 flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setCategoryFilter(cat.value)}
                className={cn(
                  "rounded-full px-3 py-1 text-sm font-medium transition-colors",
                  categoryFilter === cat.value
                    ? "bg-primary-100 text-primary-700"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {templatesLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
            </div>
          ) : !templatesData?.items.length ? (
            <EmptyState
              icon={<FileText className="h-8 w-8" />}
              title="No templates found"
              description="No report templates match the selected category."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {templatesData.items.map((tmpl) => (
                <TemplateCard
                  key={tmpl.id}
                  template={tmpl}
                  canGenerate={canCreate}
                  onGenerate={() => {
                    setSelectedTemplate(tmpl);
                    setGenerateOpen(true);
                  }}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* Generated reports tab */}
        <TabsContent value="reports" className="mt-4">
          {reportsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
            </div>
          ) : !reportsData?.items.length ? (
            <EmptyState
              icon={<BarChart3 className="h-8 w-8" />}
              title="No reports generated"
              description="Generate a report from the Templates tab to get started."
            />
          ) : (
            <DataTable
              columns={reportColumnsWithActions}
              data={reportsData.items}
              pagination={{
                page: reportsData.page,
                limit: reportsData.page_size,
                total: reportsData.total,
              }}
              onPaginationChange={(newPage) => setPage(newPage)}
            />
          )}

          {hasPending && (
            <p className="mt-3 flex items-center gap-2 text-sm text-neutral-500">
              <Clock className="h-4 w-4 animate-pulse" />
              Some reports are still generating. Refresh to see updates.
            </p>
          )}
        </TabsContent>

        {/* Schedules tab */}
        <TabsContent value="schedules" className="mt-4">
          {schedulesLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
            </div>
          ) : !schedulesData?.items.length ? (
            <EmptyState
              icon={<Calendar className="h-8 w-8" />}
              title="No scheduled reports"
              description="Set up recurring report generation from the API."
            />
          ) : (
            <DataTable
              columns={scheduleColumnsWithActions}
              data={schedulesData.items}
            />
          )}
        </TabsContent>
      </Tabs>

      {/* Generate dialog */}
      {selectedTemplate && (
        <GenerateDialog
          template={selectedTemplate}
          open={generateOpen}
          onOpenChange={(open) => {
            setGenerateOpen(open);
            if (!open) setSelectedTemplate(null);
          }}
        />
      )}
    </div>
  );
}
