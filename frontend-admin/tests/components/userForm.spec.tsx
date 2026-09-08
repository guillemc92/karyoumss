import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserForm } from '../../src/admin/components/UserForm';

const STRONG_PW = 'StrongPass1234';

describe('UserForm — validación', () => {
  beforeEach(() => {});

  it('muestra error si nombre <2 caracteres', async () => {
    const user = userEvent.setup();
    render(<UserForm onSubmit={() => Promise.resolve()} onCancel={() => undefined} />);
    await user.type(screen.getByTestId('input-full_name'), 'A');
    await user.type(screen.getByTestId('input-email'), 'test@biomed.umss.bo');
    await user.click(screen.getByTestId('submit-user'));
    expect(screen.getByTestId('error-full_name')).toHaveTextContent(/al menos 2/);
  });

  it('muestra error si email vacío en modo creación', async () => {
    const user = userEvent.setup();
    render(<UserForm onSubmit={() => Promise.resolve()} onCancel={() => undefined} />);
    await user.type(screen.getByTestId('input-full_name'), 'Válido Nombre');
    // email vacío
    await user.click(screen.getByTestId('submit-user'));
    expect(screen.getByTestId('error-email')).toHaveTextContent(/obligatorio/);
  });

  it('muestra error si email no tiene formato', async () => {
    const user = userEvent.setup();
    render(<UserForm onSubmit={() => Promise.resolve()} onCancel={() => undefined} />);
    await user.type(screen.getByTestId('input-full_name'), 'Válido Nombre');
    await user.type(screen.getByTestId('input-email'), 'no-es-email');
    await user.click(screen.getByTestId('submit-user'));
    expect(screen.getByTestId('error-email')).toHaveTextContent(/inválido/);
  });

  it('muestra error si la contraseña es débil (corta)', async () => {
    const user = userEvent.setup();
    render(<UserForm onSubmit={() => Promise.resolve()} onCancel={() => undefined} />);
    await user.type(screen.getByTestId('input-full_name'), 'Válido Nombre');
    await user.type(screen.getByTestId('input-email'), 'test@biomed.umss.bo');
    await user.type(screen.getByTestId('input-password'), 'short1A');
    await user.type(screen.getByTestId('input-confirm-password'), 'short1A');
    await user.click(screen.getByTestId('submit-user'));
    expect(screen.getByTestId('error-password')).toHaveTextContent(/12 caracteres/);
  });

  it('muestra error si la contraseña no coincide con la confirmación', async () => {
    const user = userEvent.setup();
    render(<UserForm onSubmit={() => Promise.resolve()} onCancel={() => undefined} />);
    await user.type(screen.getByTestId('input-full_name'), 'Válido Nombre');
    await user.type(screen.getByTestId('input-email'), 'test@biomed.umss.bo');
    await user.type(screen.getByTestId('input-password'), STRONG_PW);
    await user.type(screen.getByTestId('input-confirm-password'), 'Different1234');
    await user.click(screen.getByTestId('submit-user'));
    expect(screen.getByTestId('error-confirm-password')).toHaveTextContent(/no coincide/i);
  });

  it('llama onSubmit con draft válido (incluye password)', async () => {
    let captured: { full_name: string; email: string; role: string; active: boolean; password: string } | null = null;
    const user = userEvent.setup();
    render(
      <UserForm
        onSubmit={async (draft) => {
          captured = draft;
        }}
        onCancel={() => undefined}
      />,
    );
    await user.type(screen.getByTestId('input-full_name'), 'Lucía Vargas');
    await user.type(screen.getByTestId('input-email'), 'lucia@biomed.umss.bo');
    await user.type(screen.getByTestId('input-password'), STRONG_PW);
    await user.type(screen.getByTestId('input-confirm-password'), STRONG_PW);
    await user.selectOptions(screen.getByTestId('select-role'), 'supervisor');
    await user.click(screen.getByTestId('submit-user'));
    await waitFor(() => expect(captured).not.toBeNull());
    expect(captured).toEqual({
      full_name: 'Lucía Vargas',
      email: 'lucia@biomed.umss.bo',
      role: 'supervisor',
      active: true,
      password: STRONG_PW,
    });
  });

  it('email es readOnly en modo edición y no muestra campos de password', () => {
    render(
      <UserForm
        editing={{
          id: 'x',
          full_name: 'Edit User',
          email: 'edit@biomed.umss.bo',
          role: 'analista',
          active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          created_by: null,
        }}
        onSubmit={() => Promise.resolve()}
        onCancel={() => undefined}
      />,
    );
    expect(screen.getByTestId('input-email')).toHaveAttribute('readonly');
    expect(screen.queryByTestId('input-password')).not.toBeInTheDocument();
    expect(screen.queryByTestId('input-confirm-password')).not.toBeInTheDocument();
  });

  it('llama onCancel al click en cancelar', async () => {
    let cancelled = false;
    const user = userEvent.setup();
    render(
      <UserForm
        onSubmit={() => Promise.resolve()}
        onCancel={() => (cancelled = true)}
      />,
    );
    await user.click(screen.getByTestId('cancel-user'));
    expect(cancelled).toBe(true);
  });

  it('muestra error general si onSubmit lanza', async () => {
    const user = userEvent.setup();
    render(
      <UserForm
        onSubmit={async () => {
          throw new Error('server caído');
        }}
        onCancel={() => undefined}
      />,
    );
    await user.type(screen.getByTestId('input-full_name'), 'Válido Nombre');
    await user.type(screen.getByTestId('input-email'), 'ok@biomed.umss.bo');
    await user.type(screen.getByTestId('input-password'), STRONG_PW);
    await user.type(screen.getByTestId('input-confirm-password'), STRONG_PW);
    await user.click(screen.getByTestId('submit-user'));
    await waitFor(() =>
      expect(screen.getByTestId('error-general')).toHaveTextContent(/server caído/),
    );
  });

  it('muestra error general "Error al guardar" si onSubmit lanza con string', async () => {
    const user = userEvent.setup();
    render(
      <UserForm
        onSubmit={async () => {
          // eslint-disable-next-line @typescript-eslint/no-throw-literal
          throw 'algo';
        }}
        onCancel={() => undefined}
      />,
    );
    await user.type(screen.getByTestId('input-full_name'), 'Válido Nombre');
    await user.type(screen.getByTestId('input-email'), 'ok@biomed.umss.bo');
    await user.type(screen.getByTestId('input-password'), STRONG_PW);
    await user.type(screen.getByTestId('input-confirm-password'), STRONG_PW);
    await user.click(screen.getByTestId('submit-user'));
    await waitFor(() =>
      expect(screen.getByTestId('error-general')).toHaveTextContent(/Error al guardar/),
    );
  });
});
