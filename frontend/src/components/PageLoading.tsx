import { Box, CircularProgress } from '@mui/material';

// One consistent loading treatment for every list and detail page - a
// centered spinner with breathing room, instead of each page rendering a
// bare, unstyled CircularProgress that ends up positioned differently
// depending on what surrounds it.
export function PageLoading() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
      <CircularProgress />
    </Box>
  );
}
