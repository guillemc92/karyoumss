import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PatientInfoSection } from '../../src/clinic/components/PatientInfoSection';
import type { PatientData } from '../../src/clinic/types/registration';

const EMPTY: PatientData = { full_name: '', birth_date: '', document_id: '', phone: '' };

describe('PatientInfoSection', () => {
  it('renderiza los 6 campos', () => {
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={vi.fn()} onGenderChange={vi.fn()} onChnChange={vi.fn()} />,
    );
    expect(screen.getByPlaceholderText('Ej: CHN-12345')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Nombre del paciente')).toBeInTheDocument();
  });

  it('escribir en CHN llama onChnChange', async () => {
    const onChnChange = vi.fn();
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={vi.fn()} onGenderChange={vi.fn()} onChnChange={onChnChange} />,
    );
    await userEvent.type(screen.getByPlaceholderText('Ej: CHN-12345'), 'C');
    expect(onChnChange).toHaveBeenCalledWith('C');
  });

  it('escribir en nombre llama onPatientChange con el patch correcto', async () => {
    const onPatientChange = vi.fn();
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={onPatientChange} onGenderChange={vi.fn()} onChnChange={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText('Nombre del paciente'), 'A');
    expect(onPatientChange).toHaveBeenCalledWith({ ...EMPTY, full_name: 'A' });
  });

  it('cambiar género llama onGenderChange', async () => {
    const onGenderChange = vi.fn();
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={vi.fn()} onGenderChange={onGenderChange} onChnChange={vi.fn()} />,
    );
    await userEvent.selectOptions(screen.getByDisplayValue('Seleccionar...'), 'M');
    expect(onGenderChange).toHaveBeenCalledWith('M');
  });

  it('escribir en fecha de nacimiento llama onPatientChange', async () => {
    const onPatientChange = vi.fn();
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={onPatientChange} onGenderChange={vi.fn()} onChnChange={vi.fn()} />,
    );
    const dateInput = document.querySelector('input[type="date"]') as HTMLInputElement;
    await userEvent.type(dateInput, '1998-03-15');
    expect(onPatientChange).toHaveBeenCalled();
  });

  it('escribir en documento llama onPatientChange', async () => {
    const onPatientChange = vi.fn();
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={onPatientChange} onGenderChange={vi.fn()} onChnChange={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText('CI / Pasaporte'), '1');
    expect(onPatientChange).toHaveBeenCalledWith({ ...EMPTY, document_id: '1' });
  });

  it('escribir en teléfono llama onPatientChange', async () => {
    const onPatientChange = vi.fn();
    render(
      <PatientInfoSection patient={EMPTY} gender="" chnCode="" onPatientChange={onPatientChange} onGenderChange={vi.fn()} onChnChange={vi.fn()} />,
    );
    await userEvent.type(screen.getByPlaceholderText('+591 XXXXXXXX'), '7');
    expect(onPatientChange).toHaveBeenCalledWith({ ...EMPTY, phone: '7' });
  });
});
