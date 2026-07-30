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

import type { Category, CategoryInput } from './types';

interface CategoryFormDialogProps {
  mode: 'create' | 'edit';
  initialValue?: Category;
  onClose: () => void;
  onSubmit: (input: CategoryInput) => Promise<unknown>;
}

export function CategoryFormDialog({
  mode,
  initialValue,
  onClose,
  onSubmit,
}: CategoryFormDialogProps) {
  const [name, setName] = useState(initialValue?.name ?? '');
  const [description, setDescription] = useState(initialValue?.description ?? '');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({ name, description: description || null });
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 409 ? 'A category with that name already exists.' : 'Failed to save category.',
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{mode === 'create' ? 'Add Category' : 'Edit Category'}</DialogTitle>
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
              label="Description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
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
