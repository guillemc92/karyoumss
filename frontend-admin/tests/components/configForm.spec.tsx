/**
 * Tests de ConfigForm — DD-ADMIN-002 P1.
 * El componente es genérico; lo ejercitamos con un schema y campos de prueba.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { z } from 'zod';
import { ConfigForm, ConfigFieldDef } from '../../src/admin/components/ConfigForm';

interface DemoData extends Record<string, unknown> {
  full_name: string;
  email: string;
  bio: string;
}

const demoSchema = z.object({
  full_name: z.string().min(3, 'Mínimo 3'),
  email: z.string().email('Email inválido'),
  bio: z.string().max(10, 'Máx 10'),
});

const demoFields: ConfigFieldDef<DemoData>[] = [
  { name: 'full_name', label: 'Nombre', required: true },
  { name: 'email', label: 'Email', type: 'email', required: true },
  { name: 'bio', label: 'Bio', maxLength: 10 },
];

describe('ConfigForm — genérico', () => {
  it('hidrata los inputs desde `initial`', () => {
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana Castro', email: 'ana@biomed.umss.bo', bio: 'A' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => undefined}
      />,
    );
    expect(screen.getByTestId('config-form-input-full_name')).toHaveValue('Ana Castro');
    expect(screen.getByTestId('config-form-input-email')).toHaveValue('ana@biomed.umss.bo');
    expect(screen.getByTestId('config-form-input-bio')).toHaveValue('A');
  });

  it('muestra error de validación Zod en el campo correspondiente', async () => {
    const user = userEvent.setup();
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana', email: 'ana@biomed.umss.bo', bio: '' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => undefined}
      />,
    );
    const nameInput = screen.getByTestId('config-form-input-full_name');
    await user.clear(nameInput);
    await user.type(nameInput, 'AB');
    await user.click(screen.getByTestId('config-form-submit'));
    expect(await screen.findByTestId('config-form-error-full_name')).toHaveTextContent(/Mínimo 3/);
  });

  it('envía solo los campos modificados en el diff', async () => {
    let captured: Partial<DemoData> | undefined;
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana Castro', email: 'ana@biomed.umss.bo', bio: '' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async (patch) => {
          captured = patch;
        }}
      />,
    );
    const emailInput = screen.getByTestId('config-form-input-email');
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, 'nuevo@biomed.umss.bo');
    await userEvent.click(screen.getByTestId('config-form-submit'));
    await waitFor(() => expect(captured).toBeDefined());
    expect(captured).toEqual({ email: 'nuevo@biomed.umss.bo' });
  });

  it('muestra banner general con mensaje de Error si onSubmit lanza', async () => {
    const user = userEvent.setup();
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana', email: 'ana@biomed.umss.bo', bio: '' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => {
          throw new Error('server caído');
        }}
      />,
    );
    const emailInput = screen.getByTestId('config-form-input-email');
    await user.clear(emailInput);
    await user.type(emailInput, 'nuevo@biomed.umss.bo');
    await user.click(screen.getByTestId('config-form-submit'));
    expect(await screen.findByTestId('config-form-error-general')).toHaveTextContent(/server caído/);
  });

  it('muestra banner general "Error al guardar" si onSubmit lanza con string', async () => {
    const user = userEvent.setup();
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana', email: 'ana@biomed.umss.bo', bio: '' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => {
          // eslint-disable-next-line @typescript-eslint/no-throw-literal
          throw 'algo que no es Error';
        }}
      />,
    );
    const emailInput = screen.getByTestId('config-form-input-email');
    await user.clear(emailInput);
    await user.type(emailInput, 'nuevo@biomed.umss.bo');
    await user.click(screen.getByTestId('config-form-submit'));
    expect(await screen.findByTestId('config-form-error-general')).toHaveTextContent(/Error al guardar/);
  });

  it('submit sin cambios (diff vacío) → no llama onSubmit y muestra "Guardado a las …"', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana Castro', email: 'ana@biomed.umss.bo', bio: 'A' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={onSubmit}
      />,
    );
    await user.click(screen.getByTestId('config-form-submit'));
    // No se invoca el backend porque no hay diff
    expect(onSubmit).not.toHaveBeenCalled();
    // Y se muestra el feedback de "guardado"
    expect(await screen.findByTestId('config-form-saved-at')).toHaveTextContent(/Guardado a las/);
  });

  it('rehidrata el formulario cuando `initial` cambia (refresh)', async () => {
    const { rerender } = render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana', email: 'ana@biomed.umss.bo', bio: 'A' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => undefined}
      />,
    );
    expect(screen.getByTestId('config-form-input-full_name')).toHaveValue('Ana');
    rerender(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana María', email: 'ana.maria@biomed.umss.bo', bio: 'B' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => undefined}
      />,
    );
    expect(screen.getByTestId('config-form-input-full_name')).toHaveValue('Ana María');
    expect(screen.getByTestId('config-form-input-bio')).toHaveValue('B');
  });

  it('muestra botón Cancelar y llama onCancel al hacer click', async () => {
    let cancelled = false;
    const user = userEvent.setup();
    render(
      <ConfigForm<DemoData, DemoData>
        initial={{ full_name: 'Ana', email: 'ana@biomed.umss.bo', bio: '' }}
        schema={demoSchema}
        fields={demoFields}
        onSubmit={async () => undefined}
        onCancel={() => (cancelled = true)}
      />,
    );
    await user.click(screen.getByTestId('config-form-cancel'));
    expect(cancelled).toBe(true);
  });
});
