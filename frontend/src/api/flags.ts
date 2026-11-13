import type { EvaluateResult, FlagCreate, FlagResponse, FlagUpdate } from "../types/flag";
import { enc, jsonBody, request } from "./http";

const flagsUrl = (projectId: string) => `/api/projects/${enc(projectId)}/flags`;
const flagUrl = (projectId: string, key: string) => `${flagsUrl(projectId)}/${enc(key)}`;

export function listFlags(projectId: string): Promise<FlagResponse[]> {
  return request(flagsUrl(projectId));
}

export function getFlag(projectId: string, key: string): Promise<FlagResponse> {
  return request(flagUrl(projectId, key));
}

export function createFlag(projectId: string, data: FlagCreate): Promise<FlagResponse> {
  return request(flagsUrl(projectId), jsonBody("POST", data));
}

export function updateFlag(projectId: string, key: string, data: FlagUpdate): Promise<FlagResponse> {
  return request(flagUrl(projectId, key), jsonBody("PUT", data));
}

export function deleteFlag(projectId: string, key: string): Promise<void> {
  return request(flagUrl(projectId, key), { method: "DELETE" });
}

export function evaluateFlag(
  projectId: string,
  key: string,
  user: Record<string, unknown>,
): Promise<EvaluateResult> {
  return request(`${flagUrl(projectId, key)}/evaluate`, jsonBody("POST", { user }));
}
