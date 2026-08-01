import { afterEach, describe, expect, it } from 'vitest';

import { clearStoredToken, getStoredToken, setStoredToken } from './tokenStorage';

afterEach(() => {
  localStorage.clear();
});

describe('tokenStorage', () => {
  it('returns null when no token has been stored', () => {
    expect(getStoredToken()).toBeNull();
  });

  it('round-trips a stored token', () => {
    setStoredToken('abc123');

    expect(getStoredToken()).toBe('abc123');
  });

  it('clears the stored token', () => {
    setStoredToken('abc123');

    clearStoredToken();

    expect(getStoredToken()).toBeNull();
  });
});
