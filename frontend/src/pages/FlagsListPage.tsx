import { useCallback, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listFlags } from "../api/flags";
import { FlagForm } from "../components/FlagForm";
import { Modal } from "../components/Modal";
import { Toggle } from "../components/Toggle";
import { useFlagToggle } from "../lib/useFlagToggle";
import { useLoad } from "../lib/useLoad";
import { formatValue } from "../lib/values";
import { flagPath, useProject } from "../project/context";
import type { FlagResponse } from "../types/flag";

type Filter = "all" | "on" | "off" | "targeted";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "on", label: "On" },
  { id: "off", label: "Off" },
  { id: "targeted", label: "With rules or rollout" },
];

function summary(flag: FlagResponse): string {
  const parts = [];
  if (flag.rules.length) parts.push(`${flag.rules.length} rule${flag.rules.length === 1 ? "" : "s"}`);
  if (flag.rollout) parts.push(`${flag.rollout.percentage}% rollout`);
  return parts.join(" · ") || "Default only";
}

function timeAgo(iso: string): string {
  const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  const units: [number, string][] = [[60, "minute"], [3600, "hour"], [86400, "day"], [2592000, "month"]];
  let label = "";
  for (const [size, name] of units) {
    if (s >= size) {
      const n = Math.floor(s / size);
      label = `${n} ${name}${n === 1 ? "" : "s"} ago`;
    }
  }
  return label;
}

export function FlagsListPage() {
  const { project, isAdmin } = useProject();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const filter = (params.get("filter") as Filter) || "all";
  const [creating, setCreating] = useState(false);

  const flags = useLoad(() => listFlags(project.id), [project.id]);
  const { setData } = flags;
  const replace = useCallback(
    (flag: FlagResponse) => setData(prev => prev && prev.map(f => (f.key === flag.key ? flag : f))),
    [setData],
  );
  const toggle = useFlagToggle(project.id, replace);

  const setParam = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value && value !== "all") next.set(name, value);
    else next.delete(name);
    setParams(next, { replace: true });
  };

  const q = query.trim().toLowerCase();
  const all = flags.data ?? [];
  const visible = all.filter(f => {
    if (q && !f.key.toLowerCase().includes(q)) return false;
    if (filter === "on") return f.enabled;
    if (filter === "off") return !f.enabled;
    if (filter === "targeted") return f.rules.length > 0 || f.rollout !== null;
    return true;
  });

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Flags</h1>
          <p className="muted">
            {flags.data ? `${all.length} flag${all.length === 1 ? "" : "s"} · ${all.filter(f => f.enabled).length} on` : " "}
          </p>
        </div>
        {isAdmin && (
          <button type="button" className="btn primary" onClick={() => setCreating(true)}>New flag</button>
        )}
      </header>

      <div className="toolbar">
        <input
          type="search"
          className="grow"
          placeholder="Search by key"
          aria-label="Search flags"
          value={query}
          onChange={e => setParam("q", e.target.value)}
        />
        <div className="segmented" role="group" aria-label="Filter flags">
          {FILTERS.map(f => (
            <button
              key={f.id}
              type="button"
              aria-pressed={filter === f.id}
              className={filter === f.id ? "active" : ""}
              onClick={() => setParam("filter", f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {flags.error && (
        <div className="banner" role="alert">
          <span>{flags.error}</span>
          <button type="button" className="btn" onClick={flags.reload}>Retry</button>
        </div>
      )}
      {flags.loading && !flags.data && <p className="muted">Loading flags…</p>}

      {flags.data && all.length === 0 && (
        <div className="empty">
          <h2>No flags yet</h2>
          <p>Flags let you ship code switched off, then turn it on for chosen users or a percentage of traffic.</p>
          {isAdmin && <button type="button" className="btn primary" onClick={() => setCreating(true)}>Create your first flag</button>}
        </div>
      )}
      {flags.data && all.length > 0 && visible.length === 0 && (
        <p className="muted">No flags match these filters.</p>
      )}

      {visible.length > 0 && (
        <div className="card flush">
          <div className="table-wrap">
            <table className="flags-table">
              <thead>
                <tr>
                  <th>Flag</th>
                  <th>Targeting</th>
                  <th>Default</th>
                  <th>Updated</th>
                  <th className="num">On</th>
                </tr>
              </thead>
              <tbody>
                {visible.map(f => (
                  <tr
                    key={f.key}
                    className="clickable"
                    tabIndex={0}
                    onClick={() => navigate(flagPath(project.id, f.key))}
                    onKeyDown={e => {
                      if (e.target === e.currentTarget && e.key === "Enter") navigate(flagPath(project.id, f.key));
                    }}
                  >
                    <td><code className="flag-key">{f.key}</code></td>
                    <td className="muted">{summary(f)}</td>
                    <td><code>{formatValue(f.variations[f.default_variation])}</code></td>
                    <td className="muted" title={new Date(f.updated_at).toLocaleString()}>{timeAgo(f.updated_at)}</td>
                    <td className="num">
                      <Toggle
                        checked={f.enabled}
                        disabled={!isAdmin}
                        onChange={() => toggle(f)}
                        label={isAdmin ? `Turn ${f.key} ${f.enabled ? "off" : "on"}` : "Only admins can change flags"}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Modal open={creating} title="New flag" onClose={() => setCreating(false)}>
        <FlagForm
          projectId={project.id}
          onCancel={() => setCreating(false)}
          onCreated={flag => navigate(flagPath(project.id, flag.key))}
        />
      </Modal>
    </>
  );
}
