import { apiClient } from '../../api/client';
import type {
  MarkAllReadResult,
  Notification,
  NotificationListParams,
  PaginatedNotifications,
  UnreadCount,
} from './types';

export async function listNotifications(
  params: NotificationListParams = {},
): Promise<PaginatedNotifications> {
  const { data } = await apiClient.get<PaginatedNotifications>('/notifications', { params });
  return data;
}

export async function getUnreadCount(): Promise<UnreadCount> {
  const { data } = await apiClient.get<UnreadCount>('/notifications/unread-count');
  return data;
}

export async function markNotificationRead(id: number): Promise<Notification> {
  const { data } = await apiClient.patch<Notification>(`/notifications/${id}/read`);
  return data;
}

export async function markAllNotificationsRead(): Promise<MarkAllReadResult> {
  const { data } = await apiClient.patch<MarkAllReadResult>('/notifications/read-all');
  return data;
}
