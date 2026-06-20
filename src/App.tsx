import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import AppNav from "@/components/AppNav";
import AdminRoute from "@/admin/AdminRoute";
import AdminLayout from "@/admin/AdminLayout";
import AddDataSourceWizard from "@/admin/AddDataSourceWizard";
import DataSourcesPage from "@/admin/DataSourcesPage";
import ExamplesPage from "@/admin/ExamplesPage";
import GlossaryPage from "@/admin/GlossaryPage";
import ImportSchemaFlow from "@/admin/ImportSchemaFlow";
import QueryLogPage from "@/admin/QueryLogPage";
import LlmSettingsPage from "@/admin/LlmSettingsPage";
import SchemaEditorPage from "@/admin/SchemaEditorPage";
import UsersPage from "@/admin/UsersPage";
import { DataSourceProvider } from "@/admin/DataSourceContext";
import SettingsPage from "@/settings/SettingsPage";
import ChatPage from "@/chat/ChatPage";
import SignInPage from "@/auth/SignInPage";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import SetupGate from "@/setup/SetupGate";
import SetupWizard from "@/setup/SetupWizard";
import { SnackbarProvider } from "@/components/snackbar/SnackbarProvider";
import ThemeSync from "@/theme/ThemeSync";

function ChatShell() {
  const { signedOut, user, loading } = useAuth();
  const showSignIn = signedOut || (!loading && !user);

  return (
    <div className="app-shell app-shell--chat">
      <main className={showSignIn ? "app-main app-main--sign-in" : "app-main app-main--chat"}>
        {showSignIn ? (
          <SignInPage />
        ) : (
          <ChatPage />
        )}
      </main>
    </div>
  );
}

function SettingsShell() {
  return (
    <div className="app-shell">
      <AppNav brandTo="/" />
      <main className="app-main settings-main">
        <SettingsPage />
      </main>
    </div>
  );
}

function DataSourceScopedLayout() {
  return (
    <DataSourceProvider>
      <Outlet />
    </DataSourceProvider>
  );
}

function AdminApp() {
  return (
    <AdminRoute>
      <AdminLayout />
    </AdminRoute>
  );
}

export default function App() {
  return (
    <SnackbarProvider>
      <AuthProvider>
        <ThemeSync />
        <Routes>
        <Route path="/setup" element={<SetupWizard />} />
        <Route element={<SetupGate />}>
          <Route path="/" element={<ChatShell />} />
          <Route path="/settings" element={<SettingsShell />} />
          <Route path="/admin" element={<AdminApp />}>
            <Route index element={<DataSourcesPage />} />
            <Route path="llm-settings" element={<LlmSettingsPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="data-sources/new" element={<AddDataSourceWizard />} />
            <Route path="data-sources/:dataSourceId" element={<DataSourceScopedLayout />}>
              <Route path="schema/import" element={<ImportSchemaFlow />} />
              <Route path="schema" element={<SchemaEditorPage />} />
              <Route path="glossary" element={<GlossaryPage />} />
              <Route path="examples" element={<ExamplesPage />} />
              <Route path="query-log" element={<QueryLogPage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </SnackbarProvider>
  );
}
