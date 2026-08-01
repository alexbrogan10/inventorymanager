import { createContext } from 'react';

import type { Notification } from './types';

export interface NotificationsContextValue {
  unreadCount: number;
  // Notifications the user hasn't been shown as a toast yet - a Snackbar
  // component consumes and dismisses these one at a time. See
  // NotificationsContext.tsx for why this isn't just "all unread".
  toastQueue: Notification[];
  dismissToast: (id: number) => void;
}

export const NotificationsContext = createContext<NotificationsContextValue | undefined>(undefined);
