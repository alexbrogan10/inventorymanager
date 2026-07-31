import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
} from '@mui/material';
import { useState } from 'react';
import type { FormEvent } from 'react';

import type { Warehouse, WarehouseInput } from './types';

interface WarehouseFormDialogProps {
  mode: 'create' | 'edit';
  initialValue?: Warehouse;
  onClose: () => void;
  onSubmit: (input: WarehouseInput) => Promise<unknown>;
}

export function WarehouseFormDialog({
  mode,
  initialValue,
  onClose,
  onSubmit,
}: WarehouseFormDialogProps) {
  const [name, setName] = useState(initialValue?.name ?? '');
  const [address, setAddress] = useState(initialValue?.address ?? '');
  const [notes, setNotes] = useState(initialValue?.notes ?? '');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ name, address, notes: notes || null });
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 409 ? 'A warehouse with that name already exists.' : 'Failed to save warehouse.',
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{mode === 'create' ? 'Add Warehouse' : 'Edit Warehouse'}</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              label="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Address"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              required
              multiline
              minRows={2}
              fullWidth
            />
            <TextField
              label="Notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              multiline
              minRows={2}
              fullWidth
            />
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
