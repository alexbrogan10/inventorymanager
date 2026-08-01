import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import * as notificationsApi from './api';
import { NotificationBell } from './NotificationBell';
import type { Notification } from './types';
import * as useNotificationsModule from './useNotifications';

vi.mock('./api');
vi.mock('./useNotifications');

const mockedApi = vi.mocked(notificationsApi);
const mockedUseNotifications = vi.mocked(useNotificationsModule.useNotifications);

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: 1,
    type: 'low_stock',
    severity: 'warning',
    title: 'Low stock: Widget',
    message: 'Widget (WIDGET-001) has dropped to 4 units, below the minimum of 5.',
    product_id: 1,
    purchase_order_id: null,
    is_read: false,
    created_at: '2026-08-01T12:00:00Z',
    ...overrides,
  };
}

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <ThemeProvider theme={getTheme('light')}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe('NotificationBell', () => {
  it('shows the unread count as a badge', () => {
    mockedUseNotifications.mockReturnValue({
      unreadCount: 3,
      toastQueue: [],
      dismissToast: vi.fn(),
    });

    renderWithProviders(<NotificationBell />);

    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('lists recent notifications when opened', async () => {
    const user = userEvent.setup();
    mockedUseNotifications.mockReturnValue({
      unreadCount: 1,
      toastQueue: [],
      dismissToast: vi.fn(),
    });
    mockedApi.listNotifications.mockResolvedValue({
      items: [makeNotification()],
      total: 1,
      page: 1,
      page_size: 5,
    });

    renderWithProviders(<NotificationBell />);
    await user.click(screen.getByLabelText('Notifications'));

    expect(await screen.findByText('Low stock: Widget')).toBeInTheDocument();
  });

  it('marks all read when the button is clicked', async () => {
    const user = userEvent.setup();
    mockedUseNotifications.mockReturnValue({
      unreadCount: 1,
      toastQueue: [],
      dismissToast: vi.fn(),
    });
    mockedApi.listNotifications.mockResolvedValue({
      items: [makeNotification()],
      total: 1,
      page: 1,
      page_size: 5,
    });
    mockedApi.markAllNotificationsRead.mockResolvedValue({ marked_count: 1 });

    renderWithProviders(<NotificationBell />);
    await user.click(screen.getByLabelText('Notifications'));
    await screen.findByText('Low stock: Widget');
    await user.click(screen.getByText('Mark all read'));

    await waitFor(() => expect(mockedApi.markAllNotificationsRead).toHaveBeenCalled());
  });
});
