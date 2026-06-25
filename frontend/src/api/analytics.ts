import type { ExperimentResults } from "../types/flag";

export async function getExperimentResults(flagKey: string): Promise<ExperimentResults> {
  const r = await fetch(`/api/experiments/${flagKey}/results`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
