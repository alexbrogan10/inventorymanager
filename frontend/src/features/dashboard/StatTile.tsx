import { Card, CardContent, Stack, Typography } from '@mui/material';
import type { ReactNode } from 'react';

interface StatTileProps {
  label: string;
  value: string;
  icon?: ReactNode;
  color?: 'warning.main' | 'error.main';
}

// Stat tile: label + value, optionally paired with a status icon/color - a
// handful of headline numbers is a KPI row of these, not a chart (see the
// dataviz guidance this dashboard follows).
export function StatTile({ label, value, icon, color }: StatTileProps) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mt: 0.5 }}>
          {icon}
          <Typography variant="h4" component="span" sx={color ? { color } : undefined}>
            {value}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
