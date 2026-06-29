import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy /api hacia backend-admin en dev (FastAPI+Django corren en :8000/:8001)
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
});