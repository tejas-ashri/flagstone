import { useEffect, useState } from "react";
import type { ExperimentResults as Results } from "../types/flag";
import { getExperimentResults } from "../api/analytics";

export function ExperimentResults({ flagKey }: { flagKey: string }) {
  const [data, setData] = useState<Results | null>(null);
  useEffect(() => {
    getExperimentResults(flagKey).then(setData);
  }, [flagKey]);
  if (!data) return <p>Loading...</p>;
  if (!data.variations.length) return <p>No experiment data yet.</p>;
  const best = data.variations.reduce((a, b) =>
    (b.conversion_rate_pct ?? 0) > (a.conversion_rate_pct ?? 0) ? b : a
  );
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          {["Variation", "Exposures", "Conversions", "Rate"].map(h => (
            <th key={h} style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #ddd" }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.variations.map(v => (
          <tr key={v.variation_index} style={{ background: v === best ? "#f0fdf4" : undefined }}>
            <td style={{ padding: "8px" }}>Variation {v.variation_index}{v === best ? " ★" : ""}</td>
            <td style={{ padding: "8px" }}>{v.exposures}</td>
            <td style={{ padding: "8px" }}>{v.conversions}</td>
            <td style={{ padding: "8px" }}>{v.conversion_rate_pct != null ? `${v.conversion_rate_pct}%` : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
