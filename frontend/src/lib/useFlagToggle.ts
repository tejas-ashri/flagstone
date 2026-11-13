import { useCallback } from "react";
import { updateFlag } from "../api/flags";
import { messageOf } from "../api/http";
import { useToast } from "../components/toast/context";
import type { FlagResponse } from "../types/flag";

// Optimistic on/off: `apply` updates local state at once, the server call
// follows, a failure rolls back, and success offers Undo.
export function useFlagToggle(projectId: string, apply: (flag: FlagResponse) => void) {
  const toast = useToast();

  const set = useCallback(
    async (flag: FlagResponse, enabled: boolean, isUndo = false) => {
      apply({ ...flag, enabled });
      try {
        const saved = await updateFlag(projectId, flag.key, { enabled });
        apply(saved);
        if (!isUndo) {
          toast(`${flag.key} turned ${enabled ? "on" : "off"}`, {
            kind: "success",
            action: { label: "Undo", onClick: () => set(saved, !enabled, true) },
          });
        }
      } catch (err) {
        apply(flag);
        toast(`Couldn't turn ${flag.key} ${enabled ? "on" : "off"}: ${messageOf(err)}`, { kind: "error" });
      }
    },
    [projectId, apply, toast],
  );

  return useCallback((flag: FlagResponse) => set(flag, !flag.enabled), [set]);
}
