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

import { formatCurrency } from './format';
import type { SupplierPerformanceReport } from './types';

export function SupplierPerformanceTable({ report }: { report: SupplierPerformanceReport }) {
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Supplier</TableCell>
            <TableCell align="right">Total orders</TableCell>
            <TableCell align="right">Received</TableCell>
            <TableCell align="right">Cancelled</TableCell>
            <TableCell align="right">Total spend</TableCell>
            <TableCell align="right">Avg. lead time (days)</TableCell>
            <TableCell align="right">On-time rate</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {report.rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={7}>
                <Typography color="text.secondary">No suppliers with orders yet.</Typography>
              </TableCell>
            </TableRow>
          )}
          {report.rows.map((row) => (
            <TableRow key={row.supplier_id} hover>
              <TableCell>{row.company_name}</TableCell>
              <TableCell align="right">{row.total_orders}</TableCell>
              <TableCell align="right">{row.total_received}</TableCell>
              <TableCell align="right">{row.total_cancelled}</TableCell>
              <TableCell align="right">{formatCurrency(row.total_spend)}</TableCell>
              <TableCell align="right">
                {row.average_lead_time_days === null ? '—' : row.average_lead_time_days.toFixed(1)}
              </TableCell>
              <TableCell align="right">
                {row.on_time_rate === null ? '—' : `${Math.round(row.on_time_rate * 100)}%`}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
