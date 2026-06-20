export const CONNECTOR_LABELS: Record<string, string> = {
  sqlite: "SQLite",
  postgresql: "PostgreSQL",
  mysql: "MySQL",
  mssql: "SQL Server",
};

export function formatConnectorLabel(
  connectorType: string,
  displayName?: string,
): string {
  const key = connectorType.toLowerCase();
  if (CONNECTOR_LABELS[key]) {
    return CONNECTOR_LABELS[key];
  }

  const fallback = (displayName || connectorType)
    .replace(/\s+connection$/i, "")
    .trim();
  return fallback || connectorType;
}

export function dataSourceTypeChips(
  connectorType: string,
  dialectName: string,
): { key: string; label: string; muted?: boolean }[] {
  const connector = connectorType.toLowerCase();
  const dialect = dialectName.toLowerCase();
  const chips: { key: string; label: string; muted?: boolean }[] = [
    { key: "connector", label: formatConnectorLabel(connectorType, connectorType) },
  ];

  if (dialect !== connector) {
    chips.push({ key: "dialect", label: dialectName, muted: true });
  }

  return chips;
}
