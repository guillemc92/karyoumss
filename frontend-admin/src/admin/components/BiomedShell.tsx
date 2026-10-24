import { ReactNode, useState } from 'react';
import { BiomedNavbar } from './BiomedNavbar';
import { BiomedSidebar, SidebarSection, SIDEBAR_SECTIONS } from './BiomedSidebar';
import { useSession } from '../state/useSession';

interface BiomedShellProps {
  /** Slot para el contenido principal (panel, placeholders, etc.). */
  children: (active: SidebarSection) => ReactNode;
}

/**
 * Shell institucional — replica la estructura del `configuracion.html`:
 * Navbar superior + grid 280px sidebar + contenido principal.
 *
 * Si la sección activa requiere admin y el rol actual no es admin,
 * cae a la primera sección no restringida (no rompe la demo).
 */
export function BiomedShell({ children }: BiomedShellProps) {
  const { isAdmin } = useSession();
  const [active, setActive] = useState<SidebarSection>('users');

  function handleSelect(section: SidebarSection) {
    setActive(section);
  }

  function handleNav(target: 'configuracion' | 'admin' | 'index') {
    if (target === 'index') {
      // Sin router: en demo solo cambiamos a la vista de perfil como fallback.
      setActive('profile');
    } else if (target === 'configuracion') {
      setActive('profile');
    } else if (target === 'admin') {
      setActive('users');
    }
  }

  // Sanity: si la sección activa requiere admin y el rol no es admin, caer a profile.
  const activeSection = SIDEBAR_SECTIONS.find((s) => s.id === active);
  const safeActive: SidebarSection =
    activeSection && (!activeSection.adminOnly || isAdmin) ? active : 'profile';

  const titleMap: Record<SidebarSection, { title: string; subtitle: string }> = {
    profile: { title: 'Perfil de Usuario', subtitle: 'Actualiza tu información personal y credenciales' },
    security: { title: 'Seguridad', subtitle: 'Gestiona tu contraseña y métodos de autenticación' },
    modelos: { title: 'Modelo IA', subtitle: 'Gestiona y configura los modelos de inteligencia artificial' },
    notifications: { title: 'Notificaciones', subtitle: 'Configura tus preferencias de alertas y avisos' },
    integrations: { title: 'Integraciones', subtitle: 'Conecta Biomed con HIS, LIS y sistemas externos' },
    appearance: { title: 'Visualización', subtitle: 'Personaliza el tema y las preferencias visuales' },
    users: { title: 'Usuarios Institucionales', subtitle: 'Gestión de cuentas (solo Administrador TI)' },
  };

  const navActive: 'configuracion' | 'admin' = safeActive === 'users' ? 'admin' : 'configuracion';

  return (
    <div className="biomed-app-shell" data-testid="biomed-shell">
      <BiomedNavbar activeNav={navActive} onNav={handleNav} />
      <main className="biomed-main">
        <div className="biomed-page-header">
          <h2>
            <i className="fas fa-cog" aria-hidden="true" /> Configuración del Sistema
          </h2>
          <p>Personaliza tu experiencia y ajusta los parámetros del sistema</p>
        </div>

        <div className="biomed-config-layout">
          <BiomedSidebar active={safeActive} onSelect={handleSelect} />

          <section className="biomed-config-content" data-testid={`shell-content-${safeActive}`}>
            <header className="biomed-config-content-header">
              <div className="biomed-config-content-title">{titleMap[safeActive].title}</div>
              <div className="biomed-config-content-subtitle">{titleMap[safeActive].subtitle}</div>
            </header>
            <div className="biomed-config-content-body">{children(safeActive)}</div>
          </section>
        </div>
      </main>
    </div>
  );
}
