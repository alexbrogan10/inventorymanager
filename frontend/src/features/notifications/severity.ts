import type { NotificationSeverity, NotificationType } from './types';

// MUI doesn't have a "critical" severity - it maps onto "error", the most
// severe built-in option, for both Alert and Chip color props.
export function severityToColor(severity: NotificationSeverity): 'info' | 'warning' | 'error' {
  if (severity === 'critical') return 'error';
  return severity;
}

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  low_stock: 'Low Stock',
  overstock: 'Overstock',
  order_arrived: 'Order Arrived',
  anomaly: 'Unusual Demand',
};
