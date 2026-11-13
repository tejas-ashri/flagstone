import { useCallback, useEffect, useRef, useState } from "react";
import { messageOf } from "../api/http";

export interface Loaded<T> {
  data: T | null;
  error: string;
  loading: boolean;
  reload: () => Promise<void>;
  setData: (value: T | ((prev: T | null) => T | null)) => void;
}

// Fetches on mount and whenever deps change. Responses for stale deps are
// ignored, so fast navigation can't show the previous page's data.
export function useLoad<T>(load: () => Promise<T>, deps: unknown[]): Loaded<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const generation = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);

  const reload = useCallback(async () => {
    const gen = ++generation.current;
    setLoading(true);
    try {
      const value = await run();
      if (gen === generation.current) {
        setData(value);
        setError("");
      }
    } catch (err) {
      if (gen === generation.current) setError(messageOf(err));
    } finally {
      if (gen === generation.current) setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    setData(null);
    reload();
  }, [reload]);

  return { data, error, loading, reload, setData };
}
