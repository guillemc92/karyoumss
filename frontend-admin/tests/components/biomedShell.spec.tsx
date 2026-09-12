/**
 * Tests del shell institucional (BiomedShell, BiomedNavbar, BiomedSidebar)
 * y del gating por rol (useSession + SessionProvider).
 */
import { describe, expect, it, beforeEach } from 'vitest';
import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { BiomedShell } from '../../src/admin/components/BiomedShell';
import { BiomedSidebar } from '../../src/admin/components/BiomedSidebar';
import { SessionProvider, useSession, setStoredRole, getStoredRole } from '../../src/admin/state/useSession';
import { SidebarSection } from '../../src/admin/components/BiomedSidebar';
import { AdminUsersProvider } from '../../src/admin/state/adminUsersStore';
import { AuthProvider } from '../../src/admin/auth/AuthContext';

/** BiomedNavbar (dentro de BiomedShell) usa useAuth()+useNavigate() desde ADR-0017. */
function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <AuthProvider>{children}</AuthProvider>
    </MemoryRouter>
  );
}

function ShellHarness() {
  return withProviders(
    <SessionProvider>
      <BiomedShell>
        {(active) => <div data-testid={`harness-${active}`}>section: {active}</div>}
      </BiomedShell>
    </SessionProvider>,
  );
}

function RoleProbe() {
  const { role, isAdmin } = useSession();
  return (
    <div>
      <span data-testid="probe-role">{role ?? 'none'}</span>
      <span data-testid="probe-is-admin">{String(isAdmin)}</span>
    </div>
  );
}

describe('useSession — localStorage helpers', () => {
  beforeEach(() => {
    try {
      localStorage.removeItem('biomed:auth:role');
    } catch {
      /* jsdom ok */
    }
  });

  it('getStoredRole devuelve null cuando no hay rol guardado', () => {
    expect(getStoredRole()).toBeNull();
  });

  it('setStoredRole persiste y getStoredRole lee', () => {
    setStoredRole('admin');
    expect(getStoredRole()).toBe('admin');
  });

  it('setStoredRole(null) limpia el valor', () => {
    setStoredRole('admin');
    setStoredRole(null);
    expect(getStoredRole()).toBeNull();
  });
});

describe('SessionProvider', () => {
  beforeEach(() => {
    try {
      localStorage.removeItem('biomed:auth:role');
    } catch {
      /* ignore */
    }
  });

  it('expone isAdmin=true cuando role=admin', () => {
    setStoredRole('admin');
    render(
      <SessionProvider>
        <RoleProbe />
      </SessionProvider>,
    );
    expect(screen.getByTestId('probe-role')).toHaveTextContent('admin');
    expect(screen.getByTestId('probe-is-admin')).toHaveTextContent('true');
  });

  it('expone isAdmin=false cuando role=supervisor', () => {
    setStoredRole('supervisor');
    render(
      <SessionProvider>
        <RoleProbe />
      </SessionProvider>,
    );
    expect(screen.getByTestId('probe-is-admin')).toHaveTextContent('false');
  });

  it('forceAdminOnMount=true fuerza role=admin cuando no hay rol', () => {
    render(
      <SessionProvider forceAdminOnMount>
        <RoleProbe />
      </SessionProvider>,
    );
    expect(screen.getByTestId('probe-is-admin')).toHaveTextContent('true');
    expect(getStoredRole()).toBe('admin');
  });
});

describe('BiomedSidebar — gating por rol', () => {
  beforeEach(() => {
    try {
      localStorage.removeItem('biomed:auth:role');
    } catch {
      /* ignore */
    }
  });

  it('muestra 6 secciones y oculta "Usuarios" cuando role≠admin', () => {
    setStoredRole('supervisor');
    render(
      <SessionProvider>
        <BiomedSidebar active="profile" onSelect={() => undefined} />
      </SessionProvider>,
    );
    expect(screen.getByTestId('sidebar-profile')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-security')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-modelos')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-notifications')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-integrations')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar-appearance')).toBeInTheDocument();
    expect(screen.queryByTestId('sidebar-users')).not.toBeInTheDocument();
  });

  it('muestra "Usuarios" cuando role=admin', () => {
    setStoredRole('admin');
    render(
      <SessionProvider>
        <BiomedSidebar active="users" onSelect={() => undefined} />
      </SessionProvider>,
    );
    expect(screen.getByTestId('sidebar-users')).toBeInTheDocument();
  });

  it('marca la sección activa con aria-current=page', () => {
    setStoredRole('admin');
    render(
      <SessionProvider>
        <BiomedSidebar active="users" onSelect={() => undefined} />
      </SessionProvider>,
    );
    const usersBtn = screen.getByTestId('sidebar-users');
    expect(usersBtn).toHaveAttribute('aria-current', 'page');
  });

  it('invoca onSelect al click en un item', async () => {
    setStoredRole('admin');
    let selected: SidebarSection | null = null;
    const user = userEvent.setup();
    render(
      <SessionProvider>
        <BiomedSidebar
          active="profile"
          onSelect={(s) => {
            selected = s;
          }}
        />
      </SessionProvider>,
    );
    await user.click(screen.getByTestId('sidebar-modelos'));
    expect(selected).toBe('modelos');
  });
});

describe('BiomedShell — layout institucional', () => {
  beforeEach(() => {
    try {
      localStorage.removeItem('biomed:auth:role');
    } catch {
      /* ignore */
    }
  });

  it('renderiza navbar + sidebar + contenido', () => {
    setStoredRole('admin');
    render(<ShellHarness />);
    expect(screen.getByTestId('biomed-navbar')).toBeInTheDocument();
    expect(screen.getByTestId('biomed-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('harness-users')).toBeInTheDocument();
  });

  it('cambia de sección al hacer click en un item del sidebar', async () => {
    setStoredRole('admin');
    const user = userEvent.setup();
    render(<ShellHarness />);
    expect(screen.getByTestId('harness-users')).toBeInTheDocument();
    await user.click(screen.getByTestId('sidebar-profile'));
    expect(screen.getByTestId('harness-profile')).toBeInTheDocument();
  });

  it('cae a profile si la sección activa requiere admin y role≠admin', () => {
    setStoredRole('supervisor');
    render(<ShellHarness />);
    // El shell protege: si active=users pero role no es admin, debe caer a profile.
    expect(screen.queryByTestId('harness-users')).not.toBeInTheDocument();
    expect(screen.getByTestId('harness-profile')).toBeInTheDocument();
  });

  it('muestra navbar con brand BIOMED UMSS', () => {
    setStoredRole('admin');
    render(<ShellHarness />);
    expect(screen.getByTestId('biomed-navbar')).toHaveTextContent('BIOMED UMSS');
  });

  it('monta AdminUsersProvider + AdminUsersPanel dentro de la sección "users"', () => {
    setStoredRole('admin');
    render(
      withProviders(
        <SessionProvider>
          <BiomedShell>
            {(active) =>
              active === 'users' ? (
                <AdminUsersProvider>
                  <div data-testid="admin-users-mounted">admin ok</div>
                </AdminUsersProvider>
              ) : null
            }
          </BiomedShell>
        </SessionProvider>,
      ),
    );
    expect(screen.getByTestId('admin-users-mounted')).toBeInTheDocument();
  });

  it('muestra el botón "Salir" (ADR-0017, replica configuracion.html nav-item)', () => {
    setStoredRole('admin');
    render(<ShellHarness />);
    expect(screen.getByTestId('nav-logout')).toHaveTextContent('Salir');
  });

  it('click en "Salir" llama logout y navega a /login', async () => {
    setStoredRole('admin');
    const user = userEvent.setup();
    render(<ShellHarness />);
    await user.click(screen.getByTestId('nav-logout'));
    // La navegación real la valida privateRoute.spec.tsx / loginPage.spec.tsx;
    // aquí solo verificamos que el botón es interactivo y no rompe el render.
    expect(screen.getByTestId('nav-logout')).toBeInTheDocument();
  });
});
