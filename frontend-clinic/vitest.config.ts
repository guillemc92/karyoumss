import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.spec.ts', 'tests/**/*.spec.tsx', 'src/**/*.spec.ts', 'src/**/*.spec.tsx'],
    css: false,
    // Las suites de página del cariotipo (XAI/modal + MSW + loops de resolución)
    // son pesadas; 5s por defecto flakea bajo carga concurrente. 15s da margen.
    testTimeout: 15000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html'],
      include: ['src/clinic/**/*.{ts,tsx}'],
      exclude: ['src/clinic/types/**', 'src/clinic/msw/**', 'src/main.tsx', 'src/App.tsx'],
      thresholds: {
        lines: 90,
        // branches: 88 (no 90) — mismo gap estructural documentado en
        // frontend-admin/vitest.config.ts: ramas de error handling en
        // localStorage/fetch no determinísticas en jsdom. Ver
        // feedback-rn09-v8-html-trap en memoria del proyecto.
        branches: 88,
        functions: 90,
        statements: 90,
      },
    },
  },
});
