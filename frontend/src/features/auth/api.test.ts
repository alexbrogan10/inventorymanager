import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import { getCurrentUser, login, register } from './api';
import type { User } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const USER: User = {
  id: 1,
  email: 'jane@example.com',
  full_name: 'Jane Doe',
  role: 'employee',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
};

describe('auth api', () => {
  it('login posts form-encoded credentials', async () => {
    mockedClient.post.mockResolvedValue({
      data: { access_token: 'tok123', token_type: 'bearer' },
    });

    const result = await login('jane@example.com', 'hunter2');

    expect(mockedClient.post).toHaveBeenCalledWith(
      '/auth/login',
      new URLSearchParams({ username: 'jane@example.com', password: 'hunter2' }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );
    expect(result).toEqual({ access_token: 'tok123', token_type: 'bearer' });
  });

  it('register posts the signup payload', async () => {
    mockedClient.post.mockResolvedValue({ data: USER });

    const result = await register('jane@example.com', 'hunter2', 'Jane Doe');

    expect(mockedClient.post).toHaveBeenCalledWith('/auth/register', {
      email: 'jane@example.com',
      password: 'hunter2',
      full_name: 'Jane Doe',
    });
    expect(result).toEqual(USER);
  });

  it('getCurrentUser fetches the current session user', async () => {
    mockedClient.get.mockResolvedValue({ data: USER });

    const result = await getCurrentUser();

    expect(mockedClient.get).toHaveBeenCalledWith('/auth/me');
    expect(result).toEqual(USER);
  });
});
