import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as categoriesApi from './api';
import { CategoriesPage } from './CategoriesPage';
import type { Category } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(categoriesApi);

beforeEach(() => {
  vi.clearAllMocks();
});

const MANAGER: User = {
  id: 1,
  email: 'manager@example.com',
  full_name: 'Manager User',
  role: 'manager',
  is_active: true,
  created_at: '',
};

const EMPLOYEE: User = { ...MANAGER, id: 2, email: 'employee@example.com', role: 'employee' };

const SAMPLE_CATEGORY: Category = {
  id: 1,
  name: 'Electronics',
  description: 'Gadgets',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function mockAuth(user: User) {
  mockedUseAuth.mockReturnValue({
    user,
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  });
}

function renderPage(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('CategoriesPage', () => {
  it('renders categories returned by the API', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listCategories.mockResolvedValue([SAMPLE_CATEGORY]);

    renderPage(<CategoriesPage />);

    expect(await screen.findByText('Electronics')).toBeInTheDocument();
    expect(screen.getByText('Gadgets')).toBeInTheDocument();
  });

  it('hides write controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listCategories.mockResolvedValue([SAMPLE_CATEGORY]);

    renderPage(<CategoriesPage />);

    await screen.findByText('Electronics');
    expect(screen.queryByRole('button', { name: /add category/i })).not.toBeInTheDocument();
  });

  it('lets a manager create a category', async () => {
    mockAuth(MANAGER);
    mockedApi.listCategories.mockResolvedValue([]);
    mockedApi.createCategory.mockResolvedValue({ ...SAMPLE_CATEGORY, id: 2 });
    const user = userEvent.setup();

    renderPage(<CategoriesPage />);
    await user.click(await screen.findByRole('button', { name: /add category/i }));
    await user.type(screen.getByLabelText(/name/i), 'Electronics');
    await user.click(screen.getByRole('button', { name: /save/i }));

    // TanStack Query's mutationFn is invoked with an internal context object
    // as a second argument, so assert on the first call argument directly
    // rather than using toHaveBeenCalledWith (which checks the full arg list).
    await waitFor(() =>
      expect(mockedApi.createCategory.mock.calls[0]?.[0]).toEqual({
        name: 'Electronics',
        description: null,
      }),
    );
  });

  it('lets a manager delete a category after confirming', async () => {
    mockAuth(MANAGER);
    mockedApi.listCategories.mockResolvedValue([SAMPLE_CATEGORY]);
    mockedApi.deleteCategory.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderPage(<CategoriesPage />);
    await user.click(await screen.findByLabelText(/delete electronics/i));

    await waitFor(() => expect(mockedApi.deleteCategory.mock.calls[0]?.[0]).toBe(1));
  });

  it('does not delete when the confirmation is declined', async () => {
    mockAuth(MANAGER);
    mockedApi.listCategories.mockResolvedValue([SAMPLE_CATEGORY]);
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const user = userEvent.setup();

    renderPage(<CategoriesPage />);
    await user.click(await screen.findByLabelText(/delete electronics/i));

    expect(mockedApi.deleteCategory).not.toHaveBeenCalled();
  });

  it('lets a manager edit a category', async () => {
    mockAuth(MANAGER);
    mockedApi.listCategories.mockResolvedValue([SAMPLE_CATEGORY]);
    mockedApi.updateCategory.mockResolvedValue({ ...SAMPLE_CATEGORY, name: 'Updated' });
    const user = userEvent.setup();

    renderPage(<CategoriesPage />);
    await user.click(await screen.findByLabelText(/edit electronics/i));
    const nameField = screen.getByLabelText(/name/i);
    await user.clear(nameField);
    await user.type(nameField, 'Updated');
    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(mockedApi.updateCategory.mock.calls[0]?.[0]).toBe(1));
    expect(mockedApi.updateCategory.mock.calls[0]?.[1]).toEqual({
      name: 'Updated',
      description: 'Gadgets',
    });
  });

  it('closes the dialog when cancelled', async () => {
    mockAuth(MANAGER);
    mockedApi.listCategories.mockResolvedValue([]);
    const user = userEvent.setup();

    renderPage(<CategoriesPage />);
    await user.click(await screen.findByRole('button', { name: /add category/i }));
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(screen.queryByLabelText(/name/i)).not.toBeInTheDocument();
  });

  it('shows a conflict error when the category name already exists', async () => {
    mockAuth(MANAGER);
    mockedApi.listCategories.mockResolvedValue([]);
    mockedApi.createCategory.mockRejectedValue({ response: { status: 409 } });
    const user = userEvent.setup();

    renderPage(<CategoriesPage />);
    await user.click(await screen.findByRole('button', { name: /add category/i }));
    await user.type(screen.getByLabelText(/name/i), 'Electronics');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(
      await screen.findByText('A category with that name already exists.'),
    ).toBeInTheDocument();
  });
});
