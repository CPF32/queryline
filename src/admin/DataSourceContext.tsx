import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useParams } from "react-router-dom";
import { getDataSource } from "@/api/client";
import type { DataSource } from "@/types/contracts";

interface DataSourceContextValue {
  dataSource: DataSource | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const DataSourceContext = createContext<DataSourceContextValue | null>(null);

export function DataSourceProvider({ children }: { children: ReactNode }) {
  const { dataSourceId } = useParams<{ dataSourceId: string }>();
  const [dataSource, setDataSource] = useState<DataSource | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!dataSourceId) {
      setDataSource(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const ds = await getDataSource(dataSourceId);
      setDataSource(ds);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data source");
      setDataSource(null);
    } finally {
      setLoading(false);
    }
  }, [dataSourceId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ dataSource, loading, error, refresh }),
    [dataSource, loading, error, refresh],
  );

  return (
    <DataSourceContext.Provider value={value}>{children}</DataSourceContext.Provider>
  );
}

export function useDataSourceContext(): DataSourceContextValue {
  const ctx = useContext(DataSourceContext);
  if (!ctx) {
    return { dataSource: null, loading: false, error: null, refresh: async () => {} };
  }
  return ctx;
}

export function useRequiredDataSourceId(): string {
  const { dataSourceId } = useParams<{ dataSourceId: string }>();
  if (!dataSourceId) throw new Error("dataSourceId route param is required");
  return dataSourceId;
}
