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

import { formatCurrency, formatDateTime } from './format';
import type { PurchaseHistoryReport } from './types';

export function PurchaseHistoryTable({ report }: { report: PurchaseHistoryReport }) {
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>PO #</TableCell>
            <TableCell>Date</TableCell>
            <TableCell>Supplier</TableCell>
            <TableCell>Warehouse</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Items</TableCell>
            <TableCell align="right">Cost</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {report.rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={7}>
                <Typography color="text.secondary">
                  No purchase orders in this date range.
                </Typography>
              </TableCell>
            </TableRow>
          )}
          {report.rows.map((row) => (
            <TableRow key={row.purchase_order_id} hover>
              <TableCell>{row.purchase_order_id}</TableCell>
              <TableCell>{formatDateTime(row.created_at)}</TableCell>
              <TableCell>{row.supplier}</TableCell>
              <TableCell>{row.warehouse}</TableCell>
              <TableCell>
                <Chip label={row.status} size="small" />
              </TableCell>
              <TableCell align="right">{row.item_count}</TableCell>
              <TableCell align="right">{formatCurrency(row.total_cost)}</TableCell>
            </TableRow>
          ))}
          {report.rows.length > 0 && (
            <TableRow>
              <TableCell colSpan={6} />
              <TableCell align="right">
                <strong>{formatCurrency(report.total_cost)}</strong>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
