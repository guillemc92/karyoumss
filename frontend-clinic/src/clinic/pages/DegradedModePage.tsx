import { Link } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';

export function DegradedModePage() {
  return (
    <BiomedShell>
      <div role="alert" className="degraded-banner">
        <h1>⚠️ Modo Degradado — Pipeline de IA no disponible</h1>
        <p>El pipeline de inferencia (U-Net + EfficientNet) no responde. Esto puede deberse a mantenimiento programado o falla del servidor.</p>
        <h3>¿Qué puede hacer?</h3>
        <ol>
          <li>Las muestras existentes siguen disponibles para consulta.</li>
          <li>Puede crear nuevas muestras (quedan en PENDING_AI).</li>
          <li>No puede disparar el pipeline automático.</li>
          <li>
            Para análisis manual: descargue la imagen desde S3, use la herramienta de
            análisis externo (recurso IT), e ingrese el resultado manualmente en el
            visor vanilla (<code>correccion de cariotipo.html</code>).
          </li>
        </ol>
        <Link to="/clinic/samples">← Volver a la lista</Link>
      </div>
    </BiomedShell>
  );
}
