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
import { createCategory, deleteCategory, listCategories, updateCategory } from './api';
import { CategoryFormDialog } from './CategoryFormDialog';
import type { Category, CategoryInput } from './types';

type DialogState = { mode: 'create' } | { mode: 'edit'; category: Category };

export function CategoriesPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [dialogState, setDialogState] = useState<DialogState | null>(null);

  const {
    data: categories,
    isPending,
    isError,
  } = useQuery({ queryKey: ['categories'], queryFn: listCategories });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['categories'] });
  const createMutation = useMutation({ mutationFn: createCategory, onSuccess: invalidate });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: CategoryInput }) => updateCategory(id, input),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({ mutationFn: deleteCategory, onSuccess: invalidate });

  function handleSubmit(input: CategoryInput) {
    if (dialogState?.mode === 'edit') {
      return updateMutation.mutateAsync({ id: dialogState.category.id, input });
    }
    return createMutation.mutateAsync(input);
  }

  function handleDelete(category: Category) {
    if (window.confirm(`Delete category "${category.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(category.id);
    }
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Categories</Typography>
        {canWrite && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDialogState({ mode: 'create' })}
          >
            Add Category
          </Button>
        )}
      </Box>

      {isPending && <PageLoading />}
      {isError && <Alert severity="error">Failed to load categories.</Alert>}

      {categories && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                {canWrite && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {categories.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canWrite ? 3 : 2}>
                    <Typography color="text.secondary">No categories yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {categories.map((category) => (
                <TableRow key={category.id}>
                  <TableCell>{category.name}</TableCell>
                  <TableCell>{category.description ?? '—'}</TableCell>
                  {canWrite && (
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        aria-label={`Edit ${category.name}`}
                        onClick={() => setDialogState({ mode: 'edit', category })}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Delete ${category.name}`}
                        onClick={() => handleDelete(category)}
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
        <CategoryFormDialog
          mode={dialogState.mode}
          initialValue={dialogState.mode === 'edit' ? dialogState.category : undefined}
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
