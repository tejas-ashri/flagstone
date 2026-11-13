import type { ExperimentResults } from "../types/flag";
import { enc, request } from "./http";

export function getExperimentResults(projectId: string, flagKey: string): Promise<ExperimentResults> {
  return request(`/api/projects/${enc(projectId)}/experiments/${enc(flagKey)}/results`);
}
