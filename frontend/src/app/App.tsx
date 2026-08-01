import { CssBaseline, ThemeProvider } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMemo } from 'react';
import { BrowserRouter } from 'react-router';

import { AuthProvider } from '../features/auth/AuthContext';
import { NotificationsProvider } from '../features/notifications/NotificationsContext';
import { getTheme } from '../theme';
import { ThemeModeProvider } from '../theme/ThemeModeProvider';
import { useThemeMode } from '../theme/useThemeMode';
import { AppRoutes } from './AppRoutes';

const queryClient = new QueryClient();

function ThemedApp() {
  const { mode } = useThemeMode();
  const theme = useMemo(() => getTheme(mode), [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <NotificationsProvider>
              <AppRoutes />
            </NotificationsProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export function App() {
  return (
    <ThemeModeProvider>
      <ThemedApp />
    </ThemeModeProvider>
  );
}
