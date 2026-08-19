/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origin of the DealDog backend, without a trailing /api. Empty locally. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
