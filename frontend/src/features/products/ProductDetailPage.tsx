import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router';

import { apiOrigin } from '../../api/client';
import { useAuth } from '../auth/useAuth';
import { deleteProduct, getProduct, updateProduct, uploadProductImage } from './api';
import { ProductFormDialog } from './ProductFormDialog';
import type { ProductInput } from './types';

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

export function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const navigate = useNavigate();
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);

  const {
    data: product,
    isPending,
    isError,
  } = useQuery({ queryKey: ['products', productId], queryFn: () => getProduct(productId) });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['products'] });
  const updateMutation = useMutation({
    mutationFn: (input: ProductInput) => updateProduct(productId, input),
    onSuccess: invalidate,
  });
  const uploadImageMutation = useMutation({
    mutationFn: (file: File) => uploadProductImage(productId, file),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteProduct(productId),
    onSuccess: () => {
      invalidate();
      navigate('/products');
    },
  });

  async function handleSubmit(input: ProductInput, imageFile: File | null) {
    await updateMutation.mutateAsync(input);
    if (imageFile) {
      await uploadImageMutation.mutateAsync(imageFile);
    }
  }

  function handleDelete() {
    if (product && window.confirm(`Delete product "${product.name}"? This cannot be undone.`)) {
      deleteMutation.mutate();
    }
  }

  if (isPending) {
    return <CircularProgress />;
  }

  if (isError || !product) {
    return <Alert severity="error">Product not found.</Alert>;
  }

  const isLowStock = product.current_quantity < product.minimum_quantity;

  return (
    <Stack spacing={3}>
      <Button
        component={RouterLink}
        to="/products"
        startIcon={<ArrowBackIcon />}
        sx={{ alignSelf: 'flex-start' }}
      >
        Back to products
      </Button>

      <Card>
        <CardContent>
          <Stack direction="row" spacing={3} sx={{ alignItems: 'flex-start' }}>
            <Avatar
              variant="rounded"
              src={product.image_url ? `${apiOrigin}${product.image_url}` : undefined}
              sx={{ width: 120, height: 120, fontSize: 40 }}
            >
              {product.name.slice(0, 1).toUpperCase()}
            </Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h4">{product.name}</Typography>
              <Typography color="text.secondary">
                SKU: {product.sku}
                {product.barcode && ` · Barcode: ${product.barcode}`}
              </Typography>
              {isLowStock && <Chip label="Low stock" color="warning" size="small" sx={{ mt: 1 }} />}
            </Box>
            {canWrite && (
              <Stack direction="row" spacing={1}>
                <Button startIcon={<EditIcon />} onClick={() => setIsEditing(true)}>
                  Edit
                </Button>
                <Button startIcon={<DeleteIcon />} color="error" onClick={handleDelete}>
                  Delete
                </Button>
              </Stack>
            )}
          </Stack>

          <Divider sx={{ my: 3 }} />

          <Grid container spacing={2}>
            <DetailField label="Category" value={product.category.name} />
            <DetailField label="Supplier" value={product.supplier.company_name} />
            <DetailField label="Purchase price" value={`$${product.purchase_price}`} />
            <DetailField label="Selling price" value={`$${product.selling_price}`} />
            <DetailField label="Current quantity" value={String(product.current_quantity)} />
            <DetailField label="Minimum quantity" value={String(product.minimum_quantity)} />
            <DetailField
              label="Maximum quantity"
              value={product.maximum_quantity != null ? String(product.maximum_quantity) : '—'}
            />
            <DetailField label="Unit type" value={product.unit_type} />
            <DetailField label="Warehouse location" value={product.warehouse_location ?? '—'} />
            <DetailField label="Description" value={product.description ?? '—'} />
          </Grid>
        </CardContent>
      </Card>

      {isEditing && (
        <ProductFormDialog
          mode="edit"
          initialValue={product}
          onClose={() => setIsEditing(false)}
          onSubmit={async (input, imageFile) => {
            await handleSubmit(input, imageFile);
            setIsEditing(false);
          }}
        />
      )}
    </Stack>
  );
}
