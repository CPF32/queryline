import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { LoadingState } from "@/admin/AdminUi";

export default function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading, signedOut } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingState message="Checking access…" />;
  }

  if (signedOut || !user) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  if (!user.is_admin) {
    return <Navigate to="/settings" replace />;
  }

  return children;
}
