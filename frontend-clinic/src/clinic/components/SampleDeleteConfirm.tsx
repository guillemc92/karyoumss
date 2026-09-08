interface SampleDeleteConfirmProps {
  chnCode: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export function SampleDeleteConfirm({ chnCode, onConfirm, onCancel, isDeleting }: SampleDeleteConfirmProps) {
  return (
    <div role="dialog" aria-modal="true" className="modal-overlay">
      <div className="modal-content modal-content--small">
        <h3>Eliminar Muestra</h3>
        <p>¿Está seguro de eliminar la muestra <strong>{chnCode}</strong>?</p>
        <p className="hint">Esta acción no se puede deshacer.</p>
        <div className="modal-actions">
          <button type="button" onClick={onCancel}>Cancelar</button>
          <button type="button" className="btn-danger" onClick={onConfirm} disabled={isDeleting}>
            {isDeleting ? 'Eliminando...' : 'Eliminar'}
          </button>
        </div>
      </div>
    </div>
  );
}
