import { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { QueryColumnMeta } from "@/types/contracts";
import { formatCellValue } from "@/utils/queryData";

const PAGE_SIZE = 25;
const VIRTUALIZE_THRESHOLD = 100;
const ROW_HEIGHT = 40;

export interface DataTableProps {
  columns: QueryColumnMeta[];
  rows: unknown[][];
  truncated: boolean;
  executionMs?: number;
}

export default function DataTable({
  columns,
  rows,
  truncated,
  executionMs,
}: DataTableProps) {
  const [page, setPage] = useState(0);
  const shouldVirtualize = rows.length > VIRTUALIZE_THRESHOLD;
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);

  const visibleRows = useMemo(() => {
    if (shouldVirtualize) {
      return rows;
    }
    const start = safePage * PAGE_SIZE;
    return rows.slice(start, start + PAGE_SIZE);
  }, [rows, safePage, shouldVirtualize]);

  if (columns.length === 0) {
    return null;
  }

  return (
    <div className="data-table">
      <div className="data-table__meta">
        <span>
          {rows.length.toLocaleString()} row{rows.length === 1 ? "" : "s"}
          {truncated ? " (truncated to limit)" : ""}
        </span>
        {executionMs !== undefined && (
          <span>{executionMs.toFixed(1)} ms</span>
        )}
      </div>

      {shouldVirtualize ? (
        <VirtualizedTable columns={columns} rows={visibleRows} />
      ) : (
        <StaticTable columns={columns} rows={visibleRows} />
      )}

      {!shouldVirtualize && pageCount > 1 && (
        <div className="data-table__pagination">
          <button
            type="button"
            className="btn btn--ghost"
            disabled={safePage === 0}
            onClick={() => setPage((current) => Math.max(0, current - 1))}
          >
            Previous
          </button>
          <span>
            Page {safePage + 1} of {pageCount}
          </span>
          <button
            type="button"
            className="btn btn--ghost"
            disabled={safePage >= pageCount - 1}
            onClick={() =>
              setPage((current) => Math.min(pageCount - 1, current + 1))
            }
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function StaticTable({
  columns,
  rows,
}: {
  columns: QueryColumnMeta[];
  rows: unknown[][];
}) {
  return (
    <div className="data-table__scroll">
      <table className="data-table__table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.name}>{column.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column, columnIndex) => (
                <td key={`${rowIndex}-${column.name}`}>
                  {formatCellValue(row[columnIndex])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function VirtualizedTable({
  columns,
  rows,
}: {
  columns: QueryColumnMeta[];
  rows: unknown[][];
}) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });

  return (
    <div
      ref={parentRef}
      className="data-table__scroll data-table__scroll--virtual"
    >
      <table className="data-table__table data-table__table--virtual">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.name}>{column.name}</th>
            ))}
          </tr>
        </thead>
        <tbody
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            position: "relative",
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const row = rows[virtualRow.index];
            return (
              <tr
                key={virtualRow.key}
                className="data-table__virtual-row"
                style={{
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {columns.map((column, columnIndex) => (
                  <td key={`${virtualRow.index}-${column.name}`}>
                    {formatCellValue(row[columnIndex])}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
