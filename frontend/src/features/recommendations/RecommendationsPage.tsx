import {
  Alert,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';

import { getRecommendations } from './api';
import type { SeasonalPattern } from './types';

const SEASONAL_PATTERN_LABELS: Record<SeasonalPattern, string> = {
  weekend_spike: 'Weekend spike',
  weekday_light: 'Weekday light',
};

export function RecommendationsPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['recommendations'],
    queryFn: getRecommendations,
  });

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Smart Recommendations</Typography>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load recommendations.</Alert>}

      {data && (
        <>
          {!data.model_trained && (
            <Alert severity="info">
              Reorder suggestions need the demand forecasting model to be trained first - train it
              from the Dashboard. The other recommendations below don&apos;t depend on it.
            </Alert>
          )}

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Reorder Suggestions
              </Typography>
              {data.reorder_suggestions.length === 0 ? (
                <Typography color="text.secondary">
                  No products need reordering right now.
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">Current qty</TableCell>
                        <TableCell align="right">Predicted daily demand</TableCell>
                        <TableCell>Depletion date</TableCell>
                        <TableCell align="right">Days until depletion</TableCell>
                        <TableCell align="right">Reorder qty</TableCell>
                        <TableCell align="right">Confidence</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.reorder_suggestions.map((row) => (
                        <TableRow key={row.product_id} hover>
                          <TableCell>{row.sku}</TableCell>
                          <TableCell>{row.name}</TableCell>
                          <TableCell align="right">{row.current_quantity}</TableCell>
                          <TableCell align="right">{row.predicted_daily_demand}</TableCell>
                          <TableCell>
                            {row.stock_depletion_date
                              ? new Date(row.stock_depletion_date).toLocaleDateString()
                              : '—'}
                          </TableCell>
                          <TableCell align="right">{row.days_until_depletion ?? '—'}</TableCell>
                          <TableCell align="right">{row.reorder_quantity}</TableCell>
                          <TableCell align="right">
                            {Math.round(row.confidence_score * 100)}%
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Overstock Warnings
              </Typography>
              {data.overstock_warnings.length === 0 ? (
                <Typography color="text.secondary">No overstock warnings.</Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">Current qty</TableCell>
                        <TableCell align="right">Max qty</TableCell>
                        <TableCell align="right">Days of supply</TableCell>
                        <TableCell>Reasons</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.overstock_warnings.map((row) => (
                        <TableRow key={row.product_id} hover>
                          <TableCell>{row.sku}</TableCell>
                          <TableCell>{row.name}</TableCell>
                          <TableCell align="right">{row.current_quantity}</TableCell>
                          <TableCell align="right">{row.maximum_quantity ?? '—'}</TableCell>
                          <TableCell align="right">
                            {row.days_of_supply !== null ? Math.round(row.days_of_supply) : '—'}
                          </TableCell>
                          <TableCell>{row.reasons.join('; ')}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Slow-Moving Products
              </Typography>
              {data.slow_moving_products.length === 0 ? (
                <Typography color="text.secondary">No slow-moving products.</Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">Current qty</TableCell>
                        <TableCell align="right">Sold in last 60 days</TableCell>
                        <TableCell align="right">Days since last sale</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.slow_moving_products.map((row) => (
                        <TableRow key={row.product_id} hover>
                          <TableCell>{row.sku}</TableCell>
                          <TableCell>{row.name}</TableCell>
                          <TableCell align="right">{row.current_quantity}</TableCell>
                          <TableCell align="right">{row.quantity_sold_last_60_days}</TableCell>
                          <TableCell align="right">
                            {row.days_since_last_sale ?? 'Never sold'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Seasonal Trends
              </Typography>
              {data.seasonal_trends.length === 0 ? (
                <Typography color="text.secondary">No seasonal trends detected.</Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell>Pattern</TableCell>
                        <TableCell align="right">Weekend / weekday ratio</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.seasonal_trends.map((row) => (
                        <TableRow key={row.product_id} hover>
                          <TableCell>{row.sku}</TableCell>
                          <TableCell>{row.name}</TableCell>
                          <TableCell>
                            <Chip label={SEASONAL_PATTERN_LABELS[row.pattern]} size="small" />
                          </TableCell>
                          <TableCell align="right">{row.weekend_to_weekday_ratio}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Stack>
  );
}
