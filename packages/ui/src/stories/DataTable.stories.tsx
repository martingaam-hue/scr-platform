import type { Meta, StoryObj } from "@storybook/react";
import { DataTable } from "../components/data-table";
import { Badge } from "../components/badge";
import { ScoreBadge } from "../components/badge";
import type { ColumnDef } from "@tanstack/react-table";

type Project = {
  id: string;
  name: string;
  status: string;
  score: number;
  aum: number;
  sector: string;
};

const sampleData: Project[] = [
  { id: "1", name: "Solar Farm Alpha", status: "active", score: 87, aum: 12500000, sector: "Solar" },
  { id: "2", name: "Wind Park Beta", status: "review", score: 72, aum: 8200000, sector: "Wind" },
  { id: "3", name: "EV Charging Net", status: "active", score: 65, aum: 4100000, sector: "Transport" },
  { id: "4", name: "Green H2 Plant", status: "draft", score: 45, aum: 0, sector: "Hydrogen" },
  { id: "5", name: "Reforestation X", status: "active", score: 91, aum: 6700000, sector: "Nature" },
];

const columns: ColumnDef<Project, unknown>[] = [
  { accessorKey: "name", header: "Project Name", enableSorting: true },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ getValue }) => {
      const s = getValue() as string;
      const variant = s === "active" ? "success" : s === "review" ? "warning" : "neutral";
      return <Badge variant={variant}>{s}</Badge>;
    },
  },
  {
    accessorKey: "score",
    header: "Score",
    enableSorting: true,
    cell: ({ getValue }) => <ScoreBadge score={getValue() as number} />,
  },
  {
    accessorKey: "aum",
    header: "AUM",
    enableSorting: true,
    cell: ({ getValue }) => {
      const v = getValue() as number;
      return v > 0 ? `$${(v / 1_000_000).toFixed(1)}M` : "—";
    },
  },
  { accessorKey: "sector", header: "Sector" },
];

const meta: Meta<typeof DataTable<Project>> = {
  title: "Components/DataTable",
  component: DataTable,
};
export default meta;

export const Default: StoryObj = {
  render: () => <DataTable columns={columns} data={sampleData} />,
};

export const WithPagination: StoryObj = {
  render: () => (
    <DataTable
      columns={columns}
      data={sampleData}
      pagination={{ page: 1, limit: 10, total: 42 }}
    />
  ),
};

export const WithSelection: StoryObj = {
  render: () => (
    <DataTable
      columns={columns}
      data={sampleData}
      enableRowSelection
      enableColumnVisibility
      enableExport
      getRowId={(row) => row.id}
    />
  ),
};

export const Loading: StoryObj = {
  render: () => <DataTable columns={columns} data={[]} loading />,
};

export const Empty: StoryObj = {
  render: () => <DataTable columns={columns} data={[]} />,
};
