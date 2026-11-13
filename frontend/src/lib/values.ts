// Variation and rule values are arbitrary JSON. In the UI they are edited as
// text: anything that parses as JSON is taken as that value (true, 42, {"a":1}),
// anything else is a plain string. Strings that would otherwise be read back
// as JSON (e.g. the string "true") are shown quoted so the round trip is exact.

export function parseValue(text: string): unknown {
  const trimmed = text.trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed;
  }
}

export function formatValue(value: unknown): string {
  if (typeof value !== "string") return JSON.stringify(value) ?? "";
  if (value === "" || value !== value.trim()) return JSON.stringify(value);
  try {
    JSON.parse(value);
    return JSON.stringify(value);
  } catch {
    return value;
  }
}

export function valueType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "list";
  if (typeof value === "object") return "json";
  return typeof value;
}
