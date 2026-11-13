import type { FlagCreate, FlagResponse, FlagUpdate } from "../types/flag";
import { jsonBody, request } from "./http";

const BASE = "/api";

const flagUrl = (key: string) => `${BASE}/flags/${encodeURIComponent(key)}`;

export function listFlags(): Promise<FlagResponse[]> {
  return request(`${BASE}/flags`);
}

export function createFlag(data: FlagCreate): Promise<FlagResponse> {
  return request(`${BASE}/flags`, jsonBody("POST", data));
}

export function updateFlag(key: string, data: FlagUpdate): Promise<FlagResponse> {
  return request(flagUrl(key), jsonBody("PUT", data));
}

export function deleteFlag(key: string): Promise<void> {
  return request(flagUrl(key), { method: "DELETE" });
}
