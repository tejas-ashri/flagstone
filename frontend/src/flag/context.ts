import { createContext, useContext } from "react";
import type { FlagResponse } from "../types/flag";

export interface FlagState {
  flag: FlagResponse;
  setFlag: (flag: FlagResponse) => void;
}

export const FlagContext = createContext<FlagState | null>(null);

export function useFlag(): FlagState {
  const ctx = useContext(FlagContext);
  if (!ctx) throw new Error("useFlag must be used inside a flag route");
  return ctx;
}
