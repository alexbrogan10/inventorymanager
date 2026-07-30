import axios from 'axios';

import { clearStoredToken, getStoredToken } from './tokenStorage';

// A single configured Axios instance so every feature module shares base URL,
// timeout, and auth-token attachment via interceptors, instead of each API
// file constructing its own client.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
});

// Uploaded files (product images) are served from the API's origin at
// /static/..., not under the /api/v1 prefix - derive the origin from the
// same configured base URL rather than hardcoding it a second time.
export const apiOrigin = new URL(API_BASE_URL).origin;

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
