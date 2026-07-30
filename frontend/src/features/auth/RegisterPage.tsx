import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router';

import { useAuth } from './useAuth';

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email, password, fullName);
      navigate('/', { replace: true });
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      setError(
        status === 409 ? 'An account with that email already exists.' : 'Registration failed.',
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent>
          <Stack spacing={2} component="form" onSubmit={handleSubmit}>
            <Typography variant="h5">Create an account</Typography>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              label="Full name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              required
              autoFocus
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
              label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              fullWidth
              helperText="At least 8 characters."
            />
            <TextField
              label="Confirm password"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              fullWidth
            />
            <Button type="submit" variant="contained" disabled={isSubmitting} fullWidth>
              {isSubmitting ? 'Creating account…' : 'Register'}
            </Button>
            <Typography variant="body2">
              Already have an account?{' '}
              <MuiLink component={RouterLink} to="/login">
                Sign in
              </MuiLink>
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
