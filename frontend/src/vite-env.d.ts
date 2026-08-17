/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute backend URL for the native (Capacitor) build -- see frontend/MOBILE.md. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
