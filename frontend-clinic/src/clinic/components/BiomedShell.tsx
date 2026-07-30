import { Link, useLocation } from 'react-router-dom';
import { useSession } from '../auth';

interface BiomedShellProps {
  children: React.ReactNode;
}

const ROLE_LABELS: Record<string, string> = {
  analista: 'Analista',
  supervisor: 'Supervisor',
  admin: 'Administrador',
};

export function BiomedShell({ children }: BiomedShellProps) {
  const { role, username, logout } = useSession();
  const location = useLocation();
  const isSamplesActive = location.pathname.startsWith('/clinic/samples');
  // La bandeja es del Supervisor (RN-06): al analista no le toca ese trabajo.
  const isSupervisor = role === 'supervisor' || role === 'admin';
  const isInboxActive = location.pathname.startsWith('/clinic/supervisor');

  return (
    <div className="biomed-shell">
      <nav className="navbar">
        <Link to="/clinic/samples" className="nav-brand">
          <i className="fas fa-dna fa-lg"></i>
          <div>
            <strong>BIOMED UMSS</strong>
            <div style={{ fontSize: '0.6rem' }}>INTELLIGENT KARYOTYPING</div>
          </div>
          <span className="role-tag">CRUD MUESTRAS</span>
        </Link>
        <div className="nav-links">
          <Link to="/clinic/samples" className={`nav-item${isSamplesActive ? ' active' : ''}`}>
            <i className="fas fa-flask"></i> Muestras
          </Link>
          {isSupervisor && (
            <Link to="/clinic/supervisor" className={`nav-item${isInboxActive ? ' active' : ''}`} data-testid="nav-supervisor-inbox">
              <i className="fas fa-user-check"></i> Bandeja
            </Link>
          )}
          <Link to="/clinic/degraded" className="nav-item">
            <i className="fas fa-exclamation-triangle"></i> Modo Manual
          </Link>
        </div>
        <div className="user-info">
          {username && <span className="user-name">{username}</span>}
          {role && <span className="role-badge">{ROLE_LABELS[role] ?? role}</span>}
          <button type="button" onClick={logout}>
            <i className="fas fa-sign-out-alt"></i> Salir
          </button>
        </div>
      </nav>
      <div className="main-container">{children}</div>
    </div>
  );
}
