import {
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

import { formatDateTime } from './format';
import type { ProductMovementEventType, ProductMovementReport } from './types';

const EVENT_LABELS: Record<ProductMovementEventType, string> = {
  purchase_receipt: 'Purchase receipt',
  sale: 'Sale',
  transfer_in: 'Transfer in',
  transfer_out: 'Transfer out',
};

export function ProductMovementTable({ report }: { report: ProductMovementReport }) {
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Date</TableCell>
            <TableCell>Event</TableCell>
            <TableCell>Warehouse</TableCell>
            <TableCell>Reference</TableCell>
            <TableCell align="right">Quantity change</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {report.rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5}>
                <Typography color="text.secondary">
                  No movement recorded for this product in this date range.
                </Typography>
              </TableCell>
            </TableRow>
          )}
          {report.rows.map((row) => (
            // (reference, type) is unique per row - a transfer's out/in legs
            // share a reference but never a type.
            <TableRow key={`${row.reference}-${row.type}`} hover>
              <TableCell>{formatDateTime(row.timestamp)}</TableCell>
              <TableCell>
                <Chip label={EVENT_LABELS[row.type]} size="small" />
              </TableCell>
              <TableCell>{row.warehouse}</TableCell>
              <TableCell>{row.reference}</TableCell>
              <TableCell
                align="right"
                sx={{ color: row.quantity_change >= 0 ? 'success.main' : 'error.main' }}
              >
                {row.quantity_change > 0 ? `+${row.quantity_change}` : row.quantity_change}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
