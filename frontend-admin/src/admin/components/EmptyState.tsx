interface EmptyStateProps {
  title: string;
  hint?: string;
  testId?: string;
}

export function EmptyState({ title, hint, testId }: EmptyStateProps) {
  return (
    <div className="biomed-empty-state" data-testid={testId ?? 'empty-state'}>
      <p className="biomed-empty-state__title">{title}</p>
      {hint && <p className="biomed-empty-state__hint">{hint}</p>}
    </div>
  );
}