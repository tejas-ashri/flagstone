import type { FlagResponse } from "../types/flag";
import { updateFlag, deleteFlag } from "../api/flags";

interface Props {
  flags: FlagResponse[];
  onRefresh: () => void;
}

export function FlagList({ flags, onRefresh }: Props) {
  const toggle = async (flag: FlagResponse) => {
    await updateFlag(flag.key, { enabled: !flag.enabled });
    onRefresh();
  };
  const remove = async (key: string) => {
    if (confirm(`Delete flag "${key}"?`)) {
      await deleteFlag(key);
      onRefresh();
    }
  };
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr>
          {["Key", "Status", "Variations", "Updated", "Actions"].map(h => (
            <th key={h} style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #ddd" }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {flags.map(f => (
          <tr key={f.key}>
            <td style={{ padding: "8px" }}><code>{f.key}</code></td>
            <td style={{ padding: "8px" }}>
              <button onClick={() => toggle(f)} style={{ background: f.enabled ? "#22c55e" : "#ef4444", color: "#fff", border: "none", borderRadius: 4, padding: "4px 12px", cursor: "pointer" }}>
                {f.enabled ? "ON" : "OFF"}
              </button>
            </td>
            <td style={{ padding: "8px" }}>{f.variations.length} variations</td>
            <td style={{ padding: "8px" }}>{new Date(f.updated_at).toLocaleString()}</td>
            <td style={{ padding: "8px" }}>
              <button onClick={() => remove(f.key)} style={{ color: "#ef4444", background: "none", border: "none", cursor: "pointer" }}>Delete</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
