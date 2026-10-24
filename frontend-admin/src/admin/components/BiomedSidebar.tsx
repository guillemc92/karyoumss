import { useSession } from '../state/useSession';

export type SidebarSection =
  | 'profile'
  | 'security'
  | 'modelos'
  | 'notifications'
  | 'integrations'
  | 'appearance'
  | 'users';

interface SectionConfig {
  id: SidebarSection;
  label: string;
  sublabel: string;
  icon: string; // FontAwesome class sin prefijo "fa-"
  iconColor: 'blue' | 'green' | 'yellow' | 'light-blue' | 'red' | 'purple' | 'neural';
  /** Si true, solo se muestra a usuarios con role=admin. */
  adminOnly?: boolean;
}

const SECTIONS: SectionConfig[] = [
  { id: 'profile', label: 'Perfil de Usuario', sublabel: 'Datos personales', icon: 'fa-user', iconColor: 'blue' },
  { id: 'security', label: 'Seguridad', sublabel: 'Privacidad y acceso', icon: 'fa-lock', iconColor: 'red' },
  { id: 'modelos', label: 'Modelo IA', sublabel: 'Algoritmos y precisión', icon: 'fa-brain', iconColor: 'neural' },
  { id: 'notifications', label: 'Notificaciones', sublabel: 'Alertas y avisos', icon: 'fa-bell', iconColor: 'yellow' },
  { id: 'integrations', label: 'Integraciones', sublabel: 'HIS, LIS, API', icon: 'fa-plug', iconColor: 'light-blue' },
  { id: 'appearance', label: 'Visualización', sublabel: 'Tema y preferencias', icon: 'fa-palette', iconColor: 'purple' },
  { id: 'users', label: 'Usuarios', sublabel: 'Gestión institucional', icon: 'fa-users-cog', iconColor: 'purple', adminOnly: true },
];

interface BiomedSidebarProps {
  active: SidebarSection;
  onSelect: (section: SidebarSection) => void;
}

export function BiomedSidebar({ active, onSelect }: BiomedSidebarProps) {
  const { isAdmin } = useSession();

  return (
    <aside className="biomed-config-sidebar" data-testid="biomed-sidebar">
      <div className="biomed-config-nav">
        <div className="biomed-config-nav-title">CONFIGURACIÓN</div>
        {SECTIONS.filter((s) => !s.adminOnly || isAdmin).map((section) => {
          const isActive = active === section.id;
          return (
            <button
              key={section.id}
              type="button"
              className={`biomed-config-nav-item${isActive ? ' active' : ''}`}
              onClick={() => onSelect(section.id)}
              data-testid={`sidebar-${section.id}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className={`biomed-config-nav-icon ${section.iconColor}`}>
                <i className={`fas ${section.icon}`} aria-hidden="true" />
              </div>
              <div className="biomed-config-nav-text">
                <div className="biomed-config-nav-label">{section.label}</div>
                <div className="biomed-config-nav-sublabel">{section.sublabel}</div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="biomed-config-version">
        <div className="biomed-config-version-title">Versión del Sistema</div>
        <div className="biomed-config-version-number">Biomed v2.4.1</div>
        <div className="biomed-config-version-date">Build 2026.04.10 · Demo</div>
        <div className="biomed-config-status">
          <div className="biomed-config-status-dot" />
          <span className="biomed-config-status-text">Demo MSW activa</span>
        </div>
      </div>
    </aside>
  );
}

export const SIDEBAR_SECTIONS = SECTIONS;
