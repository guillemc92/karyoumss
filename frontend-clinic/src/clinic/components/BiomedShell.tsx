import { Link } from 'react-router-dom';
import { useSession } from '../auth';
import { RoleBadge } from './RoleBadge';

interface BiomedShellProps {
  children: React.ReactNode;
}

export function BiomedShell({ children }: BiomedShellProps) {
  const { role, username, logout } = useSession();

  return (
    <div className="biomed-shell">
      <nav className="navbar">
        <Link to="/clinic/samples" className="nav-brand">
          <strong>BIOMED UMSS</strong>
          <span className="role-tag">MUESTRAS</span>
        </Link>
        <div className="user-info">
          {username && <span className="user-name">{username}</span>}
          {role && <RoleBadge role={role} />}
          <button type="button" onClick={logout}>Salir</button>
        </div>
      </nav>
      <main className="main-container">{children}</main>
    </div>
  );
}
