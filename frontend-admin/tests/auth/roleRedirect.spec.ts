import { describe, expect, it } from 'vitest';
import { getRedirectForRole } from '../../src/admin/auth/roleRedirect';

describe('getRedirectForRole (ADR-0017 D7)', () => {
  it('admin devuelve null (se queda en la SPA)', () => {
    expect(getRedirectForRole('admin')).toBeNull();
  });

  it('analista devuelve la URL de frontend-clinic /clinic/samples', () => {
    const target = getRedirectForRole('analista');
    expect(target).toContain('/clinic/samples');
  });

  it('supervisor devuelve la URL del legacy supervisor.html', () => {
    const target = getRedirectForRole('supervisor');
    expect(target).toContain('supervisor.html');
  });
});
