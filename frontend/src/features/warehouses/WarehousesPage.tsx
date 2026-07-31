import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
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

import { useAuth } from '../auth/useAuth';
import { createWarehouse, deleteWarehouse, listWarehouses, updateWarehouse } from './api';
import { WarehouseFormDialog } from './WarehouseFormDialog';
import type { Warehouse, WarehouseInput } from './types';

type DialogState = { mode: 'create' } | { mode: 'edit'; warehouse: Warehouse };

export function WarehousesPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [dialogState, setDialogState] = useState<DialogState | null>(null);

  const {
    data: warehouses,
    isPending,
    isError,
  } = useQuery({ queryKey: ['warehouses'], queryFn: listWarehouses });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['warehouses'] });
  const createMutation = useMutation({ mutationFn: createWarehouse, onSuccess: invalidate });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: WarehouseInput }) =>
      updateWarehouse(id, input),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({ mutationFn: deleteWarehouse, onSuccess: invalidate });

  function handleSubmit(input: WarehouseInput) {
    if (dialogState?.mode === 'edit') {
      return updateMutation.mutateAsync({ id: dialogState.warehouse.id, input });
    }
    return createMutation.mutateAsync(input);
  }

  function handleDelete(warehouse: Warehouse) {
    if (window.confirm(`Delete warehouse "${warehouse.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(warehouse.id);
    }
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Warehouses</Typography>
        {canWrite && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDialogState({ mode: 'create' })}
          >
            Add Warehouse
          </Button>
        )}
      </Box>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load warehouses.</Alert>}

      {warehouses && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Address</TableCell>
                <TableCell>Notes</TableCell>
                {canWrite && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {warehouses.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canWrite ? 4 : 3}>
                    <Typography color="text.secondary">No warehouses yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {warehouses.map((warehouse) => (
                <TableRow key={warehouse.id}>
                  <TableCell>{warehouse.name}</TableCell>
                  <TableCell>{warehouse.address}</TableCell>
                  <TableCell>{warehouse.notes ?? '—'}</TableCell>
                  {canWrite && (
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`Edit ${warehouse.name}`}
                        onClick={() => setDialogState({ mode: 'edit', warehouse })}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Delete ${warehouse.name}`}
                        onClick={() => handleDelete(warehouse)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {dialogState && (
        <WarehouseFormDialog
          mode={dialogState.mode}
          initialValue={dialogState.mode === 'edit' ? dialogState.warehouse : undefined}
          onClose={() => setDialogState(null)}
          onSubmit={async (input) => {
            await handleSubmit(input);
            setDialogState(null);
          }}
        />
      )}
    </Stack>
  );
}
