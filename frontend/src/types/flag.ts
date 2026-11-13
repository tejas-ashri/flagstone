export type RuleOperator = "equals" | "contains" | "gt" | "lt" | "in";

export interface FlagRule {
  attribute: string;
  operator: RuleOperator;
  value: unknown;
  variation: number;
}

export interface FlagRollout {
  variation: number;
  percentage: number;
}

export interface FlagResponse {
  key: string;
  enabled: boolean;
  variations: unknown[];
  default_variation: number;
  rules: FlagRule[];
  rollout: FlagRollout | null;
  updated_at: string;
}

export type FlagCreate = Omit<FlagResponse, "updated_at">;

export type FlagUpdate = Partial<Omit<FlagCreate, "key">>;

export interface VariationResult {
  variation_index: number;
  exposures: number;
  conversions: number;
  conversion_rate_pct: number | null;
}

export interface ExperimentResults {
  flag_key: string;
  variations: VariationResult[];
}
