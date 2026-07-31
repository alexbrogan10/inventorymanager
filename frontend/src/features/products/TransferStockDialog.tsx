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

interface TransferStockDialogProps {
  currentLevels: InventoryLevel[];
  onClose: () => void;
  onSubmit: (fromWarehouseId: number, toWarehouseId: number, quantity: number) => Promise<unknown>;
}

export function TransferStockDialog({
  currentLevels,
  onClose,
  onSubmit,
}: TransferStockDialogProps) {
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: listWarehouses });
  const sourceOptions = currentLevels.filter((level) => level.quantity > 0);

  const [fromWarehouseId, setFromWarehouseId] = useState('');
  const [toWarehouseId, setToWarehouseId] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const destinationOptions = warehouses?.filter(
    (warehouse) => String(warehouse.id) !== fromWarehouseId,
  );

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(Number(fromWarehouseId), Number(toWarehouseId), Number(quantity));
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 409 ? 'Not enough stock at the source warehouse.' : 'Failed to transfer stock.',
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Transfer Stock</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              select
              label="From warehouse"
              value={fromWarehouseId}
              onChange={(event) => {
                setFromWarehouseId(event.target.value);
                if (event.target.value === toWarehouseId) {
                  setToWarehouseId('');
                }
              }}
              required
              autoFocus
              fullWidth
              helperText={sourceOptions.length === 0 ? 'No warehouses have stock to transfer.' : ''}
            >
              {sourceOptions.map((level) => (
                <MenuItem key={level.warehouse.id} value={String(level.warehouse.id)}>
                  {level.warehouse.name} ({level.quantity} available)
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="To warehouse"
              value={toWarehouseId}
              onChange={(event) => setToWarehouseId(event.target.value)}
              required
              fullWidth
              disabled={!fromWarehouseId}
            >
              {destinationOptions?.map((warehouse) => (
                <MenuItem key={warehouse.id} value={String(warehouse.id)}>
                  {warehouse.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Quantity"
              type="number"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              required
              slotProps={{ htmlInput: { min: 1 } }}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting || !fromWarehouseId || !toWarehouseId}
          >
            {isSubmitting ? 'Transferring…' : 'Transfer'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
