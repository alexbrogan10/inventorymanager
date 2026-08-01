import type { InternalAxiosRequestConfig } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from './client';
import * as tokenStorage from './tokenStorage';

vi.mock('./tokenStorage');

const mockedTokenStorage = vi.mocked(tokenStorage);

// Axios doesn't expose a public way to invoke a registered interceptor in
// isolation - `handlers` is the same internal array axios itself walks when
// a real request goes out, so reaching into it here is the standard way to
// unit-test interceptor logic without a live HTTP call.
interface InterceptorHandlers<T> {
  handlers: Array<{
    fulfilled: (value: T) => T;
    rejected?: (error: unknown) => unknown;
  }>;
}

const requestHandlers = (
  apiClient.interceptors.request as unknown as InterceptorHandlers<InternalAxiosRequestConfig>
).handlers;
const responseHandlers = (
  apiClient.interceptors.response as unknown as InterceptorHandlers<unknown>
).handlers;

afterEach(() => {
  vi.clearAllMocks();
});

describe('apiClient request interceptor', () => {
  it('attaches the Authorization header when a token is stored', () => {
    mockedTokenStorage.getStoredToken.mockReturnValue('abc123');

    const config = requestHandlers[0].fulfilled({ headers: {} } as InternalAxiosRequestConfig);

    expect(config.headers.Authorization).toBe('Bearer abc123');
  });

  it('leaves the Authorization header unset when there is no stored token', () => {
    mockedTokenStorage.getStoredToken.mockReturnValue(null);

    const config = requestHandlers[0].fulfilled({ headers: {} } as InternalAxiosRequestConfig);

    expect(config.headers.Authorization).toBeUndefined();
  });
});

describe('apiClient response interceptor', () => {
  it('passes a successful response through unchanged', () => {
    const response = { data: 'ok' };

    expect(responseHandlers[0].fulfilled(response)).toBe(response);
  });

  it('clears the stored token on a 401 error', async () => {
    const error = { response: { status: 401 } };

    await expect(responseHandlers[0].rejected?.(error)).rejects.toBe(error);
    expect(mockedTokenStorage.clearStoredToken).toHaveBeenCalled();
  });

  it('does not clear the stored token on a non-401 error', async () => {
    const error = { response: { status: 500 } };

    await expect(responseHandlers[0].rejected?.(error)).rejects.toBe(error);
    expect(mockedTokenStorage.clearStoredToken).not.toHaveBeenCalled();
  });
});
