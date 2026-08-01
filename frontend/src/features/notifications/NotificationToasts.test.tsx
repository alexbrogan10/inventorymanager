import { ThemeProvider } from '@mui/material/styles';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { getTheme } from '../../theme';
import { NotificationToasts } from './NotificationToasts';
import type { Notification } from './types';
import * as useNotificationsModule from './useNotifications';

vi.mock('./useNotifications');

const mockedUseNotifications = vi.mocked(useNotificationsModule.useNotifications);

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: 1,
    type: 'anomaly',
    severity: 'info',
    title: 'Unusual demand: Widget',
    message: 'Widget (WIDGET-001) sold 10 units today, versus a typical 2.0.',
    product_id: 1,
    purchase_order_id: null,
    is_read: false,
    created_at: '2026-08-01T12:00:00Z',
    ...overrides,
  };
}

function renderWithProviders(ui: ReactElement) {
  return render(<ThemeProvider theme={getTheme('light')}>{ui}</ThemeProvider>);
}

describe('NotificationToasts', () => {
  it('renders nothing when the toast queue is empty', () => {
    mockedUseNotifications.mockReturnValue({
      unreadCount: 0,
      toastQueue: [],
      dismissToast: vi.fn(),
    });

    renderWithProviders(<NotificationToasts />);

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows the head of the toast queue', () => {
    mockedUseNotifications.mockReturnValue({
      unreadCount: 1,
      toastQueue: [makeNotification()],
      dismissToast: vi.fn(),
    });

    renderWithProviders(<NotificationToasts />);

    expect(screen.getByText('Unusual demand: Widget')).toBeInTheDocument();
  });

  it('dismisses the toast when closed', async () => {
    const user = userEvent.setup();
    const dismissToast = vi.fn();
    mockedUseNotifications.mockReturnValue({
      unreadCount: 1,
      toastQueue: [makeNotification()],
      dismissToast,
    });

    renderWithProviders(<NotificationToasts />);
    await user.click(screen.getByLabelText(/close/i));

    expect(dismissToast).toHaveBeenCalledWith(1);
  });
});
