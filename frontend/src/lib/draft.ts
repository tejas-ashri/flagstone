import type { FlagResponse, FlagRule, FlagUpdate, RuleOperator } from "../types/flag";
import { formatValue, parseValue } from "./values";

// Editable form state for a flag. Values are kept as text while editing and
// only turned into the API payload by buildUpdate().

export interface VariationDraft {
  id: number;
  text: string;
}

export interface RuleDraft {
  id: number;
  attribute: string;
  operator: RuleOperator;
  valueText: string;
  variation: number;
}

export interface RolloutDraft {
  enabled: boolean;
  variation: number;
  percentage: string;
}

export interface FlagDraft {
  variations: VariationDraft[];
  defaultVariation: number;
  rules: RuleDraft[];
  rollout: RolloutDraft;
}

let nextId = 1;
export const newId = () => nextId++;

export const OPERATORS: { value: RuleOperator; label: string; hint: string }[] = [
  { value: "equals", label: "equals", hint: "pro" },
  { value: "contains", label: "contains", hint: "@example.com" },
  { value: "in", label: "is one of", hint: "US, CA, IN" },
  { value: "gt", label: "greater than", hint: "18" },
  { value: "lt", label: "less than", hint: "65" },
];

function ruleValueText(rule: FlagRule): string {
  if (rule.operator === "in" && Array.isArray(rule.value)) {
    return rule.value.map(formatValue).join(", ");
  }
  if (rule.operator === "contains" && typeof rule.value === "string") return rule.value;
  return formatValue(rule.value);
}

export function draftFromFlag(flag: FlagResponse): FlagDraft {
  return {
    variations: flag.variations.map(v => ({ id: newId(), text: formatValue(v) })),
    defaultVariation: flag.default_variation,
    rules: flag.rules.map(r => ({
      id: newId(),
      attribute: r.attribute,
      operator: r.operator,
      valueText: ruleValueText(r),
      variation: r.variation,
    })),
    rollout: flag.rollout
      ? { enabled: true, variation: flag.rollout.variation, percentage: String(flag.rollout.percentage) }
      : { enabled: false, variation: Math.min(1, flag.variations.length - 1), percentage: "10" },
  };
}

// Stable representation without row ids, used to detect unsaved changes.
export function fingerprint(draft: FlagDraft): string {
  return JSON.stringify({
    v: draft.variations.map(v => v.text),
    d: draft.defaultVariation,
    r: draft.rules.map(r => [r.attribute, r.operator, r.valueText, r.variation]),
    o: draft.rollout.enabled ? [draft.rollout.variation, draft.rollout.percentage] : null,
  });
}

// Removes a variation and re-points everything that referenced it or a later
// index, so rules and rollout never end up pointing past the end of the list.
export function removeVariation(draft: FlagDraft, index: number): FlagDraft {
  const shift = (i: number) => (i === index ? 0 : i > index ? i - 1 : i);
  return {
    variations: draft.variations.filter((_, i) => i !== index),
    defaultVariation: shift(draft.defaultVariation),
    rules: draft.rules.map(r => ({ ...r, variation: shift(r.variation) })),
    rollout: { ...draft.rollout, variation: shift(draft.rollout.variation) },
  };
}

function parseRuleValue(rule: RuleDraft, label: string, errors: string[]): unknown {
  const text = rule.valueText.trim();
  if (!text) {
    errors.push(`${label}: a value is required.`);
    return null;
  }
  switch (rule.operator) {
    case "contains":
      return text;
    case "gt":
    case "lt": {
      const n = Number(text);
      if (!Number.isFinite(n)) errors.push(`${label}: "${text}" is not a number.`);
      return n;
    }
    case "in": {
      const items = text.split(",").map(s => s.trim()).filter(Boolean).map(parseValue);
      if (!items.length) errors.push(`${label}: list at least one value.`);
      return items;
    }
    default:
      return parseValue(text);
  }
}

export type TargetingUpdate = Required<Omit<FlagUpdate, "enabled">>;

export function buildUpdate(draft: FlagDraft): { errors: string[]; payload: TargetingUpdate | null } {
  const errors: string[] = [];
  const count = draft.variations.length;
  const inRange = (i: number) => Number.isInteger(i) && i >= 0 && i < count;

  if (count < 2) errors.push("A flag needs at least two variations.");
  const seen = new Set<string>();
  const variations = draft.variations.map((v, i) => {
    if (!v.text.trim()) errors.push(`Variation ${i} has no value.`);
    const value = parseValue(v.text);
    const fp = JSON.stringify(value);
    if (seen.has(fp)) errors.push(`Variation ${i} duplicates another variation.`);
    seen.add(fp);
    return value;
  });

  if (!inRange(draft.defaultVariation)) errors.push("Pick a default variation.");

  const rules = draft.rules.map((r, i) => {
    const label = `Rule ${i + 1}`;
    const attribute = r.attribute.trim();
    if (!attribute) errors.push(`${label}: an attribute name is required.`);
    if (!inRange(r.variation)) errors.push(`${label}: pick a variation to serve.`);
    return {
      attribute,
      operator: r.operator,
      value: parseRuleValue(r, label, errors),
      variation: r.variation,
    };
  });

  let rollout: TargetingUpdate["rollout"] = null;
  if (draft.rollout.enabled) {
    const pct = Number(draft.rollout.percentage);
    if (draft.rollout.percentage.trim() === "" || !Number.isInteger(pct) || pct < 0 || pct > 100) {
      errors.push("Rollout percentage must be a whole number from 0 to 100.");
    }
    if (!inRange(draft.rollout.variation)) errors.push("Rollout: pick a variation to serve.");
    rollout = { variation: draft.rollout.variation, percentage: pct };
  }

  if (errors.length) return { errors, payload: null };
  return {
    errors,
    payload: { variations, default_variation: draft.defaultVariation, rules, rollout },
  };
}
