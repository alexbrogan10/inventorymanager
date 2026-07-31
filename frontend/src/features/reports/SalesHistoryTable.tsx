import {
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
import type { SalesHistoryReport } from './types';

export function SalesHistoryTable({ report }: { report: SalesHistoryReport }) {
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Sale #</TableCell>
            <TableCell>Date</TableCell>
            <TableCell>Customer</TableCell>
            <TableCell>Warehouse</TableCell>
            <TableCell>Sold by</TableCell>
            <TableCell align="right">Items</TableCell>
            <TableCell align="right">Revenue</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {report.rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={7}>
                <Typography color="text.secondary">No sales in this date range.</Typography>
              </TableCell>
            </TableRow>
          )}
          {report.rows.map((row) => (
            <TableRow key={row.sale_id} hover>
              <TableCell>{row.sale_id}</TableCell>
              <TableCell>{formatDateTime(row.created_at)}</TableCell>
              <TableCell>{row.customer_name}</TableCell>
              <TableCell>{row.warehouse}</TableCell>
              <TableCell>{row.sold_by}</TableCell>
              <TableCell align="right">{row.item_count}</TableCell>
              <TableCell align="right">{formatCurrency(row.total_revenue)}</TableCell>
            </TableRow>
          ))}
          {report.rows.length > 0 && (
            <TableRow>
              <TableCell colSpan={6} />
              <TableCell align="right">
                <strong>{formatCurrency(report.total_revenue)}</strong>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
