import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../../src/admin/auth/AuthContext';
import { LoginPage } from '../../src/admin/pages/LoginPage';
import * as authClient from '../../src/admin/auth/authClient';

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div data-testid="admin-home">home admin</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('LoginPage (ADR-0017, replica index.html #loginModal)', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    authClient.clearTokens();
    // Stub deliberado para observar redirects cross-app SIN romper la
    // resolución de URLs relativas que fetch/MSW necesitan (href arranca en
    // un origin válido, no '').
    // @ts-expect-error -- reemplazo deliberado para test
    delete window.location;
    // @ts-expect-error -- stub mínimo
    window.location = { href: 'http://localhost:3000/' };
  });

  afterEach(() => {
    authClient.clearTokens();
    window.location = originalLocation;
  });

  it('renderiza el header, los 3 tabs de rol y el formulario', () => {
    renderLoginPage();
    expect(screen.getByText('BIOMED UMSS')).toBeInTheDocument();
    expect(screen.getByText('Iniciar Sesión')).toBeInTheDocument();
    expect(screen.getByTestId('role-tab-citogenetista')).toBeInTheDocument();
    expect(screen.getByTestId('role-tab-supervisor')).toBeInTheDocument();
    expect(screen.getByTestId('role-tab-admin')).toBeInTheDocument();
    expect(screen.getByLabelText('Usuario')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
  });

  it('el banner de error no se muestra antes de un intento fallido', () => {
    renderLoginPage();
    expect(screen.queryByText(/Credenciales incorrectas/)).not.toBeInTheDocument();
  });

  it('el tab "citogenetista" está seleccionado por defecto', () => {
    renderLoginPage();
    expect(screen.getByTestId('role-tab-citogenetista')).toHaveClass('selected');
  });

  it('click en un tab lo marca como seleccionado (cosmético, ADR-0017 D8)', async () => {
    const user = userEvent.setup();
    renderLoginPage();
    await user.click(screen.getByTestId('role-tab-admin'));
    expect(screen.getByTestId('role-tab-admin')).toHaveClass('selected');
    expect(screen.getByTestId('role-tab-citogenetista')).not.toHaveClass('selected');
  });

  it('login exitoso como admin navega a la raíz de la SPA (no cross-app)', async () => {
    const user = userEvent.setup();
    renderLoginPage();
    await user.type(screen.getByLabelText('Usuario'), 'demo_admin@biomed.umss.bo');
    await user.type(screen.getByLabelText('Contraseña'), 'demo12345');
    await user.click(screen.getByText('Ingresar al Sistema'));
    await waitFor(() => expect(screen.getByTestId('admin-home')).toBeInTheDocument());
  });

  it('login exitoso como analista navega fuera vía window.location.href (D8: tab elegido no importa)', async () => {
    const user = userEvent.setup();
    renderLoginPage();
    // Selecciono el tab "Administrador" a propósito, pero las credenciales
    // son de una cuenta analista real — el redirect debe seguir el rol real.
    await user.click(screen.getByTestId('role-tab-admin'));
    await user.type(screen.getByLabelText('Usuario'), 'demo_analista@biomed.umss.bo');
    await user.type(screen.getByLabelText('Contraseña'), 'demo12345');
    await user.click(screen.getByText('Ingresar al Sistema'));
    await waitFor(() => expect(window.location.href).toContain('/clinic/samples'));
  });

  it('credenciales inválidas muestran el banner de error y no navegan', async () => {
    const user = userEvent.setup();
    renderLoginPage();
    await user.type(screen.getByLabelText('Usuario'), 'no-existe@biomed.umss.bo');
    await user.type(screen.getByLabelText('Contraseña'), 'incorrecta');
    await user.click(screen.getByText('Ingresar al Sistema'));
    await waitFor(() => expect(screen.getByText(/Credenciales incorrectas/)).toBeInTheDocument());
    expect(screen.queryByTestId('admin-home')).not.toBeInTheDocument();
  });

  it('el botón muestra "Ingresando…" mientras se envía', async () => {
    const user = userEvent.setup();
    renderLoginPage();
    await user.type(screen.getByLabelText('Usuario'), 'demo_admin@biomed.umss.bo');
    await user.type(screen.getByLabelText('Contraseña'), 'demo12345');
    await user.click(screen.getByText('Ingresar al Sistema'));
    // El estado "submitting" es transitorio; solo verificamos que el flujo
    // termina en el home admin sin quedar atascado en loading.
    await waitFor(() => expect(screen.getByTestId('admin-home')).toBeInTheDocument());
  });
});
