import DeleteIcon from '@mui/icons-material/Delete';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { listProducts } from '../products/api';
import { listSuppliers } from '../suppliers/api';
import { listWarehouses } from '../warehouses/api';
import type { PurchaseOrderInput, PurchaseOrderItemInput } from './types';

interface PurchaseOrderFormDialogProps {
  onClose: () => void;
  onSubmit: (input: PurchaseOrderInput) => Promise<unknown>;
}

interface ItemRow {
  productId: string;
  quantityOrdered: string;
  unitCost: string;
}

const EMPTY_ROW: ItemRow = { productId: '', quantityOrdered: '1', unitCost: '0.00' };

export function PurchaseOrderFormDialog({ onClose, onSubmit }: PurchaseOrderFormDialogProps) {
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: listSuppliers });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: listWarehouses });
  const { data: products } = useQuery({ queryKey: ['products'], queryFn: listProducts });

  const [supplierId, setSupplierId] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ROW }]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateItem(index: number, patch: Partial<ItemRow>) {
    setItems((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addItem() {
    setItems((current) => [...current, { ...EMPTY_ROW }]);
  }

  function removeItem(index: number) {
    setItems((current) => current.filter((_, i) => i !== index));
  }

  const hasValidItems = items.every((row) => row.productId !== '');

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const input: PurchaseOrderInput = {
        supplier_id: Number(supplierId),
        warehouse_id: Number(warehouseId),
        expected_delivery_date: expectedDeliveryDate || null,
        notes: notes || null,
        items: items.map((row): PurchaseOrderItemInput => ({
          product_id: Number(row.productId),
          quantity_ordered: Number(row.quantityOrdered),
          unit_cost: row.unitCost,
        })),
      };
      await onSubmit(input);
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 422
          ? 'Check that the supplier, warehouse, and every product still exist.'
          : 'Failed to create purchase order.',
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Create Purchase Order</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}

            <Stack direction="row" spacing={2}>
              <TextField
                select
                label="Supplier"
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                required
                autoFocus
                fullWidth
              >
                {suppliers?.map((supplier) => (
                  <MenuItem key={supplier.id} value={String(supplier.id)}>
                    {supplier.company_name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label="Deliver to warehouse"
                value={warehouseId}
                onChange={(e) => setWarehouseId(e.target.value)}
                required
                fullWidth
              >
                {warehouses?.map((warehouse) => (
                  <MenuItem key={warehouse.id} value={String(warehouse.id)}>
                    {warehouse.name}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>

            <Stack direction="row" spacing={2}>
              <TextField
                label="Expected delivery date"
                type="date"
                value={expectedDeliveryDate}
                onChange={(e) => setExpectedDeliveryDate(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
                fullWidth
              />
              <TextField
                label="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                fullWidth
              />
            </Stack>

            <Divider />
            <Typography variant="subtitle1">Line items</Typography>

            {items.map((row, index) => (
              <Stack direction="row" spacing={2} key={index} sx={{ alignItems: 'center' }}>
                <TextField
                  select
                  label="Product"
                  value={row.productId}
                  onChange={(e) => updateItem(index, { productId: e.target.value })}
                  required
                  fullWidth
                  sx={{ flexBasis: '50%' }}
                >
                  {products?.map((product) => (
                    <MenuItem key={product.id} value={String(product.id)}>
                      {product.sku} - {product.name}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Quantity"
                  type="number"
                  value={row.quantityOrdered}
                  onChange={(e) => updateItem(index, { quantityOrdered: e.target.value })}
                  required
                  slotProps={{ htmlInput: { min: 1 } }}
                />
                <TextField
                  label="Unit cost"
                  value={row.unitCost}
                  onChange={(e) => updateItem(index, { unitCost: e.target.value })}
                  required
                />
                <IconButton
                  aria-label="Remove item"
                  onClick={() => removeItem(index)}
                  disabled={items.length === 1}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}

            <Button onClick={addItem} sx={{ alignSelf: 'flex-start' }}>
              Add item
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting || !supplierId || !warehouseId || !hasValidItems}
          >
            {isSubmitting ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
