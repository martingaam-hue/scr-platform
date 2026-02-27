"use client";

import * as React from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type ExpandedState,
  type Row,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronDown,
  ChevronRight,
  Download,
  Columns3,
  Loader2,
} from "lucide-react";
import { cn } from "../lib/utils";

// ── Types ───────────────────────────────────────────────────────────────

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
}

export interface DataTableProps<TData> {
  columns: ColumnDef<TData, unknown>[];
  data: TData[];
  pagination?: PaginationState;
  onPaginationChange?: (page: number, limit: number) => void;
  sorting?: SortingState;
  onSortingChange?: (updater: SortingState | ((prev: SortingState) => SortingState)) => void;
  enableRowSelection?: boolean;
  enableMultiRowSelection?: boolean;
  onRowSelectionChange?: (rows: TData[]) => void;
  bulkActions?: React.ReactNode;
  enableColumnVisibility?: boolean;
  enableExport?: boolean;
  onExport?: () => void;
  loading?: boolean;
  emptyState?: React.ReactNode;
  renderExpandedRow?: (row: Row<TData>) => React.ReactNode;
  getRowId?: (row: TData) => string;
  className?: string;
}

// ── Component ───────────────────────────────────────────────────────────

function DataTable<TData>({
  columns,
  data,
  pagination,
  onPaginationChange,
  sorting: externalSorting,
  onSortingChange,
  enableRowSelection = false,
  enableMultiRowSelection = true,
  onRowSelectionChange,
  bulkActions,
  enableColumnVisibility = false,
  enableExport = false,
  onExport,
  loading = false,
  emptyState,
  renderExpandedRow,
  getRowId,
  className,
}: DataTableProps<TData>) {
  const [internalSorting, setInternalSorting] = React.useState<SortingState>(
    []
  );
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({});
  const [expanded, setExpanded] = React.useState<ExpandedState>({});
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});
  const [colMenuOpen, setColMenuOpen] = React.useState(false);

  const sorting = externalSorting ?? internalSorting;

  const selectionColumn: ColumnDef<TData, unknown> | null = enableRowSelection
    ? {
        id: "_select",
        header: ({ table }) => (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-neutral-300 text-primary-600"
            checked={table.getIsAllPageRowsSelected()}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-neutral-300 text-primary-600"
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
          />
        ),
        size: 40,
        enableSorting: false,
      }
    : null;

  const expandColumn: ColumnDef<TData, unknown> | null = renderExpandedRow
    ? {
        id: "_expand",
        header: () => null,
        cell: ({ row }) => (
          <button
            type="button"
            onClick={row.getToggleExpandedHandler()}
            className="p-0.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
          >
            {row.getIsExpanded() ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        ),
        size: 32,
        enableSorting: false,
      }
    : null;

  const allColumns = [
    ...(expandColumn ? [expandColumn] : []),
    ...(selectionColumn ? [selectionColumn] : []),
    ...columns,
  ];

  const table = useReactTable({
    data,
    columns: allColumns,
    state: { sorting, rowSelection, expanded, columnVisibility },
    onSortingChange: onSortingChange ?? setInternalSorting,
    onRowSelectionChange: setRowSelection,
    onExpandedChange: setExpanded,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: onSortingChange ? undefined : getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    enableRowSelection,
    enableMultiRowSelection,
    getRowId,
    manualSorting: !!onSortingChange,
    manualPagination: true,
    rowCount: pagination?.total,
  });

  // Report selection changes
  React.useEffect(() => {
    if (onRowSelectionChange) {
      const selected = table
        .getSelectedRowModel()
        .rows.map((r) => r.original);
      onRowSelectionChange(selected);
    }
  }, [rowSelection]);

  const selectedCount = Object.keys(rowSelection).length;
  const totalPages = pagination
    ? Math.ceil(pagination.total / pagination.limit)
    : 1;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Toolbar */}
      {(enableColumnVisibility || enableExport || (selectedCount > 0 && bulkActions)) && (
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {selectedCount > 0 && (
              <span className="text-sm text-neutral-500">
                {selectedCount} selected
              </span>
            )}
            {selectedCount > 0 && bulkActions}
          </div>
          <div className="flex items-center gap-2">
            {enableColumnVisibility && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setColMenuOpen(!colMenuOpen)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
                >
                  <Columns3 className="h-3.5 w-3.5" />
                  Columns
                </button>
                {colMenuOpen && (
                  <div className="absolute right-0 z-20 mt-1 w-48 rounded-md border border-neutral-200 bg-white py-1 shadow-lg dark:border-neutral-700 dark:bg-neutral-800">
                    {table.getAllLeafColumns().map((col) => {
                      if (col.id.startsWith("_")) return null;
                      return (
                        <label
                          key={col.id}
                          className="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-700"
                        >
                          <input
                            type="checkbox"
                            className="h-3.5 w-3.5 rounded border-neutral-300"
                            checked={col.getIsVisible()}
                            onChange={col.getToggleVisibilityHandler()}
                          />
                          {typeof col.columnDef.header === "string"
                            ? col.columnDef.header
                            : col.id}
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
            {enableExport && (
              <button
                type="button"
                onClick={onExport}
                className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
              >
                <Download className="h-3.5 w-3.5" />
                Export
              </button>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr
                key={headerGroup.id}
                className="border-b border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-800/50"
              >
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400"
                    style={{
                      width:
                        header.getSize() !== 150
                          ? header.getSize()
                          : undefined,
                    }}
                  >
                    {header.isPlaceholder ? null : header.column.getCanSort() ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 hover:text-neutral-900 dark:hover:text-neutral-100"
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getIsSorted() === "asc" ? (
                          <ArrowUp className="h-3.5 w-3.5" />
                        ) : header.column.getIsSorted() === "desc" ? (
                          <ArrowDown className="h-3.5 w-3.5" />
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5 opacity-40" />
                        )}
                      </button>
                    ) : (
                      flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td
                  colSpan={allColumns.length}
                  className="px-4 py-16 text-center"
                >
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-neutral-400" />
                </td>
              </tr>
            ) : table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={allColumns.length}
                  className="px-4 py-16 text-center"
                >
                  {emptyState || (
                    <p className="text-sm text-neutral-400">No results found</p>
                  )}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <React.Fragment key={row.id}>
                  <tr className="border-b border-neutral-100 transition-colors hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-800/30">
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className="px-4 py-3 text-neutral-700 dark:text-neutral-300"
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                  {row.getIsExpanded() && renderExpandedRow && (
                    <tr className="bg-neutral-50/50 dark:bg-neutral-800/20">
                      <td colSpan={allColumns.length} className="px-4 py-4">
                        {renderExpandedRow(row)}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && (
        <div className="flex items-center justify-between text-sm text-neutral-500">
          <span>
            {pagination.total === 0
              ? "No results"
              : `${(pagination.page - 1) * pagination.limit + 1}–${Math.min(pagination.page * pagination.limit, pagination.total)} of ${pagination.total}`}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={pagination.page <= 1}
              onClick={() =>
                onPaginationChange?.(pagination.page - 1, pagination.limit)
              }
              className="rounded-md px-3 py-1.5 hover:bg-neutral-100 disabled:opacity-40 dark:hover:bg-neutral-800"
            >
              Previous
            </button>
            <span className="px-2 tabular-nums">
              {pagination.page} / {totalPages || 1}
            </span>
            <button
              type="button"
              disabled={pagination.page >= totalPages}
              onClick={() =>
                onPaginationChange?.(pagination.page + 1, pagination.limit)
              }
              className="rounded-md px-3 py-1.5 hover:bg-neutral-100 disabled:opacity-40 dark:hover:bg-neutral-800"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export { DataTable };
export type { ColumnDef, SortingState, Row };
