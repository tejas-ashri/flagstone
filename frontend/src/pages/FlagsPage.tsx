import { useCallback, useEffect, useRef, useState } from "react";
import { deleteFlag, listFlags, updateFlag } from "../api/flags";
import { messageOf } from "../api/http";
import { FlagDetail } from "../components/FlagDetail";
import { FlagForm } from "../components/FlagForm";
import { FlagList } from "../components/FlagList";
import type { FlagResponse } from "../types/flag";

const byKey = (a: FlagResponse, b: FlagResponse) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);

export function FlagsPage() {
  const [flags, setFlags] = useState<FlagResponse[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const dirty = useRef(false);

  const refresh = useCallback(async () => {
    try {
      setFlags(await listFlags());
      setError("");
    } catch (err) {
      setError(messageOf(err));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onDirtyChange = useCallback((d: boolean) => {
    dirty.current = d;
  }, []);

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty.current) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, []);

  const canLeave = () => !dirty.current || confirm("Discard unsaved changes?");

  const put = (flag: FlagResponse) =>
    setFlags(prev => [...(prev ?? []).filter(f => f.key !== flag.key), flag].sort(byKey));

  const select = (key: string) => {
    if (key === selected && !creating) return;
    if (!canLeave()) return;
    setCreating(false);
    setSelected(key);
  };

  const startCreate = () => {
    if (!canLeave()) return;
    setSelected(null);
    setCreating(true);
  };

  const toggle = async (flag: FlagResponse) => {
    try {
      put(await updateFlag(flag.key, { enabled: !flag.enabled }));
      setError("");
    } catch (err) {
      setError(messageOf(err));
      refresh();
    }
  };

  const remove = async (flag: FlagResponse) => {
    if (!confirm(`Delete flag "${flag.key}"? Its experiment events are deleted too. This cannot be undone.`)) return;
    try {
      await deleteFlag(flag.key);
      setFlags(prev => (prev ?? []).filter(f => f.key !== flag.key));
      setSelected(null);
      setError("");
    } catch (err) {
      setError(messageOf(err));
      refresh();
    }
  };

  const q = query.trim().toLowerCase();
  const visible = (flags ?? []).filter(f => f.key.toLowerCase().includes(q));
  const current = flags?.find(f => f.key === selected) ?? null;

  return (
    <div className="app">
      <header className="topbar">
        <h1>Flagstone</h1>
        <span className="muted small">
          {flags ? `${flags.length} flag${flags.length === 1 ? "" : "s"} · ${flags.filter(f => f.enabled).length} on` : ""}
        </span>
      </header>

      {error && (
        <div className="banner" role="alert">
          <span>{error}</span>
          <button type="button" className="btn" onClick={refresh}>Retry</button>
        </div>
      )}

      <div className="layout">
        <aside className="sidebar">
          <div className="row">
            <input
              type="search"
              className="grow"
              placeholder="Search flags"
              aria-label="Search flags"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            <button type="button" className="btn primary" onClick={startCreate}>New flag</button>
          </div>
          {flags === null && !error && <p className="muted">Loading flags…</p>}
          {flags?.length === 0 && <p className="muted">No flags yet. Create your first one.</p>}
          {flags && flags.length > 0 && visible.length === 0 && <p className="muted">No flags match “{query}”.</p>}
          <FlagList flags={visible} selected={creating ? null : selected} onSelect={select} onToggle={toggle} />
        </aside>

        <main className="main">
          {creating ? (
            <div className="card">
              <header className="card-head">
                <h3>New flag</h3>
                <p className="muted small">Add targeting rules and a rollout after creating it.</p>
              </header>
              <FlagForm
                onCreated={flag => {
                  put(flag);
                  setCreating(false);
                  setSelected(flag.key);
                }}
                onCancel={() => setCreating(false)}
              />
            </div>
          ) : current ? (
            <FlagDetail
              key={current.key}
              flag={current}
              onSaved={put}
              onToggle={toggle}
              onDelete={remove}
              onDirtyChange={onDirtyChange}
            />
          ) : (
            <div className="empty">
              <p>Select a flag to edit its variations, targeting rules and rollout, or to see experiment results.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
