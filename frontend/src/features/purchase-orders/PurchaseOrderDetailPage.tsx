import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import {
  Alert,
  Box,
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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link as RouterLink, useParams } from 'react-router';

import { useAuth } from '../auth/useAuth';
import {
  cancelPurchaseOrder,
  getPurchaseOrder,
  receivePurchaseOrder,
  shipPurchaseOrder,
} from './api';
import { StatusChip } from './StatusChip';

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

export function PurchaseOrderDetailPage() {
  const { id } = useParams();
  const purchaseOrderId = Number(id);
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();

  const {
    data: order,
    isPending,
    isError,
  } = useQuery({
    queryKey: ['purchase-orders', purchaseOrderId],
    queryFn: () => getPurchaseOrder(purchaseOrderId),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    queryClient.invalidateQueries({ queryKey: ['products'] });
  };
  const shipMutation = useMutation({
    mutationFn: () => shipPurchaseOrder(purchaseOrderId),
    onSuccess: invalidate,
  });
  const receiveMutation = useMutation({
    mutationFn: () => receivePurchaseOrder(purchaseOrderId),
    onSuccess: invalidate,
  });
  const cancelMutation = useMutation({
    mutationFn: () => cancelPurchaseOrder(purchaseOrderId),
    onSuccess: invalidate,
  });

  function handleCancel() {
    if (window.confirm('Cancel this purchase order? This cannot be undone.')) {
      cancelMutation.mutate();
    }
  }

  if (isPending) {
    return <CircularProgress />;
  }

  if (isError || !order) {
    return <Alert severity="error">Purchase order not found.</Alert>;
  }

  const totalCost = order.items.reduce(
    (sum, item) => sum + item.quantity_ordered * Number(item.unit_cost),
    0,
  );

  return (
    <Stack spacing={3}>
      <Button
        component={RouterLink}
        to="/purchase-orders"
        startIcon={<ArrowBackIcon />}
        sx={{ alignSelf: 'flex-start' }}
      >
        Back to purchase orders
      </Button>

      <Card>
        <CardContent>
          <Stack
            direction="row"
            sx={{ justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}
          >
            <Box>
              <Typography variant="h4">Purchase Order #{order.id}</Typography>
              <Box sx={{ mt: 1 }}>
                <StatusChip status={order.status} />
              </Box>
            </Box>
            {canWrite && (
              <Stack direction="row" spacing={1}>
                {order.status === 'ordered' && (
                  <Button variant="contained" onClick={() => shipMutation.mutate()}>
                    Ship
                  </Button>
                )}
                {order.status === 'shipped' && (
                  <Button variant="contained" onClick={() => receiveMutation.mutate()}>
                    Receive
                  </Button>
                )}
                {(order.status === 'ordered' || order.status === 'shipped') && (
                  <Button color="error" onClick={handleCancel}>
                    Cancel
                  </Button>
                )}
              </Stack>
            )}
          </Stack>

          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={2}>
            <DetailField label="Supplier" value={order.supplier.company_name} />
            <DetailField label="Warehouse" value={order.warehouse.name} />
            <DetailField
              label="Expected delivery"
              value={
                order.expected_delivery_date
                  ? new Date(order.expected_delivery_date).toLocaleDateString()
                  : '—'
              }
            />
            <DetailField label="Notes" value={order.notes ?? '—'} />
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
                  <TableCell align="right">Ordered</TableCell>
                  <TableCell align="right">Received</TableCell>
                  <TableCell align="right">Unit cost</TableCell>
                  <TableCell align="right">Subtotal</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {order.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {item.product.sku} - {item.product.name}
                    </TableCell>
                    <TableCell align="right">{item.quantity_ordered}</TableCell>
                    <TableCell align="right">{item.quantity_received}</TableCell>
                    <TableCell align="right">${item.unit_cost}</TableCell>
                    <TableCell align="right">
                      ${(item.quantity_ordered * Number(item.unit_cost)).toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow>
                  <TableCell colSpan={4} align="right">
                    <strong>Total</strong>
                  </TableCell>
                  <TableCell align="right">
                    <strong>${totalCost.toFixed(2)}</strong>
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
