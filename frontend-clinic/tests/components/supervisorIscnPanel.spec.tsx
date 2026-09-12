import { describe, expect, it } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SupervisorIscnPanel } from '../../src/clinic/components/SupervisorIscnPanel';
import { setSampleStatus } from '../../src/clinic/msw/handlers';
import { renderWithProviders } from '../testUtils';

const SAMPLE = '00000000-0000-0000-0000-000000000442';

/** El ISCN se reporta DESPUÉS de la firma (ADR-0025 D5). */
function conCasoFirmado() {
  setSampleStatus(SAMPLE, 'SIGNED');
}

describe('SupervisorIscnPanel (S3)', () => {
  describe('generación del ISCN', () => {
    it('ofrece generar cuando el caso está firmado y aún no tiene nomenclatura', async () => {
      conCasoFirmado();
      renderWithProviders(<SupervisorIscnPanel sampleId={SAMPLE} status="SIGNED" />, { asSupervisor: true });

      expect(screen.getByTestId('iscn-pending-hint')).toBeInTheDocument();
      expect(screen.getByTestId('btn-generate-iscn')).toBeEnabled();
    });

    it('genera la nomenclatura y la muestra como read-only', async () => {
      conCasoFirmado();
      const user = userEvent.setup();
      renderWithProviders(<SupervisorIscnPanel sampleId={SAMPLE} status="SIGNED" />, { asSupervisor: true });

      await user.click(screen.getByTestId('btn-generate-iscn'));

      await waitFor(() => expect(screen.getByTestId('iscn-value')).toBeInTheDocument());
      // RN-04: el aviso de inmutabilidad tiene que estar visible.
      expect(screen.getByTestId('iscn-readonly-hint')).toBeInTheDocument();
      // Y el botón de generar desaparece: no se regenera sin override.
      expect(screen.queryByTestId('btn-generate-iscn')).not.toBeInTheDocument();
    });

    it('muestra el ISCN ya persistido sin volver a generarlo', () => {
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="47,XY,+21" status="REPORTED" />,
        { asSupervisor: true },
      );

      expect(screen.getByTestId('iscn-value')).toHaveTextContent('47,XY,+21');
      expect(screen.getByTestId('iscn-reported')).toBeInTheDocument();
      expect(screen.queryByTestId('btn-generate-iscn')).not.toBeInTheDocument();
    });
  });

  describe('override justificado (RN-04)', () => {
    it('exige nomenclatura Y justificación antes de habilitar el envío', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XY" status="REPORTED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-show-iscn-override'));
      const enviar = screen.getByTestId('btn-iscn-override-submit');
      expect(enviar).toBeDisabled();

      await user.type(screen.getByTestId('iscn-override-input'), '47,XY,+21');
      // Sobrescribir un diagnóstico sin explicar por qué no es auditable.
      expect(enviar).toBeDisabled();

      await user.type(screen.getByTestId('iscn-override-motivo'), 'Recuento revisado');
      expect(enviar).toBeEnabled();
    });

    it('aplica el override y lo marca como tal', async () => {
      conCasoFirmado();
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XY" status="SIGNED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-show-iscn-override'));
      await user.type(screen.getByTestId('iscn-override-input'), '47,XY,+21');
      await user.type(screen.getByTestId('iscn-override-motivo'), 'Recuento revisado');
      await user.click(screen.getByTestId('btn-iscn-override-submit'));

      await waitFor(() => expect(screen.getByTestId('iscn-override-tag')).toBeInTheDocument());
      expect(screen.getByTestId('iscn-value')).toHaveTextContent('47,XY,+21');
    });

    it('muestra el error del backend si la gramática es inválida', async () => {
      conCasoFirmado();
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XY" status="SIGNED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-show-iscn-override'));
      await user.type(screen.getByTestId('iscn-override-input'), 'no es un iscn');
      await user.type(screen.getByTestId('iscn-override-motivo'), 'x');
      await user.click(screen.getByTestId('btn-iscn-override-submit'));

      await waitFor(() => expect(screen.getByTestId('iscn-error')).toBeInTheDocument());
    });

    it('cancelar cierra el formulario sin cambiar nada', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XY" status="REPORTED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-show-iscn-override'));
      await user.click(screen.getByTestId('btn-iscn-override-cancel'));

      expect(screen.queryByTestId('iscn-override-form')).not.toBeInTheDocument();
      expect(screen.getByTestId('iscn-value')).toHaveTextContent('46,XY');
    });
  });

  describe('narrativa asistida (ADR-0024)', () => {
    it('el borrador se marca como tal y exige revisión', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XY" status="REPORTED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-generate-narrative'));

      await waitFor(() => expect(screen.getByTestId('narrative-block')).toBeInTheDocument());
      // ADR-0024 D3: el usuario tiene que saber que NO es texto final.
      expect(screen.getByTestId('narrative-draft-warning')).toBeInTheDocument();
    });

    it('muestra los campos tipados, no solo la prosa', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="47,XY,+21" status="REPORTED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-generate-narrative'));

      await waitFor(() => expect(screen.getByTestId('narrative-meta')).toBeInTheDocument());
      expect(screen.getByTestId('narrative-normal')).toHaveTextContent('alteraciones');
      expect(screen.getByTestId('narrative-anomalias')).toHaveTextContent('+21');
      expect(screen.getByTestId('narrative-confianza')).toBeInTheDocument();
    });

    it('un cariotipo normal se distingue de uno con alteraciones', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XX" status="REPORTED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-generate-narrative'));

      await waitFor(() => expect(screen.getByTestId('narrative-normal')).toBeInTheDocument());
      expect(screen.getByTestId('narrative-normal')).toHaveTextContent('normal');
      expect(screen.queryByTestId('narrative-anomalias')).not.toBeInTheDocument();
    });

    it('deja ver qué modelo la redactó y sobre qué ISCN', async () => {
      const user = userEvent.setup();
      renderWithProviders(
        <SupervisorIscnPanel sampleId={SAMPLE} iscn="46,XY" status="REPORTED" />,
        { asSupervisor: true },
      );

      await user.click(screen.getByTestId('btn-generate-narrative'));

      await waitFor(() => expect(screen.getByTestId('narrative-model')).toBeInTheDocument());
      expect(screen.getByTestId('narrative-model')).toHaveTextContent('llama3.2:3b');
    });

    it('sin ISCN no ofrece redactar: no hay dato clínico que narrar', () => {
      conCasoFirmado();
      renderWithProviders(<SupervisorIscnPanel sampleId={SAMPLE} status="SIGNED" />, { asSupervisor: true });

      expect(screen.queryByTestId('btn-generate-narrative')).not.toBeInTheDocument();
    });
  });
});
