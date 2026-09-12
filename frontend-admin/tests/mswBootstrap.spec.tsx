/**
 * Tests E2E del bootstrap de MSW en navegador (SPEC-007 §2.4).
 *
 * Estos tests cubren el gap de cobertura conocido: los tests existentes
 * usan `setupServer` (Node, jsdom) y no pueden ejercitar el camino del
 * Service Worker real. Aquí nos enfocamos en tres cosas testeables:
 *
 * 1. El componente `MswBootstrapError` renderiza el banner y permite retry.
 * 2. El archivo `public/mockServiceWorker.js` existe (test de
 *    "infraestructura como código" — si se borra, el test falla con
 *    mensaje claro en vez de un error 404 confuso en runtime).
 * 3. `vite.config.ts` tiene el proxy condicional a `VITE_USE_MSW`.
 *
 * No testeamos el SW real porque jsdom no lo soporta. Ese camino queda
 * cubierto por la verificación manual del CA-3, CA-4 y CA-5 de la spec.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { readFileSync, existsSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { MswBootstrapError } from '../src/admin/components/MswBootstrapError';

describe('SPEC-007 — MSW bootstrap (mock no intercepta)', () => {
  describe('MswBootstrapError component', () => {
    beforeEach(() => {
      // jsdom por defecto no implementa window.location.reload; stub.
      Object.defineProperty(window, 'location', {
        value: { reload: vi.fn() },
        writable: true,
      });
    });

    afterEach(() => {
      cleanup();
    });

    it('renderiza el banner de error con un mensaje claro cuando MSW falla', () => {
      const error = new Error('Service Worker registration failed: 404 Not Found');
      render(<MswBootstrapError error={error} onRetry={vi.fn()} />);

      expect(screen.getByTestId('msw-bootstrap-error')).toBeInTheDocument();
      expect(screen.getByTestId('msw-bootstrap-error-message')).toHaveTextContent(/404 Not Found/);
      // Hint específico para errores 404 (el SW no existe en public/)
      expect(screen.getByTestId('msw-bootstrap-error-message')).toHaveTextContent(
        /mockServiceWorker\.js/,
      );
    });

    it('muestra el hint de regeneración cuando el error contiene palabras clave de "not found"', () => {
      const error = new Error('Failed to fetch mockServiceWorker.js: 404');
      render(<MswBootstrapError error={error} onRetry={vi.fn()} />);

      expect(screen.getByTestId('msw-bootstrap-error-message')).toHaveTextContent(
        /npx msw init public\/ --save/,
      );
    });

    it('serializa errores que no son instancias de Error sin crashear', () => {
      render(<MswBootstrapError error={'string-error-unexpected'} onRetry={vi.fn()} />);

      expect(screen.getByTestId('msw-bootstrap-error-message')).toHaveTextContent(
        /string-error-unexpected/,
      );
    });

    it('invoca onRetry cuando el usuario hace clic en "Reintentar"', () => {
      const onRetry = vi.fn();
      render(<MswBootstrapError error={new Error('boom')} onRetry={onRetry} />);

      fireEvent.click(screen.getByTestId('msw-bootstrap-error-retry'));

      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('expone un link a la doc oficial de MSW', () => {
      render(<MswBootstrapError error={new Error('boom')} onRetry={vi.fn()} />);

      const docsLink = screen.getByTestId('msw-bootstrap-error-docs');
      expect(docsLink).toHaveAttribute('href', expect.stringContaining('mswjs.io'));
      expect(docsLink).toHaveAttribute('target', '_blank');
    });
  });

  describe('Infraestructura — mockServiceWorker.js presente', () => {
    it('public/mockServiceWorker.js existe y no está vacío', () => {
      // Test de "infraestructura como código": si alguien borra el SW en
      // un .git clean o un re-init, este test falla ANTES de que el
      // desarrollador intente levantar la demo.
      const swPath = resolve(__dirname, '..', 'public', 'mockServiceWorker.js');
      expect(existsSync(swPath)).toBe(true);

      const content = readFileSync(swPath, 'utf-8');
      expect(content.length).toBeGreaterThan(1000);
      // El SW canónico de MSW v2 exporta self.addEventListener; si no
      // está, no es un SW válido.
      expect(content).toMatch(/addEventListener|msw/);
    });

    it('package.json declara msw.workerDirectory apuntando a public/', () => {
      const pkgPath = resolve(__dirname, '..', 'package.json');
      const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8')) as {
        msw?: { workerDirectory?: string[] };
      };
      expect(pkg.msw?.workerDirectory).toEqual(
        expect.arrayContaining([expect.stringMatching(/public/)]),
      );
    });
  });

  describe('vite.config.ts — proxy condicional a VITE_USE_MSW', () => {
    it('define el proxy dentro de un ternario que evalúa useMsw', () => {
      // Parseamos vite.config.ts como string y verificamos que el patrón
      // correcto está presente. No usamos un parser AST porque añade
      // dependencia innecesaria para un test de un solo archivo.
      const configPath = resolve(__dirname, '..', 'vite.config.ts');
      const content = readFileSync(configPath, 'utf-8');

      // El fix de SPEC-007 §2.2 introduce `useMsw ? {} : { ... }` o similar.
      // Aceptamos cualquier variante razonable: que exista la lectura de
      // VITE_USE_MSW y que el proxy NO esté hardcoded a :8001 sin condicional.
      expect(content).toMatch(/VITE_USE_MSW/);
      expect(content).toMatch(/useMsw|useMsw\?/);
      // El target :8001 puede seguir existiendo (es la rama else), pero
      // NO debe estar al top-level sin condicional.
      expect(content).not.toMatch(/proxy:\s*\{\s*['"`]\/api['"`]:\s*\{\s*target:/);
    });
  });
});
