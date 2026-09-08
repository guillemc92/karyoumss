import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SampleInfoSection } from '../../src/clinic/components/SampleInfoSection';
import type { SampleData } from '../../src/clinic/types/registration';

const EMPTY: SampleData = {
  chn_code: '', sample_type: '', culture_method: '', collection_date: '',
  reception_date: '', requesting_doctor: '', department: '', gender: '',
};

describe('SampleInfoSection', () => {
  it('muestra el código autogenerado como readonly', () => {
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-20260712-042" onChange={vi.fn()} />);
    const input = screen.getByDisplayValue('BM-20260712-042');
    expect(input).toHaveAttribute('readonly');
  });

  it('cambiar tipo de muestra llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-X" onChange={onChange} />);
    await userEvent.selectOptions(screen.getByText('Sangre periférica').closest('select')!, 'sangre');
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY, sample_type: 'sangre' });
  });

  it('escribir médico solicitante llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-X" onChange={onChange} />);
    await userEvent.type(screen.getByPlaceholderText('Nombre del médico'), 'D');
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY, requesting_doctor: 'D' });
  });

  it('cambiar fecha de recolección llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-X" onChange={onChange} />);
    const dateInputs = document.querySelectorAll('input[type="date"]');
    await userEvent.type(dateInputs[0], '2026-07-12');
    expect(onChange).toHaveBeenCalled();
  });

  it('cambiar fecha de recepción llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-X" onChange={onChange} />);
    const dateInputs = document.querySelectorAll('input[type="date"]');
    await userEvent.type(dateInputs[1], '2026-07-12');
    expect(onChange).toHaveBeenCalled();
  });

  it('cambiar método de cultivo llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-X" onChange={onChange} />);
    await userEvent.selectOptions(screen.getByText('Sangre periférica — Cultura 72h').closest('select')!, '72h');
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY, culture_method: '72h' });
  });

  it('escribir departamento llama onChange', async () => {
    const onChange = vi.fn();
    render(<SampleInfoSection sample={EMPTY} sampleCode="BM-X" onChange={onChange} />);
    await userEvent.type(screen.getByPlaceholderText('Ej: Genética Clínica'), 'G');
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY, department: 'G' });
  });
});
