export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// FastAPI sends {"detail": "..."} for HTTP errors and a list of
// {"loc": [...], "msg": "..."} entries for validation errors.
async function errorMessage(r: Response): Promise<string> {
  const text = await r.text();
  try {
    const { detail } = JSON.parse(text);
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map(d => {
          const loc = Array.isArray(d.loc) ? d.loc.filter((p: unknown) => p !== "body").join(".") : "";
          return loc ? `${loc}: ${d.msg}` : String(d.msg);
        })
        .join("; ");
    }
  } catch {
    // not JSON, fall through
  }
  return text.trim() || `Request failed (${r.status})`;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Cannot reach the Flagstone API. Is the backend running?");
  }
  if (!r.ok) throw new ApiError(r.status, await errorMessage(r));
  if (r.status === 204) return undefined as T;
  return r.json();
}

export function jsonBody(method: string, data: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  };
}

export function messageOf(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}
