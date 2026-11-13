import { useEffect, useMemo, useState } from "react";
import { evaluateFlag } from "../../api/flags";
import { messageOf } from "../../api/http";
import { useFlag } from "../../flag/context";
import { OPERATORS } from "../../lib/draft";
import { formatValue, parseValue } from "../../lib/values";
import { useProject } from "../../project/context";
import type { EvaluateResult, FlagResponse } from "../../types/flag";

interface Attr {
  id: number;
  name: string;
  value: string;
}

let nextId = 1;

function initialAttrs(flag: FlagResponse): Attr[] {
  const names = ["id", ...new Set(flag.rules.map(r => r.attribute).filter(a => a && a !== "id"))];
  return names.map(name => ({ id: nextId++, name, value: name === "id" ? "user-123" : "" }));
}

function describe(flag: FlagResponse, r: EvaluateResult): string {
  switch (r.reason) {
    case "disabled":
      return "The flag is off, so everyone gets the default variation.";
    case "rule": {
      const rule = flag.rules[r.rule_index ?? 0];
      const op = OPERATORS.find(o => o.value === rule?.operator)?.label ?? rule?.operator;
      return rule
        ? `Matched rule ${(r.rule_index ?? 0) + 1}: ${rule.attribute} ${op} ${formatValue(rule.value)}.`
        : "Matched a targeting rule.";
    }
    case "rollout":
      return `No rule matched. This user's bucket is ${r.bucket}, which is inside the ${r.rollout_percentage}% rollout.`;
    case "outside_rollout":
      return `No rule matched. This user's bucket is ${r.bucket}, outside the ${r.rollout_percentage}% rollout, so they get the default.`;
    default:
      return "No rule matched and there is no rollout, so they get the default variation.";
  }
}

export function FlagTestPage() {
  const { flag } = useFlag();
  const { project } = useProject();
  const [attrs, setAttrs] = useState<Attr[]>(() => initialAttrs(flag));
  const [result, setResult] = useState<EvaluateResult | null>(null);
  const [error, setError] = useState("");

  const user = useMemo(() => {
    const u: Record<string, unknown> = {};
    for (const a of attrs) {
      const name = a.name.trim();
      if (!name || !a.value.trim()) continue;
      // The SDK hashes `id` as a string, so keep it one even if it looks numeric.
      u[name] = name === "id" ? a.value.trim() : parseValue(a.value);
    }
    return u;
  }, [attrs]);

  // Re-evaluate shortly after typing stops, and whenever the saved flag changes.
  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(() => {
      evaluateFlag(project.id, flag.key, user)
        .then(r => {
          if (cancelled) return;
          setResult(r);
          setError("");
        })
        .catch(err => !cancelled && setError(messageOf(err)));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [project.id, flag, user]);

  const setAttr = (id: number, patch: Partial<Attr>) =>
    setAttrs(as => as.map(a => (a.id === id ? { ...a, ...patch } : a)));

  return (
    <div className="split-layout">
      <section className="card">
        <header className="card-head">
          <h3>User attributes</h3>
          <p className="muted small">
            The same object your app passes to <code>is_enabled(key, user)</code>. Numbers and{" "}
            <code>true</code>/<code>false</code> are sent as typed values.
          </p>
        </header>
        <div className="stack">
          {attrs.map(a => (
            <div className="row" key={a.id}>
              <input
                className="attr-name"
                value={a.name}
                placeholder="attribute"
                aria-label="Attribute name"
                onChange={e => setAttr(a.id, { name: e.target.value })}
              />
              <input
                className="grow"
                value={a.value}
                placeholder="value"
                aria-label={`Value of ${a.name || "attribute"}`}
                onChange={e => setAttr(a.id, { value: e.target.value })}
              />
              <button
                type="button"
                className="btn ghost danger"
                aria-label={`Remove ${a.name || "attribute"}`}
                onClick={() => setAttrs(as => as.filter(x => x.id !== a.id))}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          className="btn"
          onClick={() => setAttrs(as => [...as, { id: nextId++, name: "", value: "" }])}
        >
          + Add attribute
        </button>
      </section>

      <section className="card result-card" aria-live="polite">
        <header className="card-head">
          <h3>Result</h3>
          <p className="muted small">Uses the saved configuration, not unsaved edits on the Targeting tab.</p>
        </header>
        {error && <p className="error-text" role="alert">{error}</p>}
        {result && !error && (
          <>
            <div className="result-value">
              <span className="index">{result.variation_index}</span>
              <code>{formatValue(result.value)}</code>
            </div>
            <p>{describe(flag, result)}</p>
            <pre><code>{JSON.stringify(user, null, 2)}</code></pre>
          </>
        )}
        {!result && !error && <p className="muted">Evaluating…</p>}
      </section>
    </div>
  );
}
