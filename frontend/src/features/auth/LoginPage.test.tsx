import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { LoginPage } from './LoginPage';
import { useAuth } from './useAuth';

vi.mock('./useAuth');

const mockedUseAuth = vi.mocked(useAuth);

function mockAuth(overrides: Partial<ReturnType<typeof useAuth>> = {}) {
  mockedUseAuth.mockReturnValue({
    user: null,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  });
}

describe('LoginPage', () => {
  it('submits the entered credentials', async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    mockAuth({ login });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/password/i), 'hunter22');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(login).toHaveBeenCalledWith('alice@example.com', 'hunter22');
  });

  it('shows an error message when login fails', async () => {
    mockAuth({ login: vi.fn().mockRejectedValue(new Error('bad credentials')) });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText(/incorrect email or password/i)).toBeInTheDocument();
  });
});
