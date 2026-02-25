"use client";

import * as React from "react";
import { ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  TableWrapper,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

// ─── Types ────────────────────────────────────────────────────────────────────

export type SortDirection = "asc" | "desc" | null;

export interface ColumnDef<TData> {
  /** Unique key for the column, used as accessor into TData */
  key: keyof TData | string;
  /** Column header label */
  header: string;
  /** Whether this column is sortable */
  sortable?: boolean;
  /** Custom cell renderer. Receives the row and returns a ReactNode. */
  cell?: (row: TData) => React.ReactNode;
  /** Optional className for the <td> cell */
  cellClassName?: string;
  /** Optional className for the <th> header */
  headerClassName?: string;
}

export interface SortState {
  key: string;
  direction: SortDirection;
}

export interface DataTableProps<TData> {
  /** Column definitions */
  columns: ColumnDef<TData>[];
  /** Row data */
  data: TData[];
  /** Whether data is loading — shows skeleton rows */
  loading?: boolean;
  /** Number of skeleton rows to show while loading */
  skeletonRows?: number;
  /** Current sort state */
  sortState?: SortState;
  /** Called when a sortable column header is clicked */
  onSort?: (key: string, direction: SortDirection) => void;
  /** A unique key field on TData for React reconciliation */
  rowKey: keyof TData;
  /** Optional row click handler */
  onRowClick?: (row: TData) => void;
  /** Message to show when data is empty */
  emptyMessage?: string;
  className?: string;
}

// ─── Sort Icon ────────────────────────────────────────────────────────────────

function SortIcon({ columnKey, sortState }: { columnKey: string; sortState?: SortState }) {
  if (!sortState || sortState.key !== columnKey) {
    return <ArrowUpDown className="ml-1.5 h-3.5 w-3.5 opacity-40" />;
  }
  if (sortState.direction === "asc") {
    return <ArrowUp className="ml-1.5 h-3.5 w-3.5 text-primary-600" />;
  }
  return <ArrowDown className="ml-1.5 h-3.5 w-3.5 text-primary-600" />;
}

// ─── Skeleton Rows ────────────────────────────────────────────────────────────

function SkeletonRows({ columns, rows }: { columns: number; rows: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <TableRow key={rowIdx} className="hover:bg-transparent">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <TableCell key={colIdx}>
              <Skeleton className={cn("h-4", colIdx === 0 ? "w-32" : "w-24")} />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

// ─── DataTable ────────────────────────────────────────────────────────────────

export function DataTable<TData extends Record<string, unknown>>({
  columns,
  data,
  loading = false,
  skeletonRows = 5,
  sortState,
  onSort,
  rowKey,
  onRowClick,
  emptyMessage = "Sin resultados",
  className,
}: DataTableProps<TData>) {
  function handleHeaderClick(column: ColumnDef<TData>) {
    if (!column.sortable || !onSort) return;

    const key = String(column.key);
    let nextDirection: SortDirection;

    if (!sortState || sortState.key !== key) {
      nextDirection = "asc";
    } else if (sortState.direction === "asc") {
      nextDirection = "desc";
    } else {
      nextDirection = null;
    }

    onSort(key, nextDirection);
  }

  function getCellValue(row: TData, column: ColumnDef<TData>): React.ReactNode {
    if (column.cell) return column.cell(row);
    const val = row[column.key as keyof TData];
    if (val === null || val === undefined) return "—";
    return String(val);
  }

  const isEmpty = !loading && data.length === 0;

  return (
    <TableWrapper className={className}>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {columns.map((column) => (
              <TableHead
                key={String(column.key)}
                className={cn(
                  column.sortable && onSort && "cursor-pointer select-none",
                  column.headerClassName,
                )}
                onClick={() => handleHeaderClick(column)}
                aria-sort={
                  sortState?.key === String(column.key)
                    ? sortState.direction === "asc"
                      ? "ascending"
                      : "descending"
                    : undefined
                }
              >
                <div className="flex items-center">
                  {column.header}
                  {column.sortable && onSort && (
                    <SortIcon columnKey={String(column.key)} sortState={sortState} />
                  )}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>

        <TableBody>
          {loading ? (
            <SkeletonRows columns={columns.length} rows={skeletonRows} />
          ) : isEmpty ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={columns.length}
                className="h-32 text-center text-[hsl(var(--muted-foreground))]"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            data.map((row) => (
              <TableRow
                key={String(row[rowKey])}
                onClick={() => onRowClick?.(row)}
                className={cn(onRowClick && "cursor-pointer")}
              >
                {columns.map((column) => (
                  <TableCell key={String(column.key)} className={column.cellClassName}>
                    {getCellValue(row, column)}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </TableWrapper>
  );
}
