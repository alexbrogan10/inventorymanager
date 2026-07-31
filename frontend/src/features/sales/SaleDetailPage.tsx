import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import {
  Alert,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink, useParams } from 'react-router';

import { getSale } from './api';

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <Grid size={{ xs: 12, sm: 6 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        {label}
      </Typography>
      <Typography variant="body1">{value}</Typography>
    </Grid>
  );
}

export function SaleDetailPage() {
  const { id } = useParams();
  const saleId = Number(id);

  const {
    data: sale,
    isPending,
    isError,
  } = useQuery({ queryKey: ['sales', saleId], queryFn: () => getSale(saleId) });

  if (isPending) {
    return <CircularProgress />;
  }

  if (isError || !sale) {
    return <Alert severity="error">Sale not found.</Alert>;
  }

  const totalRevenue = sale.items.reduce(
    (sum, item) => sum + item.quantity * Number(item.unit_price),
    0,
  );

  return (
    <Stack spacing={3}>
      <Button
        component={RouterLink}
        to="/sales"
        startIcon={<ArrowBackIcon />}
        sx={{ alignSelf: 'flex-start' }}
      >
        Back to sales
      </Button>

      <Card>
        <CardContent>
          <Typography variant="h4" sx={{ mb: 2 }}>
            Sale #{sale.id}
          </Typography>

          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={2}>
            <DetailField label="Customer name" value={sale.customer_name} />
            <DetailField label="Warehouse" value={sale.warehouse.name} />
            <DetailField label="Customer email" value={sale.customer_email ?? '—'} />
            <DetailField label="Customer phone" value={sale.customer_phone ?? '—'} />
            <DetailField label="Notes" value={sale.notes ?? '—'} />
            <DetailField label="Recorded" value={new Date(sale.created_at).toLocaleString()} />
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Line items
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Product</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Unit price</TableCell>
                  <TableCell align="right">Subtotal</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sale.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {item.product.sku} - {item.product.name}
                    </TableCell>
                    <TableCell align="right">{item.quantity}</TableCell>
                    <TableCell align="right">${item.unit_price}</TableCell>
                    <TableCell align="right">
                      ${(item.quantity * Number(item.unit_price)).toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell colSpan={3} align="right">
                    <strong>Total revenue</strong>
                  </TableCell>
                  <TableCell align="right">
                    <strong>${totalRevenue.toFixed(2)}</strong>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Stack>
  );
}
