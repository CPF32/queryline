import { useEffect } from "react";
import { fetchSystemIdentity, getDesktopSystemUser } from "@/api/client";

function formatSystemUsername(
  identity: NonNullable<Awaited<ReturnType<typeof fetchSystemIdentity>>>,
): string {
  if (identity.display_name.trim()) {
    return identity.display_name.trim();
  }
  if (identity.domain) {
    return `${identity.domain}\\${identity.username}`;
  }
  return identity.username.trim();
}

/** Pre-fill a username field from the desktop shell or server-resolved OS/SSO identity. */
export function useSystemUsernamePrefill(
  setUsername: (value: string) => void,
): void {
  useEffect(() => {
    let cancelled = false;

    async function prefill() {
      const desktopUser = getDesktopSystemUser();
      if (desktopUser) {
        if (!cancelled) {
          setUsername(desktopUser);
        }
        return;
      }

      const identity = await fetchSystemIdentity();
      if (cancelled || !identity) {
        return;
      }

      const formatted = formatSystemUsername(identity);
      if (formatted) {
        setUsername(formatted);
      }
    }

    void prefill();

    return () => {
      cancelled = true;
    };
  }, [setUsername]);
}
