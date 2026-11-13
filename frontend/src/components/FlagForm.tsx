import { useState, type FormEvent } from "react";
import { createFlag } from "../api/flags";
import { messageOf } from "../api/http";
import type { FlagResponse } from "../types/flag";

interface Props {
  onCreated: (flag: FlagResponse) => void;
  onCancel: () => void;
}

const KINDS = {
  boolean: { label: "Boolean (off / on)", variations: [false, true] },
  experiment: { label: "Experiment (control / treatment)", variations: ["control", "treatment"] },
} as const;

type Kind = keyof typeof KINDS;

// Keys end up in URL paths and in SDK calls, so keep them to a safe charset.
const KEY_PATTERN = "[A-Za-z0-9][A-Za-z0-9._\\-]*";

export function FlagForm({ onCreated, onCancel }: Props) {
  const [key, setKey] = useState("");
  const [kind, setKind] = useState<Kind>("boolean");
  const [enabled, setEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const flag = await createFlag({
        key: key.trim(),
        enabled,
        variations: [...KINDS[kind].variations],
        default_variation: 0,
        rules: [],
        rollout: null,
      });
      onCreated(flag);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="create-form">
      <label className="field">
        <span>Flag key</span>
        <input
          autoFocus
          value={key}
          onChange={e => setKey(e.target.value)}
          placeholder="new-checkout"
          pattern={KEY_PATTERN}
          title="Letters, numbers, dots, dashes and underscores"
          maxLength={100}
          required
        />
      </label>
      <label className="field">
        <span>Type</span>
        <select value={kind} onChange={e => setKind(e.target.value as Kind)}>
          {Object.entries(KINDS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
        Turn on immediately
      </label>
      {error && <p className="error-text" role="alert">{error}</p>}
      <div className="row">
        <button type="submit" className="btn primary" disabled={busy}>
          {busy ? "Creating…" : "Create flag"}
        </button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
