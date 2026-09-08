interface StatusToggleProps {
  active: boolean;
  onChange: (next: boolean) => void;
  disabled?: boolean;
}

export function StatusToggle({ active, onChange, disabled }: StatusToggleProps) {
  return (
    <label className="biomed-status-toggle">
      <input
        type="checkbox"
        checked={active}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        data-testid={`status-toggle-${active ? 'on' : 'off'}`}
        aria-label={active ? 'Activo' : 'Inactivo'}
      />
      <span>{active ? 'Activo' : 'Inactivo'}</span>
    </label>
  );
}