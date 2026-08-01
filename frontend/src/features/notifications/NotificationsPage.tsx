import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { listNotifications, markAllNotificationsRead, markNotificationRead } from './api';
import { NOTIFICATION_TYPE_LABELS, severityToColor } from './severity';

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const searchParams = { page: page + 1, page_size: pageSize, unread_only: unreadOnly };

  const {
    data: result,
    isPending,
    isError,
  } = useQuery({
    queryKey: ['notifications', 'list', searchParams],
    queryFn: () => listNotifications(searchParams),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  }

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidate,
  });

  const markAllReadMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  });

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Notifications</Typography>
        <Button
          variant="outlined"
          disabled={markAllReadMutation.isPending}
          onClick={() => markAllReadMutation.mutate()}
        >
          Mark all read
        </Button>
      </Box>

      <FormControlLabel
        control={
          <Switch
            checked={unreadOnly}
            onChange={(event) => {
              setUnreadOnly(event.target.checked);
              setPage(0);
            }}
          />
        }
        label="Unread only"
      />

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load notifications.</Alert>}

      {result && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Received</TableCell>
                <TableCell align="right">Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {result.items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4}>
                    <Typography color="text.secondary">No notifications.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {result.items.map((notification) => (
                <TableRow
                  key={notification.id}
                  hover
                  sx={{ opacity: notification.is_read ? 0.6 : 1 }}
                >
                  <TableCell>
                    <Chip
                      size="small"
                      label={NOTIFICATION_TYPE_LABELS[notification.type]}
                      color={severityToColor(notification.severity)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      sx={{ fontWeight: notification.is_read ? 400 : 600 }}
                    >
                      {notification.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {notification.message}
                    </Typography>
                  </TableCell>
                  <TableCell>{new Date(notification.created_at).toLocaleString()}</TableCell>
                  <TableCell align="right">
                    {notification.is_read ? (
                      <Typography variant="body2" color="text.secondary">
                        Read
                      </Typography>
                    ) : (
                      <Button size="small" onClick={() => markReadMutation.mutate(notification.id)}>
                        Mark read
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={result.total}
            page={page}
            onPageChange={(_event, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(0);
            }}
            rowsPerPageOptions={[10, 20, 50]}
          />
        </TableContainer>
      )}
    </Stack>
  );
}
