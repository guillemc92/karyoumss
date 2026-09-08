import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from '../../src/admin/auth/AuthContext';
import * as authClient from '../../src/admin/auth/authClient';

const DEMO_ADMIN = { email: 'demo_admin@biomed.umss.bo', password: 'demo12345' };

function Probe() {
  const { user, isLoading, isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="role">{user?.role ?? 'none'}</span>
      <button onClick={() => login(DEMO_ADMIN.email, DEMO_ADMIN.password)}>login</button>
      <button onClick={() => { login('bad@biomed.umss.bo', 'bad').catch(() => undefined); }}>
        login-bad
      </button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

describe('AuthContext (ADR-0017)', () => {
  beforeEach(() => {
    authClient.clearTokens();
  });
  afterEach(() => {
    authClient.clearTokens();
    vi.useRealTimers();
  });

  it('sin tokens en localStorage: isLoading termina en false, no autenticado', async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
  });

  it('login exitoso actualiza user y authenticated', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    await user.click(screen.getByText('login'));
    await waitFor(() => expect(screen.getByTestId('authenticated')).toHaveTextContent('true'));
    expect(screen.getByTestId('role')).toHaveTextContent('admin');
  });

  it('login fallido no autentica y propaga el error', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    await user.click(screen.getByText('login-bad'));
    await waitFor(() => expect(screen.getByTestId('authenticated')).toHaveTextContent('false'));
  });

  it('logout limpia user y authenticated', async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    await user.click(screen.getByText('login'));
    await waitFor(() => expect(screen.getByTestId('authenticated')).toHaveTextContent('true'));
    await user.click(screen.getByText('logout'));
    await waitFor(() => expect(screen.getByTestId('authenticated')).toHaveTextContent('false'));
  });

  it('hidrata la sesión al montar si ya hay un access token válido en localStorage', async () => {
    // Login "fuera de React" para simular una recarga de página con sesión previa.
    await authClient.login(DEMO_ADMIN.email, DEMO_ADMIN.password);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('role')).toHaveTextContent('admin');
  });

  it('useAuth fuera de AuthProvider lanza', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    expect(() => render(<Probe />)).toThrow('useAuth debe usarse dentro de <AuthProvider>');
    consoleError.mockRestore();
  });
});
