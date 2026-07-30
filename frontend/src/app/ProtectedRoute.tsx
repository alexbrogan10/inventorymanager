import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

import { useAuth } from '../features/auth/useAuth';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // A full-page loading state is part of Milestone 15's UX polish pass;
    // rendering nothing avoids a flash redirect to /login in the meantime.
    return null;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
