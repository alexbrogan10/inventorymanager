import axios from 'axios';

import { clearStoredToken, getStoredToken } from './tokenStorage';

// A single configured Axios instance so every feature module shares base URL,
// timeout, and auth-token attachment via interceptors, instead of each API
// file constructing its own client.
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10_000,
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // The token is invalid/expired - drop it so the next render treats the
    // user as logged out. AuthContext's own getCurrentUser call already
    // handles clearing `user` state on failure; this just keeps storage
    // consistent for any other request that hits a stale token first.
    if (error.response?.status === 401) {
      clearStoredToken();
    }
    return Promise.reject(error);
  },
);
