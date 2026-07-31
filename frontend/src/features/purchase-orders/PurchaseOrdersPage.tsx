import AddIcon from '@mui/icons-material/Add';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
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
import { useState } from 'react';
import { Link as RouterLink } from 'react-router';

import { useAuth } from '../auth/useAuth';
import { createPurchaseOrder, listPurchaseOrders } from './api';
import { PurchaseOrderFormDialog } from './PurchaseOrderFormDialog';
import { StatusChip } from './StatusChip';

export function PurchaseOrdersPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [isCreating, setIsCreating] = useState(false);

  const {
    data: orders,
    isPending,
    isError,
  } = useQuery({ queryKey: ['purchase-orders'], queryFn: listPurchaseOrders });

  const createMutation = useMutation({
    mutationFn: createPurchaseOrder,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['purchase-orders'] }),
  });

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Purchase Orders</Typography>
        {canWrite && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setIsCreating(true)}>
            Create Purchase Order
          </Button>
        )}
      </Box>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load purchase orders.</Alert>}

      {orders && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Supplier</TableCell>
                <TableCell>Warehouse</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Expected delivery</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orders.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Typography color="text.secondary">No purchase orders yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {orders.map((order) => (
                <TableRow key={order.id} hover>
                  <TableCell>
                    <RouterLink to={`/purchase-orders/${order.id}`}>#{order.id}</RouterLink>
                  </TableCell>
                  <TableCell>{order.supplier.company_name}</TableCell>
                  <TableCell>{order.warehouse.name}</TableCell>
                  <TableCell>
                    <StatusChip status={order.status} />
                  </TableCell>
                  <TableCell>
                    {order.expected_delivery_date
                      ? new Date(order.expected_delivery_date).toLocaleDateString()
                      : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {isCreating && (
        <PurchaseOrderFormDialog
          onClose={() => setIsCreating(false)}
          onSubmit={async (input) => {
            const order = await createMutation.mutateAsync(input);
            setIsCreating(false);
            return order;
          }}
        />
      )}
    </Stack>
  );
}
