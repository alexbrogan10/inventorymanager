import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { User } from '../features/auth/types';
import { useAuth } from '../features/auth/useAuth';
import { ProtectedRoute } from './ProtectedRoute';

vi.mock('../features/auth/useAuth');

const mockedUseAuth = vi.mocked(useAuth);

const FAKE_USER: User = {
  id: 1,
  email: 'alice@example.com',
  full_name: 'Alice Example',
  role: 'employee',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
};

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <div>Protected Content</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

function mockAuth(overrides: Partial<ReturnType<typeof useAuth>>) {
  mockedUseAuth.mockReturnValue({
    user: null,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  });
}

describe('ProtectedRoute', () => {
  it('redirects to /login when there is no authenticated user', () => {
    mockAuth({ user: null, isLoading: false });

    renderProtected();

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('renders the protected content once authenticated', () => {
    mockAuth({ user: FAKE_USER, isLoading: false });

    renderProtected();

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('renders nothing while the auth check is still in flight', () => {
    mockAuth({ user: null, isLoading: true });

    renderProtected();

    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });
});
