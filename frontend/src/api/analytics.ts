import type { ExperimentResults } from "../types/flag";
import { request } from "./http";

export function getExperimentResults(flagKey: string): Promise<ExperimentResults> {
  return request(`/api/experiments/${encodeURIComponent(flagKey)}/results`);
}
