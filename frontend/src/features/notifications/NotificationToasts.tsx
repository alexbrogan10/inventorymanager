import { Alert, Snackbar } from '@mui/material';

import { severityToColor } from './severity';
import { useNotifications } from './useNotifications';

// MUI's Snackbar has no built-in stacking, so only the head of the queue is
// ever rendered - dismissing it (by timeout or by hand) reveals the next one
// on the following render, giving a sequential "one toast at a time" queue.
export function NotificationToasts() {
  const { toastQueue, dismissToast } = useNotifications();
  const current = toastQueue[0] ?? null;

  return (
    <Snackbar
      key={current?.id}
      open={current !== null}
      autoHideDuration={6000}
      onClose={() => current && dismissToast(current.id)}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
    >
      {current ? (
        <Alert
          onClose={() => dismissToast(current.id)}
          severity={severityToColor(current.severity)}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {current.title}
        </Alert>
      ) : undefined}
    </Snackbar>
  );
}
