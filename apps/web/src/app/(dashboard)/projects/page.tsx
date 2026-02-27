"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  SlidersHorizontal,
  Sun,
  Wind,
  Droplets,
  Leaf,
  Flame,
  Battery,
  Atom,
  Network,
  Gauge,
  TreePine,
  Boxes,
  ArrowUpDown,
  TrendingUp,
  DollarSign,
  FolderKanban,
  Target,
} from "lucide-react";
import {
  Button,
  Badge,
  Card,
  CardContent,
  SearchInput,
  EmptyState,
  DataTable,
  type ColumnDef,
  cn,
} from "@scr/ui";
import { useSCRUser, usePermission } from "@/lib/auth";
import {
  useProjects,
  useProjectStats,
  type ProjectResponse,
  type ProjectListParams,
  type ProjectType,
  type ProjectStatus,
  type ProjectStage,
  projectTypeLabel,
  projectStatusColor,
  stageLabel,
  formatCurrency,
} from "@/lib/projects";

// ── Icon map ────────────────────────────────────────────────────────────────

const TYPE_ICONS: Record<ProjectType, React.ElementType> = {
  solar: Sun,
  wind: Wind,
  hydro: Droplets,
  biomass: Leaf,
  geothermal: Flame,
  storage: Battery,
  hydrogen: Atom,
  nuclear: Atom,
  grid: Network,
  efficiency: Gauge,
  carbon_capture: Network,
  nature_based: TreePine,
  other: Boxes,
};

// ── Metric Card ─────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
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
        </div>
      </CardContent>
    </Card>
  );
}

// ── Columns ─────────────────────────────────────────────────────────────────

const columns: ColumnDef<ProjectResponse>[] = [
  {
    accessorKey: "name",
    header: "Project",
    cell: ({ row }) => {
      const project = row.original;
      const Icon = TYPE_ICONS[project.project_type] ?? Boxes;
      return (
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-neutral-100">
            <Icon className="h-4 w-4 text-neutral-600" />
          </div>
          <div className="min-w-0">
            <p className="font-medium text-neutral-900 truncate">
              {project.name}
            </p>
            <p className="text-xs text-neutral-500">
              {projectTypeLabel(project.project_type)}
            </p>
          </div>
        </div>
      );
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={projectStatusColor(row.original.status)}>
        {row.original.status.replace("_", " ")}
      </Badge>
    ),
  },
  {
    accessorKey: "stage",
    header: "Stage",
    cell: ({ row }) => (
      <span className="text-sm text-neutral-600">
        {stageLabel(row.original.stage)}
      </span>
    ),
  },
  {
    accessorKey: "geography_country",
    header: "Geography",
    cell: ({ row }) => (
      <span className="text-sm text-neutral-600">
        {row.original.geography_country}
      </span>
    ),
  },
  {
    accessorKey: "latest_signal_score",
    header: "Signal Score",
    cell: ({ row }) => {
      const score = row.original.latest_signal_score;
      if (score === null) return <span className="text-neutral-400">—</span>;
      const color =
        score >= 80
          ? "text-green-600"
          : score >= 60
            ? "text-amber-600"
            : "text-red-600";
      return <span className={cn("font-semibold", color)}>{score}</span>;
    },
  },
  {
    accessorKey: "total_investment_required",
    header: "Funding",
    cell: ({ row }) => (
      <span className="text-sm font-medium text-neutral-700">
        {formatCurrency(
          row.original.total_investment_required,
          row.original.currency
        )}
      </span>
    ),
  },
];

// ── Status filter options ───────────────────────────────────────────────────

const STATUS_OPTIONS: { label: string; value: ProjectStatus }[] = [
  { label: "Draft", value: "draft" },
  { label: "Active", value: "active" },
  { label: "Fundraising", value: "fundraising" },
  { label: "Funded", value: "funded" },
  { label: "Construction", value: "construction" },
  { label: "Operational", value: "operational" },
];

const TYPE_OPTIONS: { label: string; value: ProjectType }[] = [
  { label: "Solar", value: "solar" },
  { label: "Wind", value: "wind" },
  { label: "Hydro", value: "hydro" },
  { label: "Storage", value: "storage" },
  { label: "Hydrogen", value: "hydrogen" },
  { label: "Biomass", value: "biomass" },
  { label: "Other", value: "other" },
];

const STAGE_OPTIONS: { label: string; value: ProjectStage }[] = [
  { label: "Concept", value: "concept" },
  { label: "Feasibility", value: "feasibility" },
  { label: "Development", value: "development" },
  { label: "Permitting", value: "permitting" },
  { label: "Financing", value: "financing" },
  { label: "Construction", value: "construction" },
  { label: "Operational", value: "operational" },
];

// ── Page ────────────────────────────────────────────────────────────────────

export default function ProjectsPage() {
  const router = useRouter();
  const canCreate = usePermission("create", "project");
  const [params, setParams] = useState<ProjectListParams>({
    page: 1,
    page_size: 20,
    sort_by: "created_at",
    sort_order: "desc",
  });

  const { data: stats } = useProjectStats();
  const { data, isLoading } = useProjects(params);

  const handleSearch = (value: string) => {
    setParams((prev) => ({ ...prev, search: value || undefined, page: 1 }));
  };

  const handleFilter = (key: keyof ProjectListParams, value: string) => {
    setParams((prev) => ({
      ...prev,
      [key]: value || undefined,
      page: 1,
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Projects</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Manage your renewable energy project pipeline
          </p>
        </div>
        {canCreate && (
          <Button onClick={() => router.push("/projects/new")}>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        )}
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Total Projects"
            value={stats.total_projects}
            icon={FolderKanban}
          />
          <MetricCard
            label="Active Fundraising"
            value={stats.active_fundraising}
            icon={TrendingUp}
          />
          <MetricCard
            label="Total Funding Needed"
            value={formatCurrency(stats.total_funding_needed)}
            icon={DollarSign}
          />
          <MetricCard
            label="Avg Signal Score"
            value={stats.avg_signal_score ?? "—"}
            icon={Target}
          />
        </div>
      )}

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          placeholder="Search projects..."
          onValueChange={handleSearch}
          className="w-64"
        />
        <select
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          value={params.status ?? ""}
          onChange={(e) => handleFilter("status", e.target.value)}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          value={params.type ?? ""}
          onChange={(e) => handleFilter("type", e.target.value)}
        >
          <option value="">All types</option>
          {TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-neutral-300 px-3 py-2 text-sm"
          value={params.stage ?? ""}
          onChange={(e) => handleFilter("stage", e.target.value)}
        >
          <option value="">All stages</option>
          {STAGE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      {!data?.items.length && !isLoading ? (
        <EmptyState
          icon={<FolderKanban className="h-12 w-12 text-neutral-400" />}
          title="No projects yet"
          description="Create your first project to get started with your pipeline."
          action={
            canCreate ? (
              <Button onClick={() => router.push("/projects/new")}>
                <Plus className="mr-2 h-4 w-4" />
                New Project
              </Button>
            ) : undefined
          }
        />
      ) : (
        <Card>
          <DataTable
            columns={columns}
            data={data?.items ?? []}
            loading={isLoading}
          />
          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between border-t px-4 py-3">
              <p className="text-sm text-neutral-500">
                Page {data.page} of {data.total_pages} ({data.total} projects)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page <= 1}
                  onClick={() =>
                    setParams((prev) => ({
                      ...prev,
                      page: (prev.page ?? 1) - 1,
                    }))
                  }
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={data.page >= data.total_pages}
                  onClick={() =>
                    setParams((prev) => ({
                      ...prev,
                      page: (prev.page ?? 1) + 1,
                    }))
                  }
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
