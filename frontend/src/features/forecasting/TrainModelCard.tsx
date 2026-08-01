import ModelTrainingIcon from '@mui/icons-material/ModelTraining';
import { Alert, Button, Card, CardContent, Stack, Typography } from '@mui/material';
import { useMutation } from '@tanstack/react-query';
import { isAxiosError } from 'axios';

import { FeatureImportanceChart } from './FeatureImportanceChart';
import { trainForecastModel } from './api';

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail;
  }
  return 'Training failed. Please try again.';
}

// Training summary only exists for as long as this card stays mounted -
// there's deliberately no separate "get last training status" endpoint,
// since the summary is only ever useful right after the action that
// produced it, not as persisted state to poll later.
export function TrainModelCard() {
  const trainMutation = useMutation({ mutationFn: trainForecastModel });

  return (
    <Card>
      <CardContent>
        <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Demand Forecasting Model</Typography>
          <Button
            variant="contained"
            startIcon={<ModelTrainingIcon />}
            disabled={trainMutation.isPending}
            onClick={() => trainMutation.mutate()}
          >
            {trainMutation.isPending ? 'Training…' : 'Train Model'}
          </Button>
        </Stack>

        {trainMutation.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {extractErrorMessage(trainMutation.error)}
          </Alert>
        )}

        {trainMutation.data && (
          <Stack spacing={2} sx={{ mt: 2 }}>
            <Stack direction="row" spacing={4}>
              <Typography color="text.secondary">
                Trained on {trainMutation.data.training_row_count.toLocaleString()} rows
              </Typography>
              <Typography color="text.secondary">
                Accuracy (R²):{' '}
                {trainMutation.data.accuracy === null
                  ? 'not enough data to measure'
                  : trainMutation.data.accuracy.toFixed(3)}
              </Typography>
              <Typography color="text.secondary">
                Trained at {new Date(trainMutation.data.trained_at).toLocaleString()}
              </Typography>
            </Stack>
            <FeatureImportanceChart featureImportance={trainMutation.data.feature_importance} />
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
