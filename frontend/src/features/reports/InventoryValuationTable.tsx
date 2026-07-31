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
import type { InventoryValuationReport } from './types';

export function InventoryValuationTable({ report }: { report: InventoryValuationReport }) {
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>SKU</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Category</TableCell>
            <TableCell>Supplier</TableCell>
            <TableCell align="right">Quantity</TableCell>
            <TableCell align="right">Purchase price</TableCell>
            <TableCell align="right">Selling price</TableCell>
            <TableCell align="right">Value at cost</TableCell>
            <TableCell align="right">Potential revenue</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {report.rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={9}>
                <Typography color="text.secondary">No products found.</Typography>
              </TableCell>
            </TableRow>
          )}
          {report.rows.map((row) => (
            <TableRow key={row.product_id} hover>
              <TableCell>{row.sku}</TableCell>
              <TableCell>{row.name}</TableCell>
              <TableCell>{row.category}</TableCell>
              <TableCell>{row.supplier}</TableCell>
              <TableCell align="right">{row.total_quantity}</TableCell>
              <TableCell align="right">{formatCurrency(row.purchase_price)}</TableCell>
              <TableCell align="right">{formatCurrency(row.selling_price)}</TableCell>
              <TableCell align="right">{formatCurrency(row.value_at_cost)}</TableCell>
              <TableCell align="right">{formatCurrency(row.potential_revenue)}</TableCell>
            </TableRow>
          ))}
          {report.rows.length > 0 && (
            <TableRow>
              <TableCell colSpan={7} />
              <TableCell align="right">
                <strong>{formatCurrency(report.total_value_at_cost)}</strong>
              </TableCell>
              <TableCell align="right">
                <strong>{formatCurrency(report.total_potential_revenue)}</strong>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
