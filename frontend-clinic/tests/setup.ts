/**
 * Setup global para Vitest.
 *
 * - Carga @testing-library/jest-dom para matchers como toBeInTheDocument.
 * - Inicia MSW antes de todas las pruebas (handlers + reset entre tests).
 * - Stub de import.meta.env.VITE_CLINIC_API_BASE para que samplesClient caiga en /api/clinic.
 */
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';
import { server } from '../src/clinic/msw/server';
import { resetMockData } from '../src/clinic/msw/handlers';

/**
 * Mock global de react-konva (P3, DD-KARYO-003 §3): Konva usa <canvas>, que
 * jsdom no implementa. Cada primitiva se renderiza como DOM conservando
 * `data-*` y `onClick`; los nodos con `onClick` (los cromosomas) se emiten
 * como <button> para preservar el contrato de los specs de P1/P2
 * (`querySelectorAll('button')`). El drag & drop de reclasificación se dispara
 * en tests con un CustomEvent 'konvadragend' + `globalThis.__konvaDrop`.
 * La geometría real de Konva se valida en E2E (Chromium).
 */
vi.mock('react-konva', async () => {
  const React = await import('react');
  function konvaNode(tag: string) {
    return function KonvaMock(props: Record<string, unknown>) {
      const { children, onClick, onDragEnd } = props as {
        children?: unknown;
        onClick?: (e: unknown) => void;
        onDragEnd?: (e: { target: { x: () => number; y: () => number; position: () => void } }) => void;
      };
      const ref = React.useRef<HTMLElement>(null);
      React.useEffect(() => {
        const el = ref.current;
        if (!el || !onDragEnd) return;
        const handler = () => {
          const drop = (globalThis as unknown as { __konvaDrop?: { x: number; y: number } }).__konvaDrop ?? { x: 0, y: 0 };
          onDragEnd({ target: { x: () => drop.x, y: () => drop.y, position: () => {} } });
        };
        el.addEventListener('konvadragend', handler);
        return () => el.removeEventListener('konvadragend', handler);
      }, [onDragEnd]);
      const domProps: Record<string, unknown> = { ref, 'data-konva': tag };
      for (const [k, v] of Object.entries(props)) {
        if (k.startsWith('data-') || k === 'aria-label') domProps[k] = v;
      }
      if (onClick) domProps.onClick = () => onClick({ cancelBubble: false });
      const element = onClick ? 'button' : 'div';
      if (element === 'button') domProps.type = 'button';
      return React.createElement(element, domProps, children as React.ReactNode);
    };
  }
  return {
    Stage: konvaNode('stage'),
    Layer: konvaNode('layer'),
    Group: konvaNode('group'),
    Rect: konvaNode('rect'),
    Text: konvaNode('text'),
    Line: konvaNode('line'),
    Label: konvaNode('label'),
    Tag: konvaNode('tag'),
  };
});

Object.defineProperty(import.meta, 'env', {
  value: { VITE_CLINIC_API_BASE: '/api/clinic' },
  writable: true,
});

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
beforeEach(() => resetMockData());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
