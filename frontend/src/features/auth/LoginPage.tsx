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
import { Link as RouterLink, useLocation, useNavigate } from 'react-router';

import { useAuth } from './useAuth';

interface LocationState {
  from?: { pathname: string };
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = (location.state as LocationState | null)?.from?.pathname ?? '/';

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate(redirectTo, { replace: true });
    } catch {
      setError('Incorrect email or password.');
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
            <Typography variant="h5">Sign in</Typography>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              fullWidth
            />
            <Button type="submit" variant="contained" disabled={isSubmitting} fullWidth>
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </Button>
            <Typography variant="body2">
              Don&apos;t have an account?{' '}
              <MuiLink component={RouterLink} to="/register">
                Register
              </MuiLink>
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
