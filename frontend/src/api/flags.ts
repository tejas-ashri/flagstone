import type { FlagResponse } from "../types/flag";

const BASE = "/api";

export async function listFlags(): Promise<FlagResponse[]> {
  const r = await fetch(`${BASE}/flags`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function createFlag(data: Partial<FlagResponse>): Promise<FlagResponse> {
  const r = await fetch(`${BASE}/flags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function updateFlag(key: string, data: Partial<FlagResponse>): Promise<FlagResponse> {
  const r = await fetch(`${BASE}/flags/${key}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteFlag(key: string): Promise<void> {
  const r = await fetch(`${BASE}/flags/${key}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`Failed to delete flag: ${r.status}`);
}
