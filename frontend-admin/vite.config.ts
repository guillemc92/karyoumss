import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// https://vitejs.dev/config/
//
// Cuando VITE_USE_MSW=true (modo demo), MSW intercepta /api/admin/* en el
// navegador vía service worker. El proxy de Vite hacia :8001 NO debe estar
// activo en ese modo porque (a) no hay backend y (b) un ECONNREFUSED del
// proxy enmascara el verdadero problema "MSW no se cargó" (ver SPEC-007).
// En modo normal (VITE_USE_MSW no definido o =false) el proxy sigue activo.
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
      port: 5173,
      proxy: useMsw
        ? {}
        : {
            // Proxy /api hacia backend-admin en dev (FastAPI+Django corren en :8000/:8001)
            '/api': {
              target: 'http://localhost:8001',
              changeOrigin: true,
            },
          },
    },
  };
});