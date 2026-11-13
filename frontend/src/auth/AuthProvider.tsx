import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, onUnauthorized } from "../api/http";
import { getMe, logout } from "../api/projects";
import type { Me } from "../types/project";
import { AuthContext, type AuthState } from "./context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [me, setMe] = useState<Me | null>(null);

  const refresh = useCallback(async () => {
    try {
      setMe(await getMe());
      setStatus("signedIn");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setMe(null);
        setStatus("signedOut");
      } else {
        // Backend unreachable on first load: show the login page, which
        // reports the connection problem itself. Later failures keep the
        // current state.
        setStatus(s => (s === "loading" ? "signedOut" : s));
      }
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    // Session expired or was revoked mid-use.
    onUnauthorized(() => {
      setMe(null);
      setStatus("signedOut");
    });
    return () => onUnauthorized(null);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      setMe(null);
      setStatus("signedOut");
    }
  }, []);

  const value = useMemo(() => ({ status, me, refresh, signOut }), [status, me, refresh, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
