import { describe, expect, it, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Routes, Route } from 'react-router-dom';
import { SampleRegisterPage } from '../../src/clinic/pages/SampleRegisterPage';
import { SampleListPage } from '../../src/clinic/pages/SampleListPage';
import { KaryotypePage } from '../../src/clinic/pages/KaryotypePage';
import { renderWithProviders } from '../testUtils';

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/clinic/samples" element={<SampleListPage />} />
      <Route path="/clinic/samples/register" element={<SampleRegisterPage />} />
      <Route path="/clinic/samples/:id/karyotype" element={<KaryotypePage />} />
    </Routes>,
    { route: '/clinic/samples/register' },
  );
}

async function uploadImages(count: number) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  const files = Array.from({ length: count }, (_, i) => new File(['x'], `img${i}.jpg`, { type: 'image/jpeg' }));
  await userEvent.upload(input, files);
}

describe('SampleRegisterPage', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn(() => Promise.reject(new Error('no camera in jsdom'))) },
      configurable: true,
    });
  });

  it('renderiza las 5 secciones del formulario', () => {
    renderPage();
    expect(screen.getByText('Información del Paciente')).toBeInTheDocument();
    expect(screen.getByText('Información de la Muestra')).toBeInTheDocument();
    expect(screen.getByText('Historial Clínico')).toBeInTheDocument();
    expect(screen.getByText('Solicitud de Análisis')).toBeInTheDocument();
    expect(screen.getByText('Captura de Metafases')).toBeInTheDocument();
  });

  it('el código de muestra se autogenera con formato BM-', () => {
    renderPage();
    const input = screen.getByDisplayValue(/^BM-\d{8}-\d+$/);
    expect(input).toBeInTheDocument();
  });

  it('guardar borrador sin CHN muestra error', async () => {
    renderPage();
    await userEvent.click(screen.getByText(/Guardar borrador/));
    expect(screen.getByText(/Complete el CHN/)).toBeInTheDocument();
  });

  it('guardar borrador con solo CHN funciona', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText('Ej: CHN-12345'), 'CHN-2026-07-12-0111');
    await userEvent.click(screen.getByText(/Guardar borrador/));
    await waitFor(() => expect(screen.getByText('Borrador guardado correctamente')).toBeInTheDocument());
  });

  it('registrar sin CHN ni nombre muestra error', async () => {
    renderPage();
    await userEvent.click(screen.getByText(/Registrar y analizar con IA/));
    expect(screen.getByText(/Complete los campos obligatorios/)).toBeInTheDocument();
  });

  it('registrar con menos de 3 imágenes muestra error', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText('Ej: CHN-12345'), 'CHN-2026-07-12-0112');
    await userEvent.type(screen.getByPlaceholderText('Nombre del paciente'), 'ANON-TEST');
    await uploadImages(1);
    await waitFor(() => expect(screen.getAllByAltText(/Metafase/)).toHaveLength(1));
    await userEvent.click(screen.getByText(/Registrar y analizar con IA/));
    expect(screen.getByText(/Se requieren al menos 3 metafases/)).toBeInTheDocument();
  });

  it('registro completo exitoso abre el modal de procesamiento', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText('Ej: CHN-12345'), 'CHN-2026-07-12-0113');
    await userEvent.type(screen.getByPlaceholderText('Nombre del paciente'), 'ANON-TEST');
    await uploadImages(3);
    await waitFor(() => expect(screen.getAllByAltText(/Metafase/)).toHaveLength(3));
    await userEvent.click(screen.getByText(/Registrar y analizar con IA/));
    await waitFor(() => expect(screen.getByText('Procesando con Biomed IA')).toBeInTheDocument());
  });

  it('registro completo: al terminar el polling navega al visor de cariotipo (P1-P4)', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText('Ej: CHN-12345'), 'CHN-2026-07-12-0199');
    await userEvent.type(screen.getByPlaceholderText('Nombre del paciente'), 'ANON-TEST');
    await uploadImages(3);
    await waitFor(() => expect(screen.getAllByAltText(/Metafase/)).toHaveLength(3));
    await userEvent.click(screen.getByText(/Registrar y analizar con IA/));
    await waitFor(() => expect(screen.getByText('Procesando con Biomed IA')).toBeInTheDocument());
    await waitFor(() => expect(screen.queryByText('Procesando con Biomed IA')).not.toBeInTheDocument(), { timeout: 5000 });
    // Ahora aterriza en el visor React (no en el prototipo vanilla legado).
    expect(await screen.findByTestId('karyotype-viewer', undefined, { timeout: 5000 })).toBeInTheDocument();
  });

  it('registro con CHN duplicado muestra error del backend', async () => {
    renderPage();
    // CHN-2026-04-10-0442 ya existe en el seed
    await userEvent.type(screen.getByPlaceholderText('Ej: CHN-12345'), 'CHN-2026-04-10-0442');
    await userEvent.type(screen.getByPlaceholderText('Nombre del paciente'), 'ANON-TEST');
    await uploadImages(3);
    await waitFor(() => expect(screen.getAllByAltText(/Metafase/)).toHaveLength(3));
    await userEvent.click(screen.getByText(/Registrar y analizar con IA/));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('CHN ya existe'));
  });

  it('cancelar con confirmación navega a la lista', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderPage();
    await userEvent.click(screen.getByText(/Cancelar/));
    await waitFor(() => expect(screen.getByText('Gestión de Muestras')).toBeInTheDocument());
  });

  it('cancelar sin confirmar no navega', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    renderPage();
    await userEvent.click(screen.getByText(/Cancelar/));
    expect(screen.getByText('Información del Paciente')).toBeInTheDocument();
  });

  it('marcar un análisis adicional actualiza el estado', async () => {
    renderPage();
    await userEvent.click(screen.getByLabelText(/FISH/));
    expect(screen.getByLabelText(/FISH/)).toBeChecked();
  });
});
