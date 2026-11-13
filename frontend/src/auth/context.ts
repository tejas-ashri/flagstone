import { createContext, useContext } from "react";
import type { Me } from "../types/project";

export interface AuthState {
  status: "loading" | "signedOut" | "signedIn";
  me: Me | null;
  // Reloads the signed-in user and their project list.
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function useMe(): Me {
  const { me } = useAuth();
  if (!me) throw new Error("useMe must be used on a signed-in page");
  return me;
}
