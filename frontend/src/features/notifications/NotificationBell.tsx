import NotificationsIcon from '@mui/icons-material/Notifications';
import {
  Badge,
  Box,
  Button,
  Chip,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Popover,
  Typography,
} from '@mui/material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { listNotifications, markAllNotificationsRead, markNotificationRead } from './api';
import { NOTIFICATION_TYPE_LABELS, severityToColor } from './severity';
import { useNotifications } from './useNotifications';

const DROPDOWN_PAGE_SIZE = 5;

export function NotificationBell() {
  const { unreadCount } = useNotifications();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const open = Boolean(anchorEl);

  const { data } = useQuery({
    queryKey: ['notifications', 'dropdown'],
    queryFn: () => listNotifications({ page: 1, page_size: DROPDOWN_PAGE_SIZE }),
    enabled: open,
  });

  function invalidateNotifications() {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  }

  return (
    <>
      <IconButton
        color="inherit"
        aria-label="Notifications"
        onClick={(event) => setAnchorEl(event.currentTarget)}
      >
        <Badge badgeContent={unreadCount} color="error" max={99}>
          <NotificationsIcon />
        </Badge>
      </IconButton>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Box sx={{ width: 360 }}>
          <List disablePadding>
            {data?.items.length === 0 && (
              <Typography sx={{ p: 2 }} color="text.secondary">
                No notifications.
              </Typography>
            )}
            {data?.items.map((notification) => (
              <ListItemButton
                key={notification.id}
                onClick={async () => {
                  if (!notification.is_read) {
                    await markNotificationRead(notification.id);
                    invalidateNotifications();
                  }
                }}
                sx={{ opacity: notification.is_read ? 0.6 : 1 }}
              >
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        size="small"
                        label={NOTIFICATION_TYPE_LABELS[notification.type]}
                        color={severityToColor(notification.severity)}
                      />
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: notification.is_read ? 400 : 600 }}
                      >
                        {notification.title}
                      </Typography>
                    </Box>
                  }
                  secondary={notification.message}
                />
              </ListItemButton>
            ))}
          </List>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 1 }}>
            <Button
              size="small"
              disabled={unreadCount === 0}
              onClick={async () => {
                await markAllNotificationsRead();
                invalidateNotifications();
              }}
            >
              Mark all read
            </Button>
            <Button
              size="small"
              onClick={() => {
                setAnchorEl(null);
                navigate('/notifications');
              }}
            >
              View all
            </Button>
          </Box>
        </Box>
      </Popover>
    </>
  );
}
