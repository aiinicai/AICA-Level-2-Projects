/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PDF_SERVICE_URL?: string;
  readonly [key: string]: any;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
