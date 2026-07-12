import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// https://vitejs.dev/config/
//
// Cuando VITE_USE_MSW=true (modo demo), MSW intercepta /api/clinic/* en el
// navegador vía service worker. El proxy de Vite hacia :8002 NO debe estar
// activo en ese modo (mismo patrón que frontend-admin, ver SPEC-007).
// En modo normal el proxy apunta a Django clínico (:8002, ADR-0015 #1).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const useMsw = env.VITE_USE_MSW === 'true';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5174,
      proxy: useMsw
        ? {}
        : {
            '/api/clinic': {
              target: 'http://localhost:8002',
              changeOrigin: true,
            },
          },
    },
  };
});
