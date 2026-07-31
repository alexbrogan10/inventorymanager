import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { listWarehouses } from '../warehouses/api';
import type { InventoryLevel } from './types';

interface AdjustStockDialogProps {
  currentLevels: InventoryLevel[];
  onClose: () => void;
  onSubmit: (warehouseId: number, quantity: number) => Promise<unknown>;
}

export function AdjustStockDialog({ currentLevels, onClose, onSubmit }: AdjustStockDialogProps) {
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: listWarehouses });
  const [warehouseId, setWarehouseId] = useState('');
  const [quantity, setQuantity] = useState('0');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleWarehouseChange(id: string) {
    setWarehouseId(id);
    const existing = currentLevels.find((level) => String(level.warehouse.id) === id);
    setQuantity(String(existing?.quantity ?? 0));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(Number(warehouseId), Number(quantity));
    } catch {
      setError('Failed to update stock level.');
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Adjust Stock</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              select
              label="Warehouse"
              value={warehouseId}
              onChange={(event) => handleWarehouseChange(event.target.value)}
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
            <TextField
              label="New quantity"
              type="number"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              required
              slotProps={{ htmlInput: { min: 0 } }}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={isSubmitting || !warehouseId}>
            {isSubmitting ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
