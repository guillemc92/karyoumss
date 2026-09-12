/**
 * Tests de infraestructura MSW (patrón SPEC-007, adaptado a frontend-clinic).
 *
 * Cubre el gap de cobertura conocido: los tests con setupServer (Node) no
 * ejercitan el Service Worker real del navegador. Verificamos que la
 * infraestructura como código esté presente para que el bootstrap real
 * (T66 verificación E2E manual) no falle silenciosamente.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

describe('Infraestructura MSW — frontend-clinic', () => {
  it('public/mockServiceWorker.js existe y no está vacío', () => {
    const swPath = resolve(__dirname, '..', 'public', 'mockServiceWorker.js');
    expect(existsSync(swPath)).toBe(true);

    const content = readFileSync(swPath, 'utf-8');
    expect(content.length).toBeGreaterThan(1000);
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

  it('vite.config.ts define el proxy condicional a VITE_USE_MSW', () => {
    const configPath = resolve(__dirname, '..', 'vite.config.ts');
    const content = readFileSync(configPath, 'utf-8');

    expect(content).toMatch(/VITE_USE_MSW/);
    expect(content).toMatch(/useMsw/);
    expect(content).not.toMatch(/proxy:\s*\{\s*['"`]\/api['"`]:\s*\{\s*target:/);
  });

  it('main.tsx invoca worker.start() condicionado a USE_MSW antes de montar React', () => {
    const mainPath = resolve(__dirname, '..', 'src', 'main.tsx');
    const content = readFileSync(mainPath, 'utf-8');

    expect(content).toMatch(/VITE_USE_MSW/);
    expect(content).toMatch(/worker\.start/);
  });
});
