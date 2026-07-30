import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
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
import { Link as RouterLink } from 'react-router';

import { apiOrigin } from '../../api/client';
import { useAuth } from '../auth/useAuth';
import {
  createProduct,
  deleteProduct,
  listProducts,
  updateProduct,
  uploadProductImage,
} from './api';
import { ProductFormDialog } from './ProductFormDialog';
import type { Product, ProductInput } from './types';

type DialogState = { mode: 'create' } | { mode: 'edit'; product: Product };

export function ProductsPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [dialogState, setDialogState] = useState<DialogState | null>(null);

  const {
    data: products,
    isPending,
    isError,
  } = useQuery({ queryKey: ['products'], queryFn: listProducts });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['products'] });
  const createMutation = useMutation({ mutationFn: createProduct, onSuccess: invalidate });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ProductInput }) => updateProduct(id, input),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({ mutationFn: deleteProduct, onSuccess: invalidate });
  const uploadImageMutation = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => uploadProductImage(id, file),
    onSuccess: invalidate,
  });

  async function handleSubmit(input: ProductInput, imageFile: File | null) {
    const product =
      dialogState?.mode === 'edit'
        ? await updateMutation.mutateAsync({ id: dialogState.product.id, input })
        : await createMutation.mutateAsync(input);
    if (imageFile) {
      await uploadImageMutation.mutateAsync({ id: product.id, file: imageFile });
    }
  }

  function handleDelete(product: Product) {
    if (window.confirm(`Delete product "${product.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(product.id);
    }
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Products</Typography>
        {canWrite && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setDialogState({ mode: 'create' })}
          >
            Add Product
          </Button>
        )}
      </Box>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load products.</Alert>}

      {products && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell />
                <TableCell>SKU</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Supplier</TableCell>
                <TableCell align="right">Selling price</TableCell>
                <TableCell align="right">Quantity</TableCell>
                {canWrite && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {products.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canWrite ? 8 : 7}>
                    <Typography color="text.secondary">No products yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {products.map((product) => {
                const isLowStock = product.current_quantity < product.minimum_quantity;
                return (
                  <TableRow key={product.id} hover>
                    <TableCell padding="checkbox">
                      <Avatar
                        variant="rounded"
                        src={product.image_url ? `${apiOrigin}${product.image_url}` : undefined}
                        sx={{ width: 32, height: 32, ml: 1 }}
                      >
                        {product.name.slice(0, 1).toUpperCase()}
                      </Avatar>
                    </TableCell>
                    <TableCell>{product.sku}</TableCell>
                    <TableCell>
                      <RouterLink to={`/products/${product.id}`}>{product.name}</RouterLink>
                    </TableCell>
                    <TableCell>{product.category.name}</TableCell>
                    <TableCell>{product.supplier.company_name}</TableCell>
                    <TableCell align="right">${product.selling_price}</TableCell>
                    <TableCell align="right">
                      <Stack
                        direction="row"
                        spacing={1}
                        sx={{ justifyContent: 'flex-end', alignItems: 'center' }}
                      >
                        <span>{product.current_quantity}</span>
                        {isLowStock && <Chip label="Low stock" color="warning" size="small" />}
                      </Stack>
                    </TableCell>
                    {canWrite && (
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          aria-label={`Edit ${product.name}`}
                          onClick={() => setDialogState({ mode: 'edit', product })}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          aria-label={`Delete ${product.name}`}
                          onClick={() => handleDelete(product)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {dialogState && (
        <ProductFormDialog
          mode={dialogState.mode}
          initialValue={dialogState.mode === 'edit' ? dialogState.product : undefined}
          onClose={() => setDialogState(null)}
          onSubmit={async (input, imageFile) => {
            await handleSubmit(input, imageFile);
            setDialogState(null);
          }}
        />
      )}
    </Stack>
  );
}
