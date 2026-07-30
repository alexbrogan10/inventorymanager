// Lives in api/ (not features/auth/) so the Axios client below can attach the
// token to outgoing requests without api/ depending on a feature module -
// features depend on api/, never the reverse (see docs/ARCHITECTURE.md).
const TOKEN_STORAGE_KEY = 'inventory_manager_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}
