import { useEffect, useState } from "react";
import type { FlagResponse } from "../types/flag";
import { listFlags } from "../api/flags";
import { FlagList } from "../components/FlagList";
import { FlagForm } from "../components/FlagForm";
import { ExperimentResults } from "../components/ExperimentResults";

export function FlagsPage() {
  const [flags, setFlags] = useState<FlagResponse[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const refresh = () => listFlags().then(setFlags).catch(console.error);
  useEffect(() => { refresh(); }, []);
  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
      <h1 style={{ marginBottom: 24 }}>Flagstone</h1>
      <FlagForm onCreated={refresh} />
      <div style={{ marginTop: 24 }}>
        <FlagList flags={flags} onRefresh={refresh} onSelect={setSelected} />
      </div>
      {selected && (
        <div style={{ marginTop: 32 }}>
          <h2>Experiment: {selected}</h2>
          <ExperimentResults flagKey={selected} />
        </div>
      )}
    </div>
  );
}
