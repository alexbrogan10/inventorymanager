import { Alert, Card, CardContent, Grid, Stack, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { isAxiosError } from 'axios';

import { predictProductDemand } from './api';
import { FeatureImportanceChart } from './FeatureImportanceChart';

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Grid size={{ xs: 6, sm: 3 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        {label}
      </Typography>
      <Typography variant="h6">{value}</Typography>
    </Grid>
  );
}

export function ForecastPanel({ productId }: { productId: number }) {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ['forecast', productId],
    queryFn: () => predictProductDemand(productId),
    retry: false,
  });

  const modelNotTrained = isAxiosError(error) && error.response?.status === 409;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Demand Forecast
        </Typography>

        {isPending && <Typography color="text.secondary">Loading forecast…</Typography>}

        {isError && modelNotTrained && (
          <Alert severity="info">
            The forecasting model hasn&apos;t been trained yet. An admin or manager can train it
            from the Dashboard.
          </Alert>
        )}
        {isError && !modelNotTrained && (
          <Alert severity="error">Failed to load the demand forecast.</Alert>
        )}

        {data && (
          <Stack spacing={2}>
            {!data.has_sufficient_history && (
              <Alert severity="info">
                Not enough sales history yet for a model-based forecast - showing a simple reorder
                recommendation instead.
              </Alert>
            )}

            <Grid container spacing={2}>
              <Metric
                label="Predicted daily demand"
                value={data.predicted_daily_demand.toString()}
              />
              <Metric
                label="Stock depletion date"
                value={
                  data.stock_depletion_date
                    ? new Date(data.stock_depletion_date).toLocaleDateString()
                    : '—'
                }
              />
              <Metric label="Recommended reorder qty" value={data.reorder_quantity.toString()} />
              <Metric label="Confidence" value={`${Math.round(data.confidence_score * 100)}%`} />
            </Grid>

            <Typography variant="body2" color="text.secondary">
              Model accuracy (R²):{' '}
              {data.model_accuracy === null
                ? 'not enough data to measure'
                : data.model_accuracy.toFixed(3)}
            </Typography>

            <FeatureImportanceChart featureImportance={data.feature_importance} />
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
