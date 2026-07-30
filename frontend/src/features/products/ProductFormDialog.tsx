import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  Stack,
  TextField,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';

import { apiOrigin } from '../../api/client';
import { listCategories } from '../categories/api';
import { listSuppliers } from '../suppliers/api';
import type { Product, ProductInput } from './types';

interface ProductFormDialogProps {
  mode: 'create' | 'edit';
  initialValue?: Product;
  onClose: () => void;
  onSubmit: (input: ProductInput, imageFile: File | null) => Promise<unknown>;
}

export function ProductFormDialog({
  mode,
  initialValue,
  onClose,
  onSubmit,
}: ProductFormDialogProps) {
  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories });
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: listSuppliers });

  const [sku, setSku] = useState(initialValue?.sku ?? '');
  const [barcode, setBarcode] = useState(initialValue?.barcode ?? '');
  const [name, setName] = useState(initialValue?.name ?? '');
  const [description, setDescription] = useState(initialValue?.description ?? '');
  const [categoryId, setCategoryId] = useState(initialValue?.category_id.toString() ?? '');
  const [supplierId, setSupplierId] = useState(initialValue?.supplier_id.toString() ?? '');
  const [purchasePrice, setPurchasePrice] = useState(initialValue?.purchase_price ?? '0.00');
  const [sellingPrice, setSellingPrice] = useState(initialValue?.selling_price ?? '0.00');
  const [currentQuantity, setCurrentQuantity] = useState(
    String(initialValue?.current_quantity ?? 0),
  );
  const [minimumQuantity, setMinimumQuantity] = useState(
    String(initialValue?.minimum_quantity ?? 0),
  );
  const [maximumQuantity, setMaximumQuantity] = useState(
    initialValue?.maximum_quantity != null ? String(initialValue.maximum_quantity) : '',
  );
  const [warehouseLocation, setWarehouseLocation] = useState(
    initialValue?.warehouse_location ?? '',
  );
  const [unitType, setUnitType] = useState(initialValue?.unit_type ?? 'each');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const imagePreviewUrl = useMemo(() => {
    if (imageFile) return URL.createObjectURL(imageFile);
    if (initialValue?.image_url) return `${apiOrigin}${initialValue.image_url}`;
    return null;
  }, [imageFile, initialValue?.image_url]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setImageFile(event.target.files?.[0] ?? null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const input: ProductInput = {
        sku,
        barcode: barcode || null,
        name,
        description: description || null,
        category_id: Number(categoryId),
        supplier_id: Number(supplierId),
        purchase_price: purchasePrice,
        selling_price: sellingPrice,
        current_quantity: Number(currentQuantity),
        minimum_quantity: Number(minimumQuantity),
        maximum_quantity: maximumQuantity === '' ? null : Number(maximumQuantity),
        warehouse_location: warehouseLocation || null,
        unit_type: unitType,
      };
      await onSubmit(input, imageFile);
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      const message =
        status === 409
          ? 'A product with that SKU or barcode already exists.'
          : status === 422
            ? 'Check that category/supplier are selected and quantities are valid.'
            : 'Failed to save product.';
      setError(message);
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>{mode === 'create' ? 'Add Product' : 'Edit Product'}</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Avatar
                variant="rounded"
                src={imagePreviewUrl ?? undefined}
                sx={{ width: 64, height: 64 }}
              >
                {name.slice(0, 1).toUpperCase()}
              </Avatar>
              <Button component="label" variant="outlined" size="small">
                {imagePreviewUrl ? 'Replace image' : 'Upload image'}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  hidden
                  onChange={handleFileChange}
                />
              </Button>
            </Box>

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="SKU"
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Barcode"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  multiline
                  minRows={2}
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  select
                  label="Category"
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  required
                  fullWidth
                >
                  {categories?.map((category) => (
                    <MenuItem key={category.id} value={String(category.id)}>
                      {category.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  select
                  label="Supplier"
                  value={supplierId}
                  onChange={(e) => setSupplierId(e.target.value)}
                  required
                  fullWidth
                >
                  {suppliers?.map((supplier) => (
                    <MenuItem key={supplier.id} value={String(supplier.id)}>
                      {supplier.company_name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Purchase price"
                  value={purchasePrice}
                  onChange={(e) => setPurchasePrice(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Selling price"
                  value={sellingPrice}
                  onChange={(e) => setSellingPrice(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  label="Current quantity"
                  type="number"
                  value={currentQuantity}
                  onChange={(e) => setCurrentQuantity(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  label="Minimum quantity"
                  type="number"
                  value={minimumQuantity}
                  onChange={(e) => setMinimumQuantity(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  label="Maximum quantity"
                  type="number"
                  value={maximumQuantity}
                  onChange={(e) => setMaximumQuantity(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Warehouse location"
                  value={warehouseLocation}
                  onChange={(e) => setWarehouseLocation(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  label="Unit type"
                  value={unitType}
                  onChange={(e) => setUnitType(e.target.value)}
                  required
                  fullWidth
                />
              </Grid>
            </Grid>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isSubmitting}>
            {isSubmitting ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
