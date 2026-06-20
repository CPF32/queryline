import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { fetchCurrentUser, login, logout } from "@/api/client";
import type { User } from "@/types/contracts";

export interface LoginCredentials {
  username: string;
  password: string;
  domain?: string;
}

const SIGNED_OUT_KEY = "text-to-sql-analytics.signed-out";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signedOut: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  updateUser: (user: User) => void;
  signOut: () => Promise<void>;
  signIn: (credentials: LoginCredentials) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function isSignedOut(): boolean {
  return sessionStorage.getItem(SIGNED_OUT_KEY) === "1";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [signedOut, setSignedOut] = useState(isSignedOut);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (isSignedOut()) {
      setUser(null);
      setSignedOut(true);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      setSignedOut(false);
      setError(null);
    } catch (err) {
      setUser(null);
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } catch {
      // Ignore logout errors — local signed-out state still applies.
    }
    sessionStorage.setItem(SIGNED_OUT_KEY, "1");
    setUser(null);
    setSignedOut(true);
    setError(null);
    setLoading(false);
  }, []);

  const signIn = useCallback(async (credentials: LoginCredentials) => {
    const authenticatedUser = await login(credentials);
    sessionStorage.removeItem(SIGNED_OUT_KEY);
    setUser(authenticatedUser);
    setSignedOut(false);
    setError(null);
    setLoading(false);
  }, []);

  const updateUser = useCallback((next: User) => {
    setUser(next);
  }, []);

  const value = useMemo(
    () => ({ user, loading, signedOut, error, refresh, updateUser, signOut, signIn }),
    [user, loading, signedOut, error, refresh, updateUser, signOut, signIn],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
