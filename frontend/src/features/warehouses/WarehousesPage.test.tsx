import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import type { User } from '../auth/types';
import { useAuth } from '../auth/useAuth';
import * as warehousesApi from './api';
import { WarehousesPage } from './WarehousesPage';
import type { Warehouse } from './types';

vi.mock('../auth/useAuth');
vi.mock('./api');

const mockedUseAuth = vi.mocked(useAuth);
const mockedApi = vi.mocked(warehousesApi);

const MANAGER: User = {
  id: 1,
  email: 'manager@example.com',
  full_name: 'Manager User',
  role: 'manager',
  is_active: true,
  created_at: '',
};

const EMPLOYEE: User = { ...MANAGER, id: 2, email: 'employee@example.com', role: 'employee' };

const SAMPLE_WAREHOUSE: Warehouse = {
  id: 1,
  name: 'Main Warehouse',
  address: '1 Main St',
  notes: 'Primary distribution center',
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

describe('WarehousesPage', () => {
  it('renders warehouses returned by the API', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listWarehouses.mockResolvedValue([SAMPLE_WAREHOUSE]);

    renderPage(<WarehousesPage />);

    expect(await screen.findByText('Main Warehouse')).toBeInTheDocument();
    expect(screen.getByText('1 Main St')).toBeInTheDocument();
  });

  it('hides write controls for an employee', async () => {
    mockAuth(EMPLOYEE);
    mockedApi.listWarehouses.mockResolvedValue([SAMPLE_WAREHOUSE]);

    renderPage(<WarehousesPage />);

    await screen.findByText('Main Warehouse');
    expect(screen.queryByRole('button', { name: /add warehouse/i })).not.toBeInTheDocument();
  });

  it('lets a manager create a warehouse', async () => {
    mockAuth(MANAGER);
    mockedApi.listWarehouses.mockResolvedValue([]);
    mockedApi.createWarehouse.mockResolvedValue({ ...SAMPLE_WAREHOUSE, id: 2 });
    const user = userEvent.setup();

    renderPage(<WarehousesPage />);
    await user.click(await screen.findByRole('button', { name: /add warehouse/i }));
    await user.type(screen.getByLabelText(/name/i), 'East Warehouse');
    await user.type(screen.getByLabelText(/address/i), '2 East St');
    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() =>
      expect(mockedApi.createWarehouse.mock.calls[0]?.[0]).toEqual({
        name: 'East Warehouse',
        address: '2 East St',
        notes: null,
      }),
    );
  });

  it('lets a manager delete a warehouse after confirming', async () => {
    mockAuth(MANAGER);
    mockedApi.listWarehouses.mockResolvedValue([SAMPLE_WAREHOUSE]);
    mockedApi.deleteWarehouse.mockResolvedValue(undefined);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const user = userEvent.setup();

    renderPage(<WarehousesPage />);
    await user.click(await screen.findByLabelText(/delete main warehouse/i));

    await waitFor(() => expect(mockedApi.deleteWarehouse.mock.calls[0]?.[0]).toBe(1));
  });
});
