import { describe, expect, it } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SupervisorAuditPanel } from '../../src/clinic/components/SupervisorAuditPanel';
import { setSampleStatus } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

const SAMPLE = '00000000-0000-0000-0000-000000000442';

describe('SupervisorAuditPanel (S1)', () => {
  it('lista la selección del 5% con badges y contador', async () => {
    renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} />, { asSupervisor: true });
    await screen.findByTestId('audit-panel');
    const rows = await screen.findAllByTestId(/^audit-row-/);
    // 43 verdes >0.86 en el mock → ceil(0.05*43) = 3.
    expect(rows).toHaveLength(3);
    expect(screen.getByTestId('audit-progress')).toHaveTextContent('0/3');
    expect(screen.getAllByTestId('audit-badge').length).toBe(3);
  });

  it('confirmar un cromosoma sube el contador y bloquea sus acciones', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED'); // decidir exige caso validado
    const user = userEvent.setup();
    renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} />, { asSupervisor: true });
    await screen.findByTestId('audit-panel');
    await screen.findAllByTestId(/^audit-row-/);

    await user.click(screen.getAllByRole('button', { name: 'Confirmar' })[0]);

    await waitFor(() => expect(screen.getByTestId('audit-progress')).toHaveTextContent('1/3'));
  });

  it('rechazar con comentario refleja la decisión', async () => {
    setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
    const user = userEvent.setup();
    renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} />, { asSupervisor: true });
    await screen.findByTestId('audit-panel');
    const firstRow = (await screen.findAllByTestId(/^audit-row-/))[0];
    within(firstRow).getByRole('textbox');

    await user.type(within(firstRow).getByRole('textbox'), 'banda dudosa');
    await user.click(within(firstRow).getByRole('button', { name: 'Rechazar' }));

    await waitFor(() => expect(within(firstRow).getByText(/Rechazado/)).toBeInTheDocument());
    expect(within(firstRow).getByText(/banda dudosa/)).toBeInTheDocument();
  });

  // --- S2 (firma MFA, DD-SUP-002) ---
  describe('firma MFA', () => {
    async function completeAudit(user: ReturnType<typeof userEvent.setup>) {
      // Confirmar los 3 hasta que el botón de firmar se habilite.
      let btns = screen.queryAllByRole('button', { name: 'Confirmar' });
      while (btns.length) {
        await user.click(btns[0]);
        await waitFor(() => {
          const now = screen.queryAllByRole('button', { name: 'Confirmar' });
          expect(now.length).toBe(btns.length - 1);
        });
        btns = screen.queryAllByRole('button', { name: 'Confirmar' });
      }
    }

    it('el botón Firmar se habilita al completar la auditoría', async () => {
      setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
      const user = userEvent.setup();
      renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} />, { asSupervisor: true });
      await screen.findByTestId('audit-panel');
      await screen.findAllByTestId(/^audit-row-/);
      expect(screen.getByTestId('btn-sign-report')).toBeDisabled();

      await completeAudit(user);
      await waitFor(() => expect(screen.getByTestId('btn-sign-report')).toBeEnabled());
    });

    it('firmar con MFA correcto (123456) marca el caso como firmado', async () => {
      setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
      const user = userEvent.setup();
      renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} signed={false} />, { asSupervisor: true });
      await screen.findByTestId('audit-panel');
      await screen.findAllByTestId(/^audit-row-/);
      await completeAudit(user);
      await waitFor(() => expect(screen.getByTestId('btn-sign-report')).toBeEnabled());

      await user.click(screen.getByTestId('btn-sign-report'));
      await user.type(screen.getByTestId('sign-mfa-input'), '123456');
      await user.click(screen.getByTestId('sign-mfa-submit'));
      // el modal se cierra al firmar OK
      await waitFor(() => expect(screen.queryByTestId('sign-mfa-modal')).not.toBeInTheDocument());
    });

    it('MFA inválido muestra el error en el modal', async () => {
      setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
      const user = userEvent.setup();
      renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} />, { asSupervisor: true });
      await screen.findByTestId('audit-panel');
      await screen.findAllByTestId(/^audit-row-/);
      await completeAudit(user);
      await waitFor(() => expect(screen.getByTestId('btn-sign-report')).toBeEnabled());

      await user.click(screen.getByTestId('btn-sign-report'));
      await user.type(screen.getByTestId('sign-mfa-input'), '000000');
      await user.click(screen.getByTestId('sign-mfa-submit'));
      expect(await screen.findByTestId('sign-mfa-error')).toBeInTheDocument();
    });

    it('con el caso firmado muestra el banner de firmado', async () => {
      setSampleStatus(SAMPLE, 'ANALYST_VALIDATED');
      renderWithProviders(<SupervisorAuditPanel sampleId={SAMPLE} signed />, { asSupervisor: true });
      expect(await screen.findByTestId('report-signed-banner')).toBeInTheDocument();
      expect(screen.queryByTestId('btn-sign-report')).not.toBeInTheDocument();
    });
  });
});
