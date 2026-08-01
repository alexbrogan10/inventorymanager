import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as suppliersApi from './api';
import { SuppliersPage } from './SuppliersPage';
import type { Supplier } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(suppliersApi);

beforeEach(() => {
  vi.clearAllMocks();
});

const ADMIN: User = {
  id: 1,
  email: 'admin@example.com',
  full_name: 'Admin User',
  role: 'admin',
  is_active: true,
  created_at: '',
};

const EMPLOYEE: User = { ...ADMIN, id: 2, email: 'employee@example.com', role: 'employee' };

const SAMPLE_SUPPLIER: Supplier = {
  id: 1,
  company_name: 'Acme Supply Co.',
  contact_person: 'Jane Doe',
  email: 'jane@acme.example',
  phone: '555-0100',
  address: '123 Warehouse Rd',
  lead_time_days: 7,
  notes: null,
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

describe('SuppliersPage', () => {
  it('renders suppliers returned by the API', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listSuppliers.mockResolvedValue([SAMPLE_SUPPLIER]);

    renderPage(<SuppliersPage />);

    expect(await screen.findByText('Acme Supply Co.')).toBeInTheDocument();
    expect(screen.getByText('jane@acme.example')).toBeInTheDocument();
  });

  it('hides write controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listSuppliers.mockResolvedValue([SAMPLE_SUPPLIER]);

    renderPage(<SuppliersPage />);

    await screen.findByText('Acme Supply Co.');
    expect(screen.queryByRole('button', { name: /add supplier/i })).not.toBeInTheDocument();
  });

  it('lets an admin create a supplier', async () => {
    mockAuth(ADMIN);
    mockedApi.listSuppliers.mockResolvedValue([]);
    mockedApi.createSupplier.mockResolvedValue({ ...SAMPLE_SUPPLIER, id: 2 });
    const user = userEvent.setup();

    renderPage(<SuppliersPage />);
    await user.click(await screen.findByRole('button', { name: /add supplier/i }));
    await user.type(screen.getByLabelText(/company name/i), 'Acme Supply Co.');
    await user.type(screen.getByLabelText(/contact person/i), 'Jane Doe');
    await user.type(screen.getByLabelText(/^email/i), 'jane@acme.example');
    await user.type(screen.getByLabelText(/phone/i), '555-0100');
    await user.type(screen.getByLabelText(/address/i), '123 Warehouse Rd');
    await user.click(screen.getByRole('button', { name: /save/i }));

    // TanStack Query's mutationFn is invoked with an internal context object
    // as a second argument, so assert on the first call argument directly
    // rather than using toHaveBeenCalledWith (which checks the full arg list).
    await waitFor(() =>
      expect(mockedApi.createSupplier.mock.calls[0]?.[0]).toEqual(
        expect.objectContaining({ company_name: 'Acme Supply Co.', lead_time_days: 7 }),
      ),
    );
  });

  it('lets an admin delete a supplier after confirming', async () => {
    mockAuth(ADMIN);
    mockedApi.listSuppliers.mockResolvedValue([SAMPLE_SUPPLIER]);
    mockedApi.deleteSupplier.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderPage(<SuppliersPage />);
    await user.click(await screen.findByLabelText(/delete acme supply co\./i));

    await waitFor(() => expect(mockedApi.deleteSupplier.mock.calls[0]?.[0]).toBe(1));
  });

  it('does not delete when the confirmation is declined', async () => {
    mockAuth(ADMIN);
    mockedApi.listSuppliers.mockResolvedValue([SAMPLE_SUPPLIER]);
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const user = userEvent.setup();

    renderPage(<SuppliersPage />);
    await user.click(await screen.findByLabelText(/delete acme supply co\./i));

    expect(mockedApi.deleteSupplier).not.toHaveBeenCalled();
  });

  it('lets an admin edit a supplier', async () => {
    mockAuth(ADMIN);
    mockedApi.listSuppliers.mockResolvedValue([SAMPLE_SUPPLIER]);
    mockedApi.updateSupplier.mockResolvedValue({ ...SAMPLE_SUPPLIER, company_name: 'Updated Co.' });
    const user = userEvent.setup();

    renderPage(<SuppliersPage />);
    await user.click(await screen.findByLabelText(/edit acme supply co\./i));
    const nameField = screen.getByLabelText(/company name/i);
    await user.clear(nameField);
    await user.type(nameField, 'Updated Co.');
    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => expect(mockedApi.updateSupplier.mock.calls[0]?.[0]).toBe(1));
    expect(mockedApi.updateSupplier.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({ company_name: 'Updated Co.' }),
    );
  });

  it('closes the dialog when cancelled', async () => {
    mockAuth(ADMIN);
    mockedApi.listSuppliers.mockResolvedValue([]);
    const user = userEvent.setup();

    renderPage(<SuppliersPage />);
    await user.click(await screen.findByRole('button', { name: /add supplier/i }));
    expect(screen.getByLabelText(/company name/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /cancel/i }));

    expect(screen.queryByLabelText(/company name/i)).not.toBeInTheDocument();
  });

  it('shows a conflict error when the company name already exists', async () => {
    mockAuth(ADMIN);
    mockedApi.listSuppliers.mockResolvedValue([]);
    mockedApi.createSupplier.mockRejectedValue({ response: { status: 409 } });
    const user = userEvent.setup();

    renderPage(<SuppliersPage />);
    await user.click(await screen.findByRole('button', { name: /add supplier/i }));
    await user.type(screen.getByLabelText(/company name/i), 'Acme Supply Co.');
    await user.type(screen.getByLabelText(/contact person/i), 'Jane Doe');
    await user.type(screen.getByLabelText(/^email/i), 'jane@acme.example');
    await user.type(screen.getByLabelText(/phone/i), '555-0100');
    await user.type(screen.getByLabelText(/address/i), '123 Warehouse Rd');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(
      await screen.findByText('A supplier with that company name already exists.'),
    ).toBeInTheDocument();
  });
});
