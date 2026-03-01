"use client";

import { Badge, Card, CardContent, DataTable, EmptyState, type ColumnDef } from "@scr/ui";
import { Activity } from "lucide-react";
import { usePortfolioDashboard } from "@/lib/monitoring";

interface ProjectSummaryRow {
  project_id: string;
  project_name: string;
  compliant: number;
  warning: number;
  breach: number;
  traffic_light: string;
}

const TRAFFIC_LIGHT_VARIANT: Record<
  string,
  "success" | "warning" | "error" | "neutral"
> = {
  green: "success",
  amber: "warning",
  red: "error",
};

const TRAFFIC_LIGHT_LABEL: Record<string, string> = {
  green: "OK",
  amber: "Warning",
  red: "Breach",
};

export default function MonitoringPage() {
  const { data, isLoading } = usePortfolioDashboard();

  const summaries = data?.project_summaries ?? [];

  const totalProjects = summaries.length;
  const totalOk = summaries.filter((s) => s.traffic_light === "green").length;
  const totalWarning = summaries.filter(
    (s) => s.traffic_light === "amber"
  ).length;
  const totalBreach = summaries.filter((s) => s.traffic_light === "red").length;

  const columns: ColumnDef<ProjectSummaryRow>[] = [
    {
      accessorKey: "project_name",
      header: "Project",
      cell: ({ row }) => (
        <span className="font-medium text-sm text-neutral-900">
          {row.original.project_name}
        </span>
      ),
    },
    {
      accessorKey: "compliant",
      header: "Compliant",
      cell: ({ row }) => (
        <span className="text-sm text-neutral-700">{row.original.compliant}</span>
      ),
    },
    {
      accessorKey: "warning",
      header: "Warning",
      cell: ({ row }) => (
        <span className="text-sm text-neutral-700">{row.original.warning}</span>
      ),
    },
    {
      accessorKey: "breach",
      header: "Breach",
      cell: ({ row }) => (
        <span className="text-sm text-neutral-700">{row.original.breach}</span>
      ),
    },
    {
      accessorKey: "traffic_light",
      header: "Status",
      cell: ({ row }) => {
        const tl = row.original.traffic_light;
        return (
          <Badge variant={TRAFFIC_LIGHT_VARIANT[tl] ?? "neutral"}>
            {TRAFFIC_LIGHT_LABEL[tl] ?? tl}
          </Badge>
        );
      },
    },
  ];

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">
          Portfolio Monitoring
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          Covenant compliance and KPI tracking across all portfolio projects.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="p-5">
            <p className="text-xs font-medium text-neutral-500 mb-1">
              Projects Monitored
            </p>
            <p className="text-2xl font-bold text-neutral-900">
              {isLoading ? "—" : totalProjects}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs font-medium text-neutral-500 mb-1">
              Covenants OK
            </p>
            <p className="text-2xl font-bold text-green-600">
              {isLoading ? "—" : totalOk}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs font-medium text-neutral-500 mb-1">
              Warnings
            </p>
            <p className="text-2xl font-bold text-amber-600">
              {isLoading ? "—" : totalWarning}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs font-medium text-neutral-500 mb-1">
              Breaches
            </p>
            <p className="text-2xl font-bold text-red-600">
              {isLoading ? "—" : totalBreach}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Traffic light table */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-base font-semibold text-neutral-900 mb-4">
            Project Covenant Status
          </h2>
          {isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
          ) : summaries.length === 0 ? (
            <EmptyState
              icon={<Activity className="h-10 w-10 text-neutral-300" />}
              title="No monitoring data"
              description="Add covenants to projects to begin portfolio monitoring."
            />
          ) : (
            <DataTable columns={columns} data={summaries} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
