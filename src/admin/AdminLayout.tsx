import { Outlet } from "react-router-dom";
import AppNav from "@/components/AppNav";
import AdminNav from "@/admin/AdminNav";
import AdminSubNav from "@/admin/AdminSubNav";

export default function AdminLayout() {
  return (
    <div className="admin-shell">
      <AppNav brandTo="/" />
      <AdminNav />
      <AdminSubNav />
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
