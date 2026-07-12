import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useSession } from '../state/useSession';

interface BiomedNavbarProps {
  activeNav: 'configuracion' | 'admin';
  onNav: (target: 'configuracion' | 'admin' | 'index') => void;
}

/**
 * Navbar superior azul UMSS — replica el shell del `configuracion.html`.
 * Sticky, con brand "BIOMED UMSS / INTELLIGENT KARYOTYPING", nav-links
 * y user-info en la derecha. data-testid estables para tests.
 */
export function BiomedNavbar({ activeNav, onNav }: BiomedNavbarProps) {
  const { userName, role } = useSession();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const displayName = userName ?? 'Dra. María López';
  const displayRole = role === 'admin' ? 'Administrador TI' : 'Garante Clínico';

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <nav className="biomed-navbar" data-testid="biomed-navbar">
      <button
        type="button"
        className="biomed-nav-brand"
        onClick={() => onNav('index')}
        data-testid="nav-brand"
        style={{ background: 'none', border: 'none', cursor: 'pointer' }}
      >
        <i className="fas fa-dna fa-lg" aria-hidden="true" />
        <div>
          <h1>BIOMED UMSS</h1>
          <small>INTELLIGENT KARYOTYPING</small>
        </div>
        <span className="biomed-nav-tag">ADMINISTRACIÓN</span>
      </button>

      <div className="biomed-nav-links">
        <button
          type="button"
          className={`biomed-nav-link${activeNav === 'configuracion' ? ' active' : ''}`}
          onClick={() => onNav('configuracion')}
          data-testid="nav-configuracion"
        >
          <i className="fas fa-cog" aria-hidden="true" /> Configuración
        </button>
        <button
          type="button"
          className={`biomed-nav-link${activeNav === 'admin' ? ' active' : ''}`}
          onClick={() => onNav('admin')}
          data-testid="nav-admin"
        >
          <i className="fas fa-users-cog" aria-hidden="true" /> Panel Admin
        </button>
      </div>

      <div className="biomed-user-info" data-testid="navbar-user">
        <div className="biomed-user-name">{displayName}</div>
        <div className="biomed-user-role">{displayRole}</div>
      </div>

      <button
        type="button"
        className="biomed-nav-link"
        onClick={handleLogout}
        data-testid="nav-logout"
      >
        <i className="fas fa-sign-out-alt" aria-hidden="true" /> Salir
      </button>
    </nav>
  );
}
