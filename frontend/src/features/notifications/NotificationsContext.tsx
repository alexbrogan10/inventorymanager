import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import { useAuth } from '../auth/useAuth';
import { getUnreadCount, listNotifications } from './api';
import { NotificationsContext } from './context';
import type { Notification } from './types';

// There's no websocket/push infra in this system - the bell badge and toast
// popups are both driven by polling the same two lightweight endpoints
// (unread count, first page of unread notifications) rather than fetching
// the full notification history on an interval.
const POLL_INTERVAL_MS = 15_000;

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const seenIds = useRef<Set<number>>(new Set());
  const [hasSeeded, setHasSeeded] = useState(false);
  const [toastQueue, setToastQueue] = useState<Notification[]>([]);

  // A fresh login (or logout) shouldn't toast every notification that was
  // already unread before this session started.
  useEffect(() => {
    seenIds.current = new Set();
    setHasSeeded(false);
    setToastQueue([]);
  }, [user?.id]);

  const { data: unreadCountData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: getUnreadCount,
    enabled: Boolean(user),
    refetchInterval: POLL_INTERVAL_MS,
  });

  const { data: recentUnread } = useQuery({
    queryKey: ['notifications', 'recent-unread'],
    queryFn: () => listNotifications({ page: 1, page_size: 10, unread_only: true }),
    enabled: Boolean(user),
    refetchInterval: POLL_INTERVAL_MS,
  });

  useEffect(() => {
    if (!recentUnread) return;

    if (!hasSeeded) {
      recentUnread.items.forEach((notification) => seenIds.current.add(notification.id));
      setHasSeeded(true);
      return;
    }

    const unseen = recentUnread.items.filter(
      (notification) => !seenIds.current.has(notification.id),
    );
    if (unseen.length === 0) return;
    unseen.forEach((notification) => seenIds.current.add(notification.id));
    setToastQueue((queue) => [...queue, ...unseen]);
  }, [recentUnread, hasSeeded]);

  const dismissToast = useCallback((id: number) => {
    setToastQueue((queue) => queue.filter((notification) => notification.id !== id));
  }, []);

  const value = useMemo(
    () => ({ unreadCount: unreadCountData?.count ?? 0, toastQueue, dismissToast }),
    [unreadCountData, toastQueue, dismissToast],
  );

  return <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>;
}
