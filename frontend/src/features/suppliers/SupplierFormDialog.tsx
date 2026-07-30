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

import type { Supplier, SupplierInput } from './types';

interface SupplierFormDialogProps {
  mode: 'create' | 'edit';
  initialValue?: Supplier;
  onClose: () => void;
  onSubmit: (input: SupplierInput) => Promise<unknown>;
}

export function SupplierFormDialog({
  mode,
  initialValue,
  onClose,
  onSubmit,
}: SupplierFormDialogProps) {
  const [companyName, setCompanyName] = useState(initialValue?.company_name ?? '');
  const [contactPerson, setContactPerson] = useState(initialValue?.contact_person ?? '');
  const [email, setEmail] = useState(initialValue?.email ?? '');
  const [phone, setPhone] = useState(initialValue?.phone ?? '');
  const [address, setAddress] = useState(initialValue?.address ?? '');
  const [leadTimeDays, setLeadTimeDays] = useState(String(initialValue?.lead_time_days ?? '7'));
  const [notes, setNotes] = useState(initialValue?.notes ?? '');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        company_name: companyName,
        contact_person: contactPerson,
        email,
        phone,
        address,
        lead_time_days: Number(leadTimeDays),
        notes: notes || null,
      });
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 409
          ? 'A supplier with that company name already exists.'
          : 'Failed to save supplier.',
      );
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{mode === 'create' ? 'Add Supplier' : 'Edit Supplier'}</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              label="Company name"
              value={companyName}
              onChange={(event) => setCompanyName(event.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Contact person"
              value={contactPerson}
              onChange={(event) => setContactPerson(event.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              fullWidth
            />
            <TextField
              label="Phone"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
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
              label="Lead time (days)"
              type="number"
              value={leadTimeDays}
              onChange={(event) => setLeadTimeDays(event.target.value)}
              required
              slotProps={{ htmlInput: { min: 0 } }}
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
