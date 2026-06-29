import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AdminUsersPanel } from '../../src/admin/components/AdminUsersPanel';
import { AdminUsersProvider } from '../../src/admin/state/adminUsersStore';
import { setAuthToken } from '../../src/admin/api/adminClient';

function renderPanel() {
  return render(
    <AdminUsersProvider>
      <AdminUsersPanel />
    </AdminUsersProvider>,
  );
}

describe('AdminUsersPanel — integración con MSW', () => {
  beforeEach(() => {
    setAuthToken(null);
  });

  it('carga la lista y muestra usuarios activos', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Ana Castro')).toBeInTheDocument();
    });
    expect(screen.getByText('Bruno Pinto')).toBeInTheDocument();
    expect(screen.queryByText('Carla Méndez')).not.toBeInTheDocument(); // está inactive
  });

  it('abre el formulario al click en "Nuevo usuario"', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('new-user'));
    expect(screen.getByTestId('user-form')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Nuevo usuario' })).toBeInTheDocument();
  });

  it('cierra el formulario al cancelar', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('new-user'));
    await user.click(screen.getByTestId('cancel-user'));
    expect(screen.queryByTestId('user-form')).not.toBeInTheDocument();
  });

  it('crea un usuario y aparece en la tabla', async () => {
    const user = userEvent.setup();
    renderPanel();
    await screen.findByText('Ana Castro');
    await user.click(screen.getByTestId('new-user'));
    await user.type(screen.getByTestId('input-full_name'), 'Daniel Quispe');
    await user.type(screen.getByTestId('input-email'), 'daniel.quispe@biomed.umss.bo');
    await user.selectOptions(screen.getByTestId('select-role'), 'analista');
    await user.click(screen.getByTestId('submit-user'));
    await waitFor(() => {
      expect(screen.getByText('Daniel Quispe')).toBeInTheDocument();
    });
  });
});