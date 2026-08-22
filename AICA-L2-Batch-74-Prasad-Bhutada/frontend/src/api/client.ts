import axios from 'axios';

// The frontend build is served by the SAME Express process/port as the API
// (see backend/src/server.ts) — so a plain relative '/api' always resolves
// correctly with zero configuration, whether you're opening this on the
// server PC itself or from another PC on the office LAN. There is no
// separate frontend server and no URL to configure for the normal setup.
//
// VITE_API_BASE_URL remains available as an escape hatch for advanced setups
// only (e.g. deliberately running the frontend build on a different machine
// or port than the backend) - see frontend/.env.example. Nobody following
// the standard setup.bat flow needs to touch it.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({ baseURL: API_BASE });

/** Attaches the Template Management admin token (if present) to protected requests. */
api.interceptors.request.use((cfg) => {
  const token = sessionStorage.getItem('templateAdminToken');
  if (token && cfg.headers) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (res) => {
    // Defense in depth: fail loudly with a clear message if a response is ever
    // not our expected {success, data} JSON shape, instead of letting
    // `undefined` propagate into a .map() somewhere and blank out the page.
    if (typeof res.data !== 'object' || res.data === null || !('success' in res.data)) {
      return Promise.reject(
        new Error('The server returned an unexpected response. Please confirm CA Docs is running and reload the page.'),
      );
    }
    return res;
  },
  (err) => {
    // Surface the backend's safe, user-friendly message; never raw stack traces (handled server-side).
    const message = err.response?.data?.message || err.message || 'Something went wrong. Please try again.';
    return Promise.reject(new Error(message));
  },
);
