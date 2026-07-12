/**
 * App shell institucional — replica el layout del `configuracion.html`
 * (navbar superior + sidebar izquierdo + slot de contenido) dentro del
 * bounded context admin (ADR-0013).
 *
 * ADR-0017: agrega enrutamiento real (react-router-dom) — ruta pública
 * `/login` y el resto de la SPA protegido por `PrivateRoute
 * allowedRoles={['admin']}`. El bootstrap de MSW envuelve TODO (incluida
 * `/login`), porque en demo el propio POST de login debe ser interceptado.
 *
 * Demo mode: si VITE_USE_MSW=true al hacer `npm run dev:msw`, el Service
 * Worker de MSW arranca antes de montar React y mockea los endpoints de
 * /api/admin/* y /api/auth/*. En prod real MSW está deshabilitado y se
 * conecta al backend via proxy de Vite.
 */
import { useEffect, useState, type ReactNode } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AdminUsersPanel } from './admin/components/AdminUsersPanel';
import { AdminUsersProvider } from './admin/state/adminUsersStore';
import { AuthProvider, useAuth } from './admin/auth/AuthContext';
import { PrivateRoute } from './admin/auth/PrivateRoute';
import { BiomedShell } from './admin/components/BiomedShell';
import { SidebarSection } from './admin/components/BiomedSidebar';
import { SessionProvider, useSession } from './admin/state/useSession';
import { LoginPage } from './admin/pages/LoginPage';
import { ProfileSection } from './admin/components/ProfileSection';
import { MswBootstrapError } from './admin/components/MswBootstrapError';

const USE_MSW = import.meta.env.VITE_USE_MSW === 'true';

function Placeholder({ icon, title, hint }: { icon: string; title: string; hint: string }) {
  return (
    <div className="biomed-placeholder" data-testid={`placeholder-${title}`}>
      <div className="biomed-placeholder__icon">
        <i className={`fas ${icon}`} aria-hidden="true" />
      </div>
      <div className="biomed-placeholder__title">{title}</div>
      <div className="biomed-placeholder__hint">{hint}</div>
    </div>
  );
}

function renderSection(section: SidebarSection) {
  if (section === 'users') {
    return (
      <AdminUsersProvider>
        <AdminUsersPanel />
      </AdminUsersProvider>
    );
  }

  // P1 (DD-ADMIN-002): sección "profile" ya tiene vista real.
  if (section === 'profile') {
    return <ProfileSection />;
  }

  const placeholders: Partial<Record<SidebarSection, { icon: string; title: string; hint: string }>> = {
    security: {
      icon: 'fa-lock',
      title: 'Seguridad',
      hint: 'Cambio de contraseña y 2FA. Vista demo.',
    },
    modelos: {
      icon: 'fa-brain',
      title: 'Modelo IA',
      hint: 'Gestión de modelos U-Net + EfficientNet-B3 + Grad-CAM. Vista demo.',
    },
    notifications: {
      icon: 'fa-bell',
      title: 'Notificaciones',
      hint: 'Preferencias de alertas. Vista demo.',
    },
    integrations: {
      icon: 'fa-plug',
      title: 'Integraciones',
      hint: 'Conexión con HIS, LIS, API. Vista demo.',
    },
    appearance: {
      icon: 'fa-palette',
      title: 'Visualización',
      hint: 'Tema y preferencias visuales. Vista demo.',
    },
  };

  const cfg = placeholders[section] ?? placeholders.security!;
  return <Placeholder {...cfg} />;
}

/** Sincroniza el rol/nombre reales de AuthContext hacia useSession (gating de UI ya existente en BiomedShell/BiomedSidebar/BiomedNavbar). */
function SessionSync() {
  const { user } = useAuth();
  const session = useSession();

  useEffect(() => {
    if (user) {
      session.setRole(user.role);
      session.setUserName(user.fullName ?? user.email);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  return null;
}

function AdminShellRoute() {
  return (
    <SessionProvider>
      <SessionSync />
      <BiomedShell>{(active) => renderSection(active)}</BiomedShell>
    </SessionProvider>
  );
}

function MswBootstrapGate({ children }: { children: ReactNode }) {
  const [mswReady, setMswReady] = useState(!USE_MSW);
  // SPEC-007 §2.3: si el SW falla, mostrar banner en vez de quedarse en
  // "Inicializando…" eternamente. `null` = bootstrap no intentado todavía.
  const [mswError, setMswError] = useState<unknown>(null);

  useEffect(() => {
    if (!USE_MSW) return;
    let cancelled = false;
    (async () => {
      try {
        const { worker } = await import('./admin/msw/browser');
        await worker.start({
          onUnhandledRequest: 'bypass',
          serviceWorker: { url: '/mockServiceWorker.js' },
          // Esperar a que el SW realmente controle la página. Sin esto, el
          // start() puede resolver antes de que el cliente esté bajo control
          // del SW y los fetch escapan al backend real (que no existe en demo).
          waitUntilReady: true,
        });
        if (!cancelled) setMswReady(true);
      } catch (err) {
        // Sin esto, errores silenciosos dan la falsa sensación de que la app
        // está OK (el dev ve "Inicializando…" para siempre). Con el banner,
        // el problema es accionable (botón "Reintentar" + link a doc).
        // eslint-disable-next-line no-console
        console.error('[MSW] worker.start() falló:', err);
        if (!cancelled) setMswError(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (mswError) {
    return (
      <MswBootstrapError
        error={mswError}
        onRetry={() => {
          setMswError(null);
          setMswReady(false);
          // El useEffect ya corrió; re-mount vía reload es la forma más
          // limpia de reintentar el bootstrap del SW.
          window.location.reload();
        }}
      />
    );
  }

  if (!mswReady) {
    return (
      <main className="biomed-main">
        <div className="biomed-page-header">
          <h2>
            <i className="fas fa-cog" aria-hidden="true" /> Configuración del Sistema
          </h2>
          <p>Inicializando mock service worker…</p>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <MswBootstrapGate>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/*"
              element={
                <PrivateRoute allowedRoles={['admin']}>
                  <AdminShellRoute />
                </PrivateRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MswBootstrapGate>
    </BrowserRouter>
  );
}
