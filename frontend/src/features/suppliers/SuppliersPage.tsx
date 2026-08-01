import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import {
  Alert,
  Box,
  Button,
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

import { PageLoading } from '../../components/PageLoading';
import { useAuth } from '../auth/useAuth';
import { createSupplier, deleteSupplier, listSuppliers, updateSupplier } from './api';
import { SupplierFormDialog } from './SupplierFormDialog';
import type { Supplier, SupplierInput } from './types';

type DialogState = { mode: 'create' } | { mode: 'edit'; supplier: Supplier };

export function SuppliersPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [dialogState, setDialogState] = useState<DialogState | null>(null);

  const {
    data: suppliers,
    isPending,
    isError,
  } = useQuery({ queryKey: ['suppliers'], queryFn: listSuppliers });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['suppliers'] });
  const createMutation = useMutation({ mutationFn: createSupplier, onSuccess: invalidate });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: SupplierInput }) => updateSupplier(id, input),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({ mutationFn: deleteSupplier, onSuccess: invalidate });

  function handleSubmit(input: SupplierInput) {
    if (dialogState?.mode === 'edit') {
      return updateMutation.mutateAsync({ id: dialogState.supplier.id, input });
    }
    return createMutation.mutateAsync(input);
  }

  function handleDelete(supplier: Supplier) {
    if (window.confirm(`Delete supplier "${supplier.company_name}"? This cannot be undone.`)) {
      deleteMutation.mutate(supplier.id);
    }
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Suppliers</Typography>
        {canWrite && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDialogState({ mode: 'create' })}
          >
            Add Supplier
          </Button>
        )}
      </Box>

      {isPending && <PageLoading />}
      {isError && <Alert severity="error">Failed to load suppliers.</Alert>}

      {suppliers && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Company</TableCell>
                <TableCell>Contact</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Phone</TableCell>
                <TableCell align="right">Lead time (days)</TableCell>
                {canWrite && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {suppliers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canWrite ? 6 : 5}>
                    <Typography color="text.secondary">No suppliers yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {suppliers.map((supplier) => (
                <TableRow key={supplier.id}>
                  <TableCell>{supplier.company_name}</TableCell>
                  <TableCell>{supplier.contact_person}</TableCell>
                  <TableCell>{supplier.email}</TableCell>
                  <TableCell>{supplier.phone}</TableCell>
                  <TableCell align="right">{supplier.lead_time_days}</TableCell>
                  {canWrite && (
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`Edit ${supplier.company_name}`}
                        onClick={() => setDialogState({ mode: 'edit', supplier })}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Delete ${supplier.company_name}`}
                        onClick={() => handleDelete(supplier)}
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
        <SupplierFormDialog
          mode={dialogState.mode}
          initialValue={dialogState.mode === 'edit' ? dialogState.supplier : undefined}
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
