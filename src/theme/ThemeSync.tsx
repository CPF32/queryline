import { useEffect } from "react";
import { useAuth } from "@/auth/AuthContext";
import { useTheme } from "@/theme/ThemeProvider";

function normalizeTheme(value: string | null | undefined): "light" | "dark" {
  return value === "light" ? "light" : "dark";
}

export default function ThemeSync() {
  const { user } = useAuth();
  const { setTheme } = useTheme();

  useEffect(() => {
    if (user?.theme) {
      setTheme(normalizeTheme(user.theme));
    }
  }, [user?.id, user?.theme, setTheme]);

  return null;
}

export { normalizeTheme };
