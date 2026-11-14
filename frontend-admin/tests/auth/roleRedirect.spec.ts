import { describe, expect, it } from 'vitest';
import { getRedirectForRole, urlMuestrasClinica } from '../../src/admin/auth/roleRedirect';

/** El destino del supervisor es CONFIGURACION, no comportamiento: lo fija
 * `VITE_SUPERVISOR_LEGACY_URL`, y en el despliegue detras de Caddy apunta a la
 * app clinica y no al `/supervisor.html` legado. Afirmar el valor por defecto
 * hacia que estas pruebas dependieran de un `.env` LOCAL Y GITIGNORED: fallaban
 * en la maquina del desarrollador y pasaban en cualquier otra. Se comprueba el
 * mapeo, que es el contrato de ADR-0017 D7. */
const DESTINO_SUPERVISOR =
  (import.meta.env.VITE_SUPERVISOR_LEGACY_URL as string | undefined) ?? '/supervisor.html';

describe('getRedirectForRole (ADR-0017 D7)', () => {
  it('admin devuelve null (se queda en la SPA)', () => {
    expect(getRedirectForRole('admin')).toBeNull();
  });

  it('analista devuelve la URL de frontend-clinic /clinic/samples', () => {
    const target = getRedirectForRole('analista');
    // `toContain('/clinic/samples')` pasaba tambien con `/clinic//clinic/samples`,
    // que es el fallo que se vio en la Demo 3: se exige el final exacto.
    expect(target).toMatch(/(^|[^/])\/clinic\/samples$/);
    expect(target).not.toContain('//clinic');
  });

  it('supervisor devuelve el destino externo configurado', () => {
    expect(getRedirectForRole('supervisor')).toBe(DESTINO_SUPERVISOR);
  });

  it('solo admin se queda en esta SPA; los otros dos navegan fuera', () => {
    expect(getRedirectForRole('admin')).toBeNull();
    expect(getRedirectForRole('analista')).not.toBeNull();
    expect(getRedirectForRole('supervisor')).not.toBeNull();
    // NO se exige que analista y supervisor difieran: tras ADR-0020 ambos
    // trabajan en la app clinica, y el visor decide que panel ve cada uno.
    // Una primera version de esta prueba lo afirmaba y fallo -- afirmaba una
    // suposicion, no el contrato.
  });
});

describe('urlMuestrasClinica', () => {
  it.each([
    ['http://localhost:5174', 'http://localhost:5174/clinic/samples'], // desarrollo: el origen
    ['http://localhost:5174/', 'http://localhost:5174/clinic/samples'],
    ['/clinic/', '/clinic/samples'], // el stack: la ruta detras del proxy
    ['/clinic', '/clinic/samples'],
    ['', '/clinic/samples'], // mismo origen, sin base
    ['/', '/clinic/samples'],
    ['https://biomed.example/clinic//', 'https://biomed.example/clinic/samples'],
  ])('con la base %j da %j', (base, esperado) => {
    expect(urlMuestrasClinica(base)).toBe(esperado);
  });

  it('nunca repite /clinic ni deja una barra doble en la ruta', () => {
    for (const base of ['/clinic/', '/clinic', '', 'http://h:1', 'http://h:1/clinic/']) {
      const ruta = urlMuestrasClinica(base).replace(/^https?:\/\//, '');
      expect(ruta).not.toContain('//');
      expect(ruta.match(/\/clinic/g)).toHaveLength(1);
    }
  });
});
