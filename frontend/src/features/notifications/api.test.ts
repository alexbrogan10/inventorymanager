import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import {
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from './api';
import type { Notification, PaginatedNotifications } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), patch: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

const NOTIFICATION: Notification = {
  id: 1,
  type: 'low_stock',
  severity: 'warning',
  title: 'Low stock: Widget',
  message: 'Widget (WIDGET-001) has dropped to 4 units, below the minimum of 5.',
  product_id: 1,
  purchase_order_id: null,
  is_read: false,
  created_at: '2026-01-01T00:00:00Z',
};

const PAGE: PaginatedNotifications = { items: [NOTIFICATION], total: 1, page: 1, page_size: 20 };

describe('notifications api', () => {
  it('listNotifications fetches a paginated page with the given params', async () => {
    mockedClient.get.mockResolvedValue({ data: PAGE });

    const result = await listNotifications({ page: 1, page_size: 10, unread_only: true });

    expect(mockedClient.get).toHaveBeenCalledWith('/notifications', {
      params: { page: 1, page_size: 10, unread_only: true },
    });
    expect(result).toEqual(PAGE);
  });

  it('getUnreadCount fetches the unread count', async () => {
    mockedClient.get.mockResolvedValue({ data: { count: 4 } });

    const result = await getUnreadCount();

    expect(mockedClient.get).toHaveBeenCalledWith('/notifications/unread-count');
    expect(result).toEqual({ count: 4 });
  });

  it('markNotificationRead patches the id path', async () => {
    mockedClient.patch.mockResolvedValue({ data: { ...NOTIFICATION, is_read: true } });

    const result = await markNotificationRead(1);

    expect(mockedClient.patch).toHaveBeenCalledWith('/notifications/1/read');
    expect(result.is_read).toBe(true);
  });

  it('markAllNotificationsRead patches the read-all endpoint', async () => {
    mockedClient.patch.mockResolvedValue({ data: { marked_count: 3 } });

    const result = await markAllNotificationsRead();

    expect(mockedClient.patch).toHaveBeenCalledWith('/notifications/read-all');
    expect(result).toEqual({ marked_count: 3 });
  });
});
