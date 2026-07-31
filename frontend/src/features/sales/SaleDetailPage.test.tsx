import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import type { Warehouse } from '../warehouses/types';
import * as salesApi from './api';
import { SaleDetailPage } from './SaleDetailPage';
import type { Sale } from './types';

vi.mock('./api');

const mockedApi = vi.mocked(salesApi);

const WAREHOUSE: Warehouse = {
  id: 1,
  name: 'Main Warehouse',
  address: '1 Main St',
  notes: null,
  created_at: '',
  updated_at: '',
};

const SALE: Sale = {
  id: 1,
  warehouse: WAREHOUSE,
  customer_name: 'Jane Customer',
  customer_email: 'jane.customer@example.com',
  customer_phone: '555-0001',
  notes: 'Handled with care',
  sold_by_id: 1,
  items: [
    {
      id: 1,
      product: { id: 1, sku: 'WIDGET-001', name: 'Widget', unit_type: 'each' },
      quantity: 3,
      unit_price: '9.99',
    },
    {
      id: 2,
      product: { id: 2, sku: 'GADGET-002', name: 'Gadget', unit_type: 'each' },
      quantity: 2,
      unit_price: '15.00',
    },
  ],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/sales/1']}>
        <Routes>
          <Route path="/sales" element={<div>Sales List</div>} />
          <Route path="/sales/:id" element={<SaleDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('SaleDetailPage', () => {
  it('renders sale details, line items, and the computed revenue total', async () => {
    mockedApi.getSale.mockResolvedValue(SALE);

    renderDetail();

    expect(await screen.findByText('Sale #1')).toBeInTheDocument();
    expect(screen.getByText('Jane Customer')).toBeInTheDocument();
    expect(screen.getByText('Main Warehouse')).toBeInTheDocument();
    expect(screen.getByText(/WIDGET-001/)).toBeInTheDocument();
    expect(screen.getByText(/GADGET-002/)).toBeInTheDocument();
    // (3 * 9.99) + (2 * 15.00) = 29.97 + 30.00 = 59.97
    expect(screen.getByText('$59.97')).toBeInTheDocument();
  });

  it('shows a not-found message for a missing sale', async () => {
    mockedApi.getSale.mockRejectedValue(new Error('not found'));

    renderDetail();

    expect(await screen.findByText('Sale not found.')).toBeInTheDocument();
  });
});
