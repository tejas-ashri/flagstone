import { useState } from "react";
import { createFlag } from "../api/flags";

interface Props {
  onCreated: () => void;
}

export function FlagForm({ onCreated }: Props) {
  const [key, setKey] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await createFlag({ key, enabled: true, variations: [false, true], default_variation: 0, rules: [], rollout: null });
      setKey("");
      onCreated();
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <form onSubmit={submit} style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input
        value={key}
        onChange={e => setKey(e.target.value)}
        placeholder="Flag key (e.g. new-checkout)"
        style={{ padding: "8px", borderRadius: 4, border: "1px solid #ddd", flex: 1 }}
        required
      />
      <button type="submit" style={{ padding: "8px 16px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
        Create Flag
      </button>
      {error && <span style={{ color: "#ef4444" }}>{error}</span>}
    </form>
  );
}
