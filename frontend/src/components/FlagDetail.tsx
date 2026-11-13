import { useCallback, useState } from "react";
import type { FlagResponse } from "../types/flag";
import { ExperimentResults } from "./ExperimentResults";
import { FlagEditor } from "./FlagEditor";
import { Toggle } from "./Toggle";

interface Props {
  flag: FlagResponse;
  onSaved: (flag: FlagResponse) => void;
  onToggle: (flag: FlagResponse) => void;
  onDelete: (flag: FlagResponse) => void;
  onDirtyChange: (dirty: boolean) => void;
}

type Tab = "targeting" | "results" | "sdk";

const TABS: { id: Tab; label: string }[] = [
  { id: "targeting", label: "Targeting" },
  { id: "results", label: "Results" },
  { id: "sdk", label: "SDK usage" },
];

function snippet(flag: FlagResponse): string {
  const key = JSON.stringify(flag.key);
  const isBoolean = flag.variations.every(v => typeof v === "boolean");
  const check = isBoolean
    ? `if client.is_enabled(${key}, user):\n    ...  # new behaviour`
    : `index = client.get_variation(${key}, user)  # index into the variations list`;
  return [
    "from sdk.client import FlagClient",
    "",
    'client = FlagClient(sdk_key="<your SDK key>", base_url="http://localhost:8000")',
    'user = {"id": "user-123", "plan": "pro"}',
    "",
    check,
    "",
    `client.track_conversion(${key}, user)`,
  ].join("\n");
}

export function FlagDetail({ flag, onSaved, onToggle, onDelete, onDirtyChange }: Props) {
  const [tab, setTab] = useState<Tab>("targeting");
  const [dirty, setDirty] = useState(false);

  const reportDirty = useCallback(
    (d: boolean) => {
      setDirty(d);
      onDirtyChange(d);
    },
    [onDirtyChange],
  );

  const switchTab = (next: Tab) => {
    // The editor unmounts when leaving the targeting tab, taking its draft with it.
    if (tab === "targeting" && next !== tab && dirty && !confirm("Discard unsaved changes?")) return;
    setTab(next);
  };

  return (
    <div className="detail">
      <header className="detail-head">
        <div>
          <h2><code>{flag.key}</code></h2>
          <p className="muted small">Updated {new Date(flag.updated_at).toLocaleString()}</p>
        </div>
        <div className="row">
          <span className={`status${flag.enabled ? " on" : ""}`}>{flag.enabled ? "On" : "Off"}</span>
          <Toggle
            checked={flag.enabled}
            onChange={() => onToggle(flag)}
            label={flag.enabled ? "Turn flag off" : "Turn flag on"}
          />
          <button type="button" className="btn danger" onClick={() => onDelete(flag)}>Delete</button>
        </div>
      </header>

      <nav className="tabs" role="tablist">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`tab${tab === t.id ? " active" : ""}`}
            onClick={() => switchTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "targeting" && <FlagEditor flag={flag} onSaved={onSaved} onDirtyChange={reportDirty} />}
      {tab === "results" && <ExperimentResults flag={flag} />}
      {tab === "sdk" && (
        <div className="card">
          <header className="card-head">
            <h3>Use this flag from Python</h3>
            <p className="muted small">
              Pass the user attributes your targeting rules refer to. <code>id</code> drives the percentage rollout.
            </p>
          </header>
          <pre><code>{snippet(flag)}</code></pre>
        </div>
      )}
    </div>
  );
}
