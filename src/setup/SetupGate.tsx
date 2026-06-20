import { useCallback, useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { getSetupStatus } from "@/api/client";

export default function SetupGate() {
  const [loading, setLoading] = useState(true);
  const [complete, setComplete] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const status = await getSetupStatus();
      setComplete(status.complete || !status.wizard_required);
    } catch {
      setComplete(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="setup-gate">
        <p className="setup-gate__message">Loading…</p>
      </div>
    );
  }

  if (!complete) {
    return <Navigate to="/setup" replace />;
  }

  return <Outlet />;
}
