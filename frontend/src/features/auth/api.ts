import { apiClient } from '../../api/client';
import type { TokenResponse, User } from './types';

export async function login(email: string, password: string): Promise<TokenResponse> {
  // The backend's /auth/login is an OAuth2PasswordRequestForm endpoint (so
  // Swagger UI's "Authorize" button works against it), which requires
  // form-encoded data with a "username" field rather than JSON.
  const body = new URLSearchParams({ username: email, password });
  const { data } = await apiClient.post<TokenResponse>('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

export async function register(email: string, password: string, fullName: string): Promise<User> {
  const { data } = await apiClient.post<User>('/auth/register', {
    email,
    password,
    full_name: fullName,
  });
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
}
