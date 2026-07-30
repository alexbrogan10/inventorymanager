import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { clearStoredToken, getStoredToken, setStoredToken } from '../../api/tokenStorage';
import * as authApi from './api';
import { AuthContext } from './context';
import type { User } from './types';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Starts true and only resolves once the stored token (if any) has been
  // checked against the backend - this is what lets ProtectedRoute tell
  // "not logged in" apart from "haven't checked yet" and avoid a flash
  // redirect to /login on page refresh.
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!getStoredToken()) {
      setIsLoading(false);
      return;
    }
    authApi
      .getCurrentUser()
      .then(setUser)
      .catch(() => clearStoredToken())
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    setStoredToken(access_token);
    setUser(await authApi.getCurrentUser());
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      await authApi.register(email, password, fullName);
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, login, register, logout }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
