import { useEffect } from 'react';

export type ToastKind = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  kind?: ToastKind;
  onDismiss: () => void;
  autoDismissMs?: number;
}

export function Toast({ message, kind = 'info', onDismiss, autoDismissMs = 4000 }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(onDismiss, autoDismissMs);
    return () => clearTimeout(t);
  }, [onDismiss, autoDismissMs]);

  return (
    <div role="status" className="toast" data-kind={kind}>
      <span>{message}</span>
      <button type="button" aria-label="Cerrar" onClick={onDismiss}>✕</button>
    </div>
  );
}
