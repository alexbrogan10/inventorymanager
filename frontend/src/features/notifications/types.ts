export type NotificationType = 'low_stock' | 'overstock' | 'order_arrived' | 'anomaly';

export type NotificationSeverity = 'info' | 'warning' | 'critical';

export interface Notification {
  id: number;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  message: string;
  product_id: number | null;
  purchase_order_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface PaginatedNotifications {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
}

export interface UnreadCount {
  count: number;
}

export interface MarkAllReadResult {
  marked_count: number;
}

export interface NotificationListParams {
  page?: number;
  page_size?: number;
  unread_only?: boolean;
}
