/**
 * Tests de ConfigSection — esqueleto loading/error/data.
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfigSection } from '../../src/admin/components/ConfigSection';

describe('ConfigSection — esqueleto loading/error/data', () => {
  it('muestra loading y luego el children con los datos', async () => {
    render(
      <ConfigSection load={async () => 'ok' as const}>
        {(data) => <div data-testid="data">data={data}</div>}
      </ConfigSection>,
    );
    expect(screen.getByTestId('config-section-loading')).toBeInTheDocument();
    expect(await screen.findByTestId('data')).toHaveTextContent('data=ok');
  });

  it('muestra banner de error + botón Reintentar si load() lanza', async () => {
    const load = vi.fn().mockRejectedValue(new Error('boom'));
    render(
      <ConfigSection load={load} testId="cs">
        {(data) => <div>{String(data)}</div>}
      </ConfigSection>,
    );
    const banner = await screen.findByTestId('cs-error-message');
    expect(banner).toHaveTextContent(/boom/);
    expect(screen.getByTestId('cs-retry')).toBeInTheDocument();
  });

  it('Reintentar vuelve a llamar load()', async () => {
    const load = vi
      .fn()
      .mockRejectedValueOnce(new Error('primera falla'))
      .mockResolvedValueOnce('segunda ok' as const);
    const user = userEvent.setup();
    render(
      <ConfigSection load={load} testId="cs">
        {(data) => <div data-testid="data">{String(data)}</div>}
      </ConfigSection>,
    );
    await screen.findByTestId('cs-error-message');
    await user.click(screen.getByTestId('cs-retry'));
    expect(await screen.findByTestId('data')).toHaveTextContent('segunda ok');
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('refresh() expuesto al children re-dispara load()', async () => {
    const load = vi.fn().mockResolvedValue('value' as const);
    render(
      <ConfigSection load={load} testId="cs">
        {(_data, refresh) => (
          <button type="button" onClick={refresh} data-testid="refresh-btn">
            refresh
          </button>
        )}
      </ConfigSection>,
    );
    await screen.findByTestId('refresh-btn');
    await userEvent.click(screen.getByTestId('refresh-btn'));
    await waitFor(() => expect(load).toHaveBeenCalledTimes(2));
  });
});
