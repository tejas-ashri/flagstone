import { useEffect, useMemo, useState } from "react";
import { updateFlag } from "../api/flags";
import { messageOf } from "../api/http";
import {
  OPERATORS,
  buildUpdate,
  draftFromFlag,
  fingerprint,
  newId,
  removeVariation,
  type FlagDraft,
  type RuleDraft,
} from "../lib/draft";
import { parseValue, valueType } from "../lib/values";
import type { FlagResponse, RuleOperator } from "../types/flag";

interface Props {
  flag: FlagResponse;
  onSaved: (flag: FlagResponse) => void;
  onDirtyChange: (dirty: boolean) => void;
}

export function FlagEditor({ flag, onSaved, onDirtyChange }: Props) {
  const [draft, setDraft] = useState<FlagDraft>(() => draftFromFlag(flag));
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const dirty = useMemo(
    () => fingerprint(draft) !== fingerprint(draftFromFlag(flag)),
    [draft, flag],
  );

  useEffect(() => {
    onDirtyChange(dirty);
    return () => onDirtyChange(false);
  }, [dirty, onDirtyChange]);

  const change = (next: FlagDraft) => {
    setDraft(next);
    setSavedAt(null);
  };

  const variationOptions = draft.variations.map((v, i) => (
    <option key={v.id} value={i}>{i}: {v.text.trim() || "(empty)"}</option>
  ));
  const variationName = (i: number) => draft.variations[i]?.text.trim() || `variation ${i}`;

  const setRule = (id: number, patch: Partial<RuleDraft>) =>
    change({ ...draft, rules: draft.rules.map(r => (r.id === id ? { ...r, ...patch } : r)) });

  const moveRule = (index: number, delta: number) => {
    const rules = [...draft.rules];
    const [rule] = rules.splice(index, 1);
    rules.splice(index + delta, 0, rule);
    change({ ...draft, rules });
  };

  const save = async () => {
    const { errors: found, payload } = buildUpdate(draft);
    setErrors(found);
    if (!payload) return;
    setSaving(true);
    try {
      const updated = await updateFlag(flag.key, payload);
      setDraft(draftFromFlag(updated));
      setSavedAt(Date.now());
      onSaved(updated);
    } catch (err) {
      setErrors([messageOf(err)]);
    } finally {
      setSaving(false);
    }
  };

  const discard = () => {
    setDraft(draftFromFlag(flag));
    setErrors([]);
  };

  const pct = Number(draft.rollout.percentage);
  const pctValid = Number.isFinite(pct) && pct >= 0 && pct <= 100;

  return (
    <div className="editor">
      {!flag.enabled && (
        <p className="notice">
          This flag is off, so every user gets the default variation. Rules and rollout apply once it is turned on.
        </p>
      )}

      <section className="card">
        <header className="card-head">
          <h3>Variations</h3>
          <p className="muted small">
            The values this flag can return. Type <code>true</code>, <code>42</code> or JSON for typed values;
            anything else is a string.
          </p>
        </header>
        <div className="stack">
          {draft.variations.map((v, i) => (
            <div className="row" key={v.id}>
              <span className="index">{i}</span>
              <input
                className="grow"
                value={v.text}
                aria-label={`Variation ${i} value`}
                onChange={e =>
                  change({
                    ...draft,
                    variations: draft.variations.map(x => (x.id === v.id ? { ...x, text: e.target.value } : x)),
                  })
                }
              />
              <span className="badge">{v.text.trim() ? valueType(parseValue(v.text)) : "empty"}</span>
              <button
                type="button"
                className="btn ghost danger"
                disabled={draft.variations.length <= 2}
                title={draft.variations.length <= 2 ? "A flag needs at least two variations" : "Remove variation"}
                onClick={() => change(removeVariation(draft, i))}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          className="btn"
          onClick={() => change({ ...draft, variations: [...draft.variations, { id: newId(), text: "" }] })}
        >
          + Add variation
        </button>
      </section>

      <section className="card">
        <header className="card-head">
          <h3>Targeting rules</h3>
          <p className="muted small">
            Checked top to bottom against the user attributes your app passes to the SDK. The first match wins.
          </p>
        </header>
        {draft.rules.length === 0 && <p className="muted">No rules. Every user falls through to the rollout.</p>}
        <div className="stack">
          {draft.rules.map((r, i) => {
            const op = OPERATORS.find(o => o.value === r.operator)!;
            return (
              <div className="rule" key={r.id}>
                <span className="index">{i + 1}</span>
                <div className="rule-fields">
                  <span className="muted">If</span>
                  <input
                    value={r.attribute}
                    placeholder="attribute, e.g. plan"
                    aria-label={`Rule ${i + 1} attribute`}
                    onChange={e => setRule(r.id, { attribute: e.target.value })}
                  />
                  <select
                    value={r.operator}
                    aria-label={`Rule ${i + 1} operator`}
                    onChange={e => setRule(r.id, { operator: e.target.value as RuleOperator })}
                  >
                    {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  <input
                    value={r.valueText}
                    placeholder={op.hint}
                    aria-label={`Rule ${i + 1} value`}
                    inputMode={r.operator === "gt" || r.operator === "lt" ? "decimal" : undefined}
                    onChange={e => setRule(r.id, { valueText: e.target.value })}
                  />
                  <span className="muted">serve</span>
                  <select
                    value={r.variation}
                    aria-label={`Rule ${i + 1} variation`}
                    onChange={e => setRule(r.id, { variation: Number(e.target.value) })}
                  >
                    {variationOptions}
                  </select>
                </div>
                <div className="rule-actions">
                  <button type="button" className="btn ghost" title="Move up" aria-label={`Move rule ${i + 1} up`} disabled={i === 0} onClick={() => moveRule(i, -1)}>↑</button>
                  <button type="button" className="btn ghost" title="Move down" aria-label={`Move rule ${i + 1} down`} disabled={i === draft.rules.length - 1} onClick={() => moveRule(i, 1)}>↓</button>
                  <button type="button" className="btn ghost danger" onClick={() => change({ ...draft, rules: draft.rules.filter(x => x.id !== r.id) })}>Remove</button>
                </div>
              </div>
            );
          })}
        </div>
        <button
          type="button"
          className="btn"
          onClick={() =>
            change({
              ...draft,
              rules: [
                ...draft.rules,
                { id: newId(), attribute: "", operator: "equals", valueText: "", variation: Math.min(1, draft.variations.length - 1) },
              ],
            })
          }
        >
          + Add rule
        </button>
      </section>

      <section className="card">
        <header className="card-head">
          <h3>Percentage rollout</h3>
          <p className="muted small">
            Applies to users who match no rule. Each user is bucketed by their <code>id</code>, so they stay in the
            same group as the percentage grows.
          </p>
        </header>
        <label className="check">
          <input
            type="checkbox"
            checked={draft.rollout.enabled}
            onChange={e => change({ ...draft, rollout: { ...draft.rollout, enabled: e.target.checked } })}
          />
          Roll out to a percentage of users
        </label>
        {draft.rollout.enabled && (
          <>
            <div className="row wrap">
              <span className="muted">Serve</span>
              <select
                value={draft.rollout.variation}
                aria-label="Rollout variation"
                onChange={e => change({ ...draft, rollout: { ...draft.rollout, variation: Number(e.target.value) } })}
              >
                {variationOptions}
              </select>
              <span className="muted">to</span>
              <input
                type="range"
                min={0}
                max={100}
                className="grow"
                aria-label="Rollout percentage slider"
                value={pctValid ? pct : 0}
                onChange={e => change({ ...draft, rollout: { ...draft.rollout, percentage: e.target.value } })}
              />
              <input
                type="number"
                min={0}
                max={100}
                step={1}
                className="pct"
                aria-label="Rollout percentage"
                value={draft.rollout.percentage}
                onChange={e => change({ ...draft, rollout: { ...draft.rollout, percentage: e.target.value } })}
              />
              <span className="muted">% of users</span>
            </div>
            {pctValid && (
              <p className="muted small">
                About {pct}% get <strong>{variationName(draft.rollout.variation)}</strong>; the other {100 - pct}% get
                the default, <strong>{variationName(draft.defaultVariation)}</strong>.
              </p>
            )}
          </>
        )}
      </section>

      <section className="card">
        <header className="card-head">
          <h3>Default variation</h3>
          <p className="muted small">
            Served when the flag is off, and to users who match no rule and fall outside the rollout.
          </p>
        </header>
        <select
          value={draft.defaultVariation}
          aria-label="Default variation"
          onChange={e => change({ ...draft, defaultVariation: Number(e.target.value) })}
        >
          {variationOptions}
        </select>
      </section>

      <footer className="save-bar">
        {errors.length > 0 && (
          <ul className="error-text" role="alert">
            {errors.map(e => <li key={e}>{e}</li>)}
          </ul>
        )}
        <div className="row">
          <button type="button" className="btn primary" disabled={!dirty || saving} onClick={save}>
            {saving ? "Saving…" : "Save changes"}
          </button>
          <button type="button" className="btn" disabled={!dirty || saving} onClick={discard}>Discard</button>
          <span className="muted small" aria-live="polite">
            {dirty ? "Unsaved changes" : savedAt ? "Saved. Connected SDKs pick this up on their next refresh." : ""}
          </span>
        </div>
      </footer>
    </div>
  );
}
