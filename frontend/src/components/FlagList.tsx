import type { FlagResponse } from "../types/flag";
import { Toggle } from "./Toggle";

interface Props {
  flags: FlagResponse[];
  selected: string | null;
  onSelect: (key: string) => void;
  onToggle: (flag: FlagResponse) => void;
}

function summary(flag: FlagResponse): string {
  const parts = [];
  if (flag.rules.length) parts.push(`${flag.rules.length} rule${flag.rules.length === 1 ? "" : "s"}`);
  if (flag.rollout) parts.push(`${flag.rollout.percentage}% rollout`);
  if (!parts.length) parts.push("default only");
  return parts.join(" · ");
}

export function FlagList({ flags, selected, onSelect, onToggle }: Props) {
  return (
    <ul className="flag-list">
      {flags.map(f => (
        <li key={f.key}>
          <div
            role="button"
            tabIndex={0}
            className={`flag-item${f.key === selected ? " selected" : ""}`}
            onClick={() => onSelect(f.key)}
            onKeyDown={e => {
              if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                e.preventDefault();
                onSelect(f.key);
              }
            }}
          >
            <div className="flag-item-text">
              <code className="flag-key">{f.key}</code>
              <span className="muted small">{summary(f)}</span>
            </div>
            <Toggle
              checked={f.enabled}
              onChange={() => onToggle(f)}
              label={f.enabled ? `Turn ${f.key} off` : `Turn ${f.key} on`}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
