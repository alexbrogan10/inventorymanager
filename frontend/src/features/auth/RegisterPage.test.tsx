import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { RegisterPage } from './RegisterPage';
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

async function fillForm(
  user: ReturnType<typeof userEvent.setup>,
  {
    password = 'hunter22',
    confirmPassword = password,
  }: { password?: string; confirmPassword?: string } = {},
) {
  await user.type(screen.getByLabelText(/full name/i), 'Alice Example');
  await user.type(screen.getByLabelText(/^email/i), 'alice@example.com');
  await user.type(screen.getByLabelText(/^password/i), password);
  await user.type(screen.getByLabelText(/confirm password/i), confirmPassword);
  await user.click(screen.getByRole('button', { name: /register/i }));
}

describe('RegisterPage', () => {
  it('registers with the entered details when the passwords match', async () => {
    const register = vi.fn().mockResolvedValue(undefined);
    mockAuth({ register });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );
    await fillForm(user);

    expect(register).toHaveBeenCalledWith('alice@example.com', 'hunter22', 'Alice Example');
  });

  it('rejects mismatched passwords without calling the API', async () => {
    const register = vi.fn();
    mockAuth({ register });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );
    await fillForm(user, { password: 'hunter22', confirmPassword: 'something-else' });

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it('shows a specific message when the email is already registered', async () => {
    mockAuth({
      register: vi.fn().mockRejectedValue({ response: { status: 409 } }),
    });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );
    await fillForm(user);

    expect(await screen.findByText(/already exists/i)).toBeInTheDocument();
  });
});
