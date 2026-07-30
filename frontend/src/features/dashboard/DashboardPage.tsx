import { useQuery } from '@tanstack/react-query';
import { Alert, Card, CardContent, CircularProgress, Stack, Typography } from '@mui/material';

import { getReadiness } from '../../api/health';

export function DashboardPage() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ['health', 'ready'],
    queryFn: getReadiness,
  });

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Dashboard</Typography>

      <Card>
        <CardContent>
          <Typography variant="subtitle2" gutterBottom>
            Backend connectivity
          </Typography>
          {isPending && <CircularProgress size={24} aria-label="Checking backend status" />}
          {isError && <Alert severity="error">{(error as Error).message}</Alert>}
          {data && <Alert severity="success">API reachable — status: {data.status}</Alert>}
        </CardContent>
      </Card>

      <Typography variant="body2" color="text.secondary">
        Inventory value, stock alerts, pending orders, and recent activity will appear here starting
        in Milestone 8.
      </Typography>
    </Stack>
  );
}
