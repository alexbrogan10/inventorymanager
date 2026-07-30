import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import * as healthApi from '../../api/health';
import { DashboardPage } from './DashboardPage';

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('DashboardPage', () => {
  it('shows a success alert when the backend is reachable', async () => {
    vi.spyOn(healthApi, 'getReadiness').mockResolvedValue({ status: 'ok' });

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText(/API reachable/i)).toBeInTheDocument();
  });

  it('shows an error alert when the backend is unreachable', async () => {
    vi.spyOn(healthApi, 'getReadiness').mockRejectedValue(new Error('Network Error'));

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText(/Network Error/i)).toBeInTheDocument();
  });
});
