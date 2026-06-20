import type { QueryResult } from "@/types/contracts";

export type ResultRecord = Record<string, unknown>;

export function queryResultToRecords(result: QueryResult): ResultRecord[] {
  const columnNames = result.columns.map((column) => column.name);
  return result.rows.map((row) => {
    const record: ResultRecord = {};
    columnNames.forEach((name, index) => {
      record[name] = row[index];
    });
    return record;
  });
}

export function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  return String(value);
}

export function toNumeric(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}
