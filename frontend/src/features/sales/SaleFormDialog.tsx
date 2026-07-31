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
import { listWarehouses } from '../warehouses/api';
import type { SaleInput, SaleItemInput } from './types';

interface SaleFormDialogProps {
  onClose: () => void;
  onSubmit: (input: SaleInput) => Promise<unknown>;
}

interface ItemRow {
  productId: string;
  quantity: string;
  unitPrice: string;
}

const EMPTY_ROW: ItemRow = { productId: '', quantity: '1', unitPrice: '0.00' };

export function SaleFormDialog({ onClose, onSubmit }: SaleFormDialogProps) {
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: listWarehouses });
  const { data: productsResult } = useQuery({
    queryKey: ['products', { page_size: 100 }],
    queryFn: () => listProducts({ page_size: 100 }),
  });
  const products = productsResult?.items;

  const [warehouseId, setWarehouseId] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState<ItemRow[]>([{ ...EMPTY_ROW }]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateItem(index: number, patch: Partial<ItemRow>) {
    setItems((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function handleProductChange(index: number, productId: string) {
    const product = products?.find((p) => String(p.id) === productId);
    updateItem(index, {
      productId,
      unitPrice: product ? product.selling_price : '0.00',
    });
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
      const input: SaleInput = {
        warehouse_id: Number(warehouseId),
        customer_name: customerName,
        customer_email: customerEmail || null,
        customer_phone: customerPhone || null,
        notes: notes || null,
        items: items.map((row): SaleItemInput => ({
          product_id: Number(row.productId),
          quantity: Number(row.quantity),
          unit_price: row.unitPrice,
        })),
      };
      await onSubmit(input);
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 409
          ? 'Not enough stock for one or more items at the selected warehouse.'
          : status === 422
            ? 'Check that the warehouse and every product still exist.'
            : 'Failed to record sale.',
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Record Sale</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}

            <TextField
              select
              label="Warehouse"
              value={warehouseId}
              onChange={(e) => setWarehouseId(e.target.value)}
              required
              autoFocus
              fullWidth
            >
              {warehouses?.map((warehouse) => (
                <MenuItem key={warehouse.id} value={String(warehouse.id)}>
                  {warehouse.name}
                </MenuItem>
              ))}
            </TextField>

            <Stack direction="row" spacing={2}>
              <TextField
                label="Customer name"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                required
                fullWidth
              />
              <TextField
                label="Customer email"
                value={customerEmail}
                onChange={(e) => setCustomerEmail(e.target.value)}
                fullWidth
              />
              <TextField
                label="Customer phone"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                fullWidth
              />
            </Stack>

            <TextField
              label="Notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              fullWidth
            />

            <Divider />
            <Typography variant="subtitle1">Line items</Typography>

            {items.map((row, index) => (
              <Stack direction="row" spacing={2} key={index} sx={{ alignItems: 'center' }}>
                <TextField
                  select
                  label="Product"
                  value={row.productId}
                  onChange={(e) => handleProductChange(index, e.target.value)}
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
                  value={row.quantity}
                  onChange={(e) => updateItem(index, { quantity: e.target.value })}
                  required
                  slotProps={{ htmlInput: { min: 1 } }}
                />
                <TextField
                  label="Unit price"
                  value={row.unitPrice}
                  onChange={(e) => updateItem(index, { unitPrice: e.target.value })}
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
            disabled={isSubmitting || !warehouseId || !customerName || !hasValidItems}
          >
            {isSubmitting ? 'Recording…' : 'Record Sale'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
