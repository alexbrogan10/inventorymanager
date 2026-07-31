import ErrorIcon from '@mui/icons-material/Error';
import InventoryIcon from '@mui/icons-material/Inventory2';
import PointOfSaleIcon from '@mui/icons-material/PointOfSale';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import {
  Alert,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Stack,
  Typography,
  useTheme,
} from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';
import { useQuery } from '@tanstack/react-query';

import { getDashboardSummary } from './api';
import { StatTile } from './StatTile';

function formatCurrency(value: string): string {
  return `$${Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function DashboardPage() {
  const theme = useTheme();
  const { data, isPending, isError } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: getDashboardSummary,
  });

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Dashboard</Typography>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load dashboard data.</Alert>}

      {data && (
        <>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <StatTile label="Inventory value" value={formatCurrency(data.inventory_value)} />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <StatTile
                label="Total products"
                value={data.total_products.toLocaleString()}
                icon={<InventoryIcon fontSize="small" />}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <StatTile
                label="Low stock"
                value={data.low_stock_count.toLocaleString()}
                icon={<WarningAmberIcon fontSize="small" sx={{ color: 'warning.main' }} />}
                color="warning.main"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <StatTile
                label="Out of stock"
                value={data.out_of_stock_count.toLocaleString()}
                icon={<ErrorIcon fontSize="small" sx={{ color: 'error.main' }} />}
                color="error.main"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <StatTile
                label="Pending purchase orders"
                value={data.pending_purchase_orders_count.toLocaleString()}
                icon={<ShoppingCartIcon fontSize="small" />}
              />
            </Grid>
          </Grid>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 7 }}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    Top Selling Products
                  </Typography>
                  {data.top_selling_products.length === 0 ? (
                    <Typography color="text.secondary">No sales recorded yet.</Typography>
                  ) : (
                    <BarChart
                      dataset={data.top_selling_products.map((product) => ({
                        sku: product.sku,
                        quantity: product.total_quantity_sold,
                      }))}
                      xAxis={[{ dataKey: 'sku', scaleType: 'band' }]}
                      series={[
                        {
                          dataKey: 'quantity',
                          label: 'Units sold',
                          color: theme.palette.primary.main,
                          barLabel: 'value',
                        },
                      ]}
                      height={300}
                      hideLegend
                    />
                  )}
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 5 }}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ mb: 1 }}>
                    Recent Activity
                  </Typography>
                  {data.recent_activity.length === 0 ? (
                    <Typography color="text.secondary">No recent activity.</Typography>
                  ) : (
                    <List dense>
                      {data.recent_activity.map((item) => (
                        <ListItem key={`${item.type}-${item.id}`} disableGutters>
                          <ListItemIcon sx={{ minWidth: 36 }}>
                            {item.type === 'sale' ? (
                              <PointOfSaleIcon fontSize="small" />
                            ) : (
                              <ShoppingCartIcon fontSize="small" />
                            )}
                          </ListItemIcon>
                          <ListItemText
                            primary={item.summary}
                            secondary={new Date(item.timestamp).toLocaleString()}
                          />
                        </ListItem>
                      ))}
                    </List>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
}
