import axios from 'axios';

// A single configured Axios instance so every feature module shares base URL,
// timeout, and (from Milestone 2 onward) auth-token attachment via
// interceptors, instead of each API file constructing its own client.
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10_000,
});
