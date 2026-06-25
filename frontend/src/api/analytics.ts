import type { ExperimentResults } from "../types/flag";

export async function getExperimentResults(flagKey: string): Promise<ExperimentResults> {
  const r = await fetch(`/api/experiments/${flagKey}/results`);
  return r.json();
}
