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
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html'],
      include: ['src/admin/**/*.{ts,tsx}'],
      exclude: ['src/admin/types/**', 'src/admin/msw/**', 'src/main.tsx', 'src/App.tsx'],
      thresholds: {
        lines: 90,
        branches: 90,
        functions: 90,
        statements: 90,
      },
    },
  },
});