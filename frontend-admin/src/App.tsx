/**
 * App shell — Bootstrap.
 *
 * Por ahora es un shell mínimo que monta el panel de usuarios del bounded context admin.
 * Cuando se integre con el auth_bridge (F7), aquí vivirá la lectura del token Django y
 * el bootstrap del contexto de sesión.
 */
import { AdminUsersPanel } from './admin/components/AdminUsersPanel';
import { AdminUsersProvider } from './admin/state/adminUsersStore';

export default function App() {
  return (
    <main className="biomed-admin">
      <header className="biomed-admin__header">
        <h1>BIOMED UMSS — Panel de Administración</h1>
        <p className="biomed-admin__subtitle">
          Bounded context <code>admin</code> · ADR-0013
        </p>
      </header>
      <AdminUsersProvider>
        <AdminUsersPanel />
      </AdminUsersProvider>
    </main>
  );
}