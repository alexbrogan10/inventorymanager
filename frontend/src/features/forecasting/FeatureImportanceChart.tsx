import { Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { BarChart } from '@mui/x-charts/BarChart';

const FEATURE_LABELS: Record<string, string> = {
  product_id: 'Product',
  day_of_week: 'Day of week',
  day_of_month: 'Day of month',
  month: 'Month',
  lag_1: "Yesterday's demand",
  rolling_mean_7: '7-day average',
};

export function FeatureImportanceChart({
  featureImportance,
}: {
  featureImportance: Record<string, number>;
}) {
  const theme = useTheme();
  const rows = Object.entries(featureImportance)
    .map(([feature, importance]) => ({
      feature: FEATURE_LABELS[feature] ?? feature,
      importance: Math.round(importance * 1000) / 10,
    }))
    .sort((a, b) => b.importance - a.importance);

  if (rows.length === 0) {
    return <Typography color="text.secondary">No feature importance data yet.</Typography>;
  }

  return (
    <BarChart
      dataset={rows}
      xAxis={[{ dataKey: 'feature', scaleType: 'band' }]}
      series={[
        {
          dataKey: 'importance',
          label: 'Importance (%)',
          color: theme.palette.primary.main,
          barLabel: 'value',
        },
      ]}
      height={260}
      hideLegend
    />
  );
}
