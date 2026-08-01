import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import * as notificationsApi from './api';
import { NotificationsPage } from './NotificationsPage';
import type { Notification, PaginatedNotifications } from './types';

vi.mock('./api');

const mockedApi = vi.mocked(notificationsApi);

beforeEach(() => {
  vi.clearAllMocks();
});

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

function makeReport(items: Notification[]): PaginatedNotifications {
  return { items, total: items.length, page: 1, page_size: 20 };
}

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <ThemeProvider theme={getTheme('light')}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </ThemeProvider>,
  );
}

describe('NotificationsPage', () => {
  it('shows an empty state when there are no notifications', async () => {
    mockedApi.listNotifications.mockResolvedValue(makeReport([]));

    renderWithProviders(<NotificationsPage />);

    expect(await screen.findByText('No notifications.')).toBeInTheDocument();
  });

  it('renders a notification row', async () => {
    mockedApi.listNotifications.mockResolvedValue(makeReport([makeNotification()]));

    renderWithProviders(<NotificationsPage />);

    expect(await screen.findByText('Low stock: Widget')).toBeInTheDocument();
    expect(screen.getByText('Low Stock')).toBeInTheDocument();
    expect(screen.getByText('Mark read')).toBeInTheDocument();
  });

  it('shows an error message when the request fails', async () => {
    mockedApi.listNotifications.mockRejectedValue(new Error('Network Error'));

    renderWithProviders(<NotificationsPage />);

    expect(await screen.findByText('Failed to load notifications.')).toBeInTheDocument();
  });

  it('marks a single notification read', async () => {
    const user = userEvent.setup();
    mockedApi.listNotifications.mockResolvedValue(makeReport([makeNotification()]));
    mockedApi.markNotificationRead.mockResolvedValue(makeNotification({ is_read: true }));

    renderWithProviders(<NotificationsPage />);
    await screen.findByText('Low stock: Widget');
    await user.click(screen.getByText('Mark read'));

    await waitFor(() => expect(mockedApi.markNotificationRead).toHaveBeenCalled());
    expect(mockedApi.markNotificationRead.mock.calls[0][0]).toBe(1);
  });

  it('marks all notifications read', async () => {
    const user = userEvent.setup();
    mockedApi.listNotifications.mockResolvedValue(makeReport([makeNotification()]));
    mockedApi.markAllNotificationsRead.mockResolvedValue({ marked_count: 1 });

    renderWithProviders(<NotificationsPage />);
    await screen.findByText('Low stock: Widget');
    await user.click(screen.getByRole('button', { name: 'Mark all read' }));

    await waitFor(() => expect(mockedApi.markAllNotificationsRead).toHaveBeenCalled());
  });

  it('toggles the unread-only filter', async () => {
    const user = userEvent.setup();
    mockedApi.listNotifications.mockResolvedValue(makeReport([makeNotification()]));

    renderWithProviders(<NotificationsPage />);
    await screen.findByText('Low stock: Widget');
    await user.click(screen.getByLabelText('Unread only'));

    await waitFor(() =>
      expect(mockedApi.listNotifications).toHaveBeenCalledWith(
        expect.objectContaining({ unread_only: true }),
      ),
    );
  });

  it('requests the next page when paginating', async () => {
    const user = userEvent.setup();
    mockedApi.listNotifications.mockResolvedValue({
      items: [makeNotification()],
      total: 50,
      page: 1,
      page_size: 20,
    });

    renderWithProviders(<NotificationsPage />);
    await screen.findByText('Low stock: Widget');
    await user.click(screen.getByRole('button', { name: /next page/i }));

    await waitFor(() =>
      expect(mockedApi.listNotifications).toHaveBeenCalledWith({
        page: 2,
        page_size: 20,
        unread_only: false,
      }),
    );
  });

  it('requests a new page size and resets to the first page', async () => {
    const user = userEvent.setup();
    mockedApi.listNotifications.mockResolvedValue({
      items: [makeNotification()],
      total: 50,
      page: 1,
      page_size: 20,
    });

    renderWithProviders(<NotificationsPage />);
    await screen.findByText('Low stock: Widget');
    await user.click(screen.getByRole('combobox', { name: /rows per page/i }));
    await user.click(await screen.findByRole('option', { name: '50' }));

    await waitFor(() =>
      expect(mockedApi.listNotifications).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        unread_only: false,
      }),
    );
  });
});
