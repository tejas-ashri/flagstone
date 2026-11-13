interface Props {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
}

export function Toggle({ checked, onChange, label, disabled }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      title={label}
      disabled={disabled}
      className={`toggle${checked ? " on" : ""}`}
      onClick={e => {
        e.stopPropagation();
        onChange(!checked);
      }}
    >
      <span className="toggle-knob" />
    </button>
  );
}
