import { createTheme, type PaletteMode, type ThemeOptions } from '@mui/material/styles';

// Shared across both palettes so switching mode never changes spacing/type -
// only color. Defined once here (Milestone 1) even though the light/dark
// toggle UI itself is built in a later milestone: retrofitting theme-aware
// styling after components already assume one palette is expensive, starting
// with it is not.
const baseOptions: ThemeOptions = {
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: ['Inter', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'].join(','),
  },
};

const lightTheme = createTheme({
  ...baseOptions,
  palette: {
    mode: 'light',
    primary: { main: '#1565c0' },
    secondary: { main: '#7b1fa2' },
    background: { default: '#f4f6f8' },
  },
});

const darkTheme = createTheme({
  ...baseOptions,
  palette: {
    mode: 'dark',
    primary: { main: '#90caf9' },
    secondary: { main: '#ce93d8' },
  },
});

export function getTheme(mode: PaletteMode) {
  return mode === 'dark' ? darkTheme : lightTheme;
}
