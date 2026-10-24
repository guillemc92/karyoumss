import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RoleBadge } from '../../src/admin/components/RoleBadge';
import { StatusToggle } from '../../src/admin/components/StatusToggle';
import { EmptyState } from '../../src/admin/components/EmptyState';

describe('RoleBadge', () => {
  it('renderiza etiqueta de analista', () => {
    render(<RoleBadge role="analista" />);
    expect(screen.getByTestId('role-analista')).toHaveTextContent('Analista');
  });

  it('renderiza etiqueta de supervisor', () => {
    render(<RoleBadge role="supervisor" />);
    expect(screen.getByTestId('role-supervisor')).toHaveTextContent('Supervisor');
  });

  it('renderiza etiqueta de administrador', () => {
    render(<RoleBadge role="admin" />);
    expect(screen.getByTestId('role-admin')).toHaveTextContent('Administrador');
  });
});

describe('StatusToggle', () => {
  it('muestra "Activo" cuando active=true', () => {
    render(<StatusToggle active={true} onChange={() => undefined} />);
    expect(screen.getByTestId('status-toggle-on')).toBeChecked();
    expect(screen.getByText('Activo')).toBeInTheDocument();
  });

  it('muestra "Inactivo" cuando active=false', () => {
    render(<StatusToggle active={false} onChange={() => undefined} />);
    expect(screen.getByTestId('status-toggle-off')).not.toBeChecked();
    expect(screen.getByText('Inactivo')).toBeInTheDocument();
  });

  it('llama onChange al cambiar', async () => {
    let last = true;
    const user = userEvent.setup();
    render(<StatusToggle active={last} onChange={(v) => (last = v)} />);
    await user.click(screen.getByTestId('status-toggle-on'));
    expect(last).toBe(false);
  });

  it('respeta disabled', () => {
    render(<StatusToggle active={true} onChange={() => undefined} disabled />);
    expect(screen.getByTestId('status-toggle-on')).toBeDisabled();
  });
});

describe('EmptyState', () => {
  it('renderiza título y hint', () => {
    render(<EmptyState title="Sin datos" hint="Crea uno nuevo" testId="empty" />);
    expect(screen.getByTestId('empty')).toBeInTheDocument();
    expect(screen.getByText('Sin datos')).toBeInTheDocument();
    expect(screen.getByText('Crea uno nuevo')).toBeInTheDocument();
  });
});