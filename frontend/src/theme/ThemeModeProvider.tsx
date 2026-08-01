import type { PaletteMode } from '@mui/material';
import { useMediaQuery } from '@mui/material';
import { useCallback, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { ThemeModeContext } from './context';

const STORAGE_KEY = 'theme-mode';

function readStoredMode(): PaletteMode | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' ? stored : null;
}

// Starts by following the OS-level preference (Milestone 1's default) - the
// stored override only exists once the user has actually clicked the
// toggle, so a first-time visitor still sees their system's light/dark
// setting rather than a hardcoded default.
export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const [override, setOverride] = useState<PaletteMode | null>(readStoredMode);

  const mode: PaletteMode = override ?? (prefersDarkMode ? 'dark' : 'light');

  const toggleMode = useCallback(() => {
    setOverride((current) => {
      const resolved = current ?? (prefersDarkMode ? 'dark' : 'light');
      const next: PaletteMode = resolved === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, [prefersDarkMode]);

  const value = useMemo(() => ({ mode, toggleMode }), [mode, toggleMode]);

  return <ThemeModeContext.Provider value={value}>{children}</ThemeModeContext.Provider>;
}
