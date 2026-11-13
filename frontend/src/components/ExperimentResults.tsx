import { useCallback, useEffect, useState } from "react";
import { getExperimentResults } from "../api/analytics";
import { messageOf } from "../api/http";
import { useFlag } from "../flag/context";
import { formatValue } from "../lib/values";
import { useProject } from "../project/context";
import type { FlagResponse, VariationResult } from "../types/flag";

function rows(flag: FlagResponse, results: VariationResult[]): VariationResult[] {
  // Show every configured variation, even with no events yet, plus any index
  // that has events but is no longer configured.
  const byIndex = new Map(results.map(r => [r.variation_index, r]));
  flag.variations.forEach((_, i) => {
    if (!byIndex.has(i)) {
      byIndex.set(i, { variation_index: i, exposures: 0, conversions: 0, conversion_rate_pct: null });
    }
  });
  return [...byIndex.values()].sort((a, b) => a.variation_index - b.variation_index);
}

function lift(rate: number | null, baseline: number | null): string {
  if (rate == null || baseline == null || baseline === 0) return "—";
  const pct = (100 * (rate - baseline)) / baseline;
  return `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

const AUTO_REFRESH_MS = 10_000;

export function ExperimentResults() {
  const { flag } = useFlag();
  const { project } = useProject();
  const [results, setResults] = useState<VariationResult[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [auto, setAuto] = useState(false);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const flagKey = flag.key;

  const load = useCallback(() => {
    setLoading(true);
    return getExperimentResults(project.id, flagKey)
      .then(d => {
        setResults(d.variations);
        setError("");
        setLoadedAt(new Date());
      })
      .catch(err => setError(messageOf(err)))
      .finally(() => setLoading(false));
  }, [project.id, flagKey]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!auto) return;
    const id = setInterval(load, AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [auto, load]);

  if (error && !results) {
    return (
      <div className="card">
        <p className="error-text" role="alert">{error}</p>
        <button type="button" className="btn" onClick={load}>Retry</button>
      </div>
    );
  }
  if (!results) return <p className="muted">Loading results…</p>;

  const data = rows(flag, results);
  const total = data.reduce((n, r) => n + r.exposures + r.conversions, 0);
  const baseline = data.find(r => r.variation_index === flag.default_variation)?.conversion_rate_pct ?? null;
  const topRate = Math.max(0, ...data.map(r => r.conversion_rate_pct ?? 0));
  const leaders = data.filter(r => topRate > 0 && r.conversion_rate_pct === topRate);

  return (
    <div className="card">
      <header className="card-head split">
        <div>
          <h3>Results by variation</h3>
          <p className="muted small">
            Exposures are recorded when the SDK evaluates this flag with <code>is_enabled</code>; conversions when
            your app calls <code>track_conversion</code>.
          </p>
        </div>
        <div className="row wrap">
          <label className="check small">
            <input type="checkbox" checked={auto} onChange={e => setAuto(e.target.checked)} />
            Auto-refresh
          </label>
          <button type="button" className="btn" onClick={load} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>
      {loadedAt && <p className="muted small">Last updated {loadedAt.toLocaleTimeString()}</p>}
      {error && <p className="error-text" role="alert">{error}</p>}
      {total === 0 ? (
        <p className="muted">No events yet. They appear here once an SDK client starts evaluating this flag.</p>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Variation</th>
                  <th className="num">Exposures</th>
                  <th className="num">Conversions</th>
                  <th className="num">Conversion rate</th>
                  <th className="num">vs default</th>
                </tr>
              </thead>
              <tbody>
                {data.map(r => {
                  const configured = r.variation_index < flag.variations.length;
                  const isDefault = r.variation_index === flag.default_variation;
                  return (
                    <tr key={r.variation_index}>
                      <td>
                        <span className="index">{r.variation_index}</span>{" "}
                        {configured ? <code>{formatValue(flag.variations[r.variation_index])}</code> : <span className="muted">removed</span>}
                        {isDefault && <span className="badge">default</span>}
                        {leaders.length === 1 && leaders[0] === r && <span className="badge good">leading</span>}
                      </td>
                      <td className="num">{r.exposures.toLocaleString()}</td>
                      <td className="num">{r.conversions.toLocaleString()}</td>
                      <td className="num">{r.conversion_rate_pct != null ? `${r.conversion_rate_pct}%` : "—"}</td>
                      <td className="num">{isDefault ? "—" : lift(r.conversion_rate_pct, baseline)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="muted small">
            Rates are raw counts with no significance test, so treat small samples with caution.
          </p>
        </>
      )}
    </div>
  );
}
