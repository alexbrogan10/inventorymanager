import { Chip } from '@mui/material';

import type { PurchaseOrderStatus } from './types';

const STATUS_LABELS: Record<PurchaseOrderStatus, string> = {
  ordered: 'Ordered',
  shipped: 'Shipped',
  received: 'Received',
  cancelled: 'Cancelled',
};

const STATUS_COLORS: Record<PurchaseOrderStatus, 'info' | 'warning' | 'success' | 'default'> = {
  ordered: 'info',
  shipped: 'warning',
  received: 'success',
  cancelled: 'default',
};

export function StatusChip({ status }: { status: PurchaseOrderStatus }) {
  return <Chip label={STATUS_LABELS[status]} color={STATUS_COLORS[status]} size="small" />;
}
