// Single source of truth for the backend URL. Normal local dev needs no
// changes — it falls back to localhost. For the same-origin deployed build
// (backend serving the built frontend), set VITE_API_BASE="" in
// frontend/.env.production so requests use relative paths instead.
export const API_BASE =
  import.meta.env.VITE_API_BASE !== undefined
    ? import.meta.env.VITE_API_BASE
    : "http://localhost:8000";
