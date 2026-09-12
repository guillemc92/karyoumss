/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ADMIN_API_BASE: string;
  readonly VITE_FASTAPI_LOGIN_URL: string;
  readonly VITE_LOG_LEVEL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}