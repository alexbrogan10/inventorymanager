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
import { createSale, listSales } from './api';
import { SaleFormDialog } from './SaleFormDialog';
import type { Sale } from './types';

function saleTotal(sale: Sale): number {
  return sale.items.reduce((sum, item) => sum + item.quantity * Number(item.unit_price), 0);
}

export function SalesPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [isCreating, setIsCreating] = useState(false);

  const { data: sales, isPending, isError } = useQuery({ queryKey: ['sales'], queryFn: listSales });

  const createMutation = useMutation({
    mutationFn: createSale,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Sales</Typography>
        {canWrite && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setIsCreating(true)}>
            Record Sale
          </Button>
        )}
      </Box>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load sales.</Alert>}

      {sales && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>Customer</TableCell>
                <TableCell>Warehouse</TableCell>
                <TableCell align="right">Items</TableCell>
                <TableCell align="right">Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sales.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Typography color="text.secondary">No sales recorded yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {sales.map((sale) => (
                <TableRow key={sale.id} hover>
                  <TableCell>
                    <RouterLink to={`/sales/${sale.id}`}>#{sale.id}</RouterLink>
                  </TableCell>
                  <TableCell>{sale.customer_name}</TableCell>
                  <TableCell>{sale.warehouse.name}</TableCell>
                  <TableCell align="right">{sale.items.length}</TableCell>
                  <TableCell align="right">${saleTotal(sale).toFixed(2)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {isCreating && (
        <SaleFormDialog
          onClose={() => setIsCreating(false)}
          onSubmit={async (input) => {
            const sale = await createMutation.mutateAsync(input);
            setIsCreating(false);
            return sale;
          }}
        />
      )}
    </Stack>
  );
}
