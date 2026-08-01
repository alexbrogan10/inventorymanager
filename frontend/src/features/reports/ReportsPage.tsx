import DownloadIcon from '@mui/icons-material/Download';
import {
  Alert,
  Box,
  Button,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { PageLoading } from '../../components/PageLoading';
import { listProducts } from '../products/api';
import {
  downloadReport,
  getInventoryValuation,
  getProductMovement,
  getPurchaseHistory,
  getSalesHistory,
  getSupplierPerformance,
} from './api';
import { InventoryValuationTable } from './InventoryValuationTable';
import { ProductMovementTable } from './ProductMovementTable';
import { PurchaseHistoryTable } from './PurchaseHistoryTable';
import { SalesHistoryTable } from './SalesHistoryTable';
import { SupplierPerformanceTable } from './SupplierPerformanceTable';
import type { DateRangeParams } from './types';

type ReportTab =
  | 'inventory-valuation'
  | 'sales-history'
  | 'purchase-history'
  | 'product-movement'
  | 'supplier-performance';

const REPORT_TABS: { value: ReportTab; label: string }[] = [
  { value: 'inventory-valuation', label: 'Inventory Valuation' },
  { value: 'sales-history', label: 'Sales History' },
  { value: 'purchase-history', label: 'Purchase History' },
  { value: 'product-movement', label: 'Product Movement' },
  { value: 'supplier-performance', label: 'Supplier Performance' },
];

// Every report's date-range filter/export uses this same shape, so it's
// built once here rather than per-report-branch below.
function useDateRangeState() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const params: DateRangeParams = {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  };
  return { startDate, setStartDate, endDate, setEndDate, params };
}

export function ReportsPage() {
  const [tab, setTab] = useState<ReportTab>('inventory-valuation');
  const [productId, setProductId] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const dateRange = useDateRangeState();

  const { data: products } = useQuery({
    queryKey: ['products', 'all-for-reports'],
    queryFn: () => listProducts({ page_size: 100 }),
  });

  const inventoryValuationQuery = useQuery({
    queryKey: ['reports', 'inventory-valuation'],
    queryFn: getInventoryValuation,
    enabled: tab === 'inventory-valuation',
  });
  const salesHistoryQuery = useQuery({
    queryKey: ['reports', 'sales-history', dateRange.params],
    queryFn: () => getSalesHistory(dateRange.params),
    enabled: tab === 'sales-history',
  });
  const purchaseHistoryQuery = useQuery({
    queryKey: ['reports', 'purchase-history', dateRange.params],
    queryFn: () => getPurchaseHistory(dateRange.params),
    enabled: tab === 'purchase-history',
  });
  const productMovementQuery = useQuery({
    queryKey: ['reports', 'product-movement', productId, dateRange.params],
    queryFn: () => getProductMovement(Number(productId), dateRange.params),
    enabled: tab === 'product-movement' && productId !== '',
  });
  const supplierPerformanceQuery = useQuery({
    queryKey: ['reports', 'supplier-performance'],
    queryFn: getSupplierPerformance,
    enabled: tab === 'supplier-performance',
  });

  function exportParams(): Record<string, string | number | undefined> {
    if (tab === 'sales-history' || tab === 'purchase-history') return { ...dateRange.params };
    if (tab === 'product-movement') return { product_id: Number(productId), ...dateRange.params };
    return {};
  }

  async function handleDownload(format: 'csv' | 'xlsx') {
    setIsDownloading(true);
    try {
      await downloadReport(tab, format, `${tab}.${format}`, exportParams());
    } finally {
      setIsDownloading(false);
    }
  }

  const downloadDisabled = isDownloading || (tab === 'product-movement' && !productId);

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Reports</Typography>

      <Tabs
        value={tab}
        onChange={(_event, value: ReportTab) => setTab(value)}
        variant="scrollable"
        scrollButtons="auto"
      >
        {REPORT_TABS.map((reportTab) => (
          <Tab key={reportTab.value} value={reportTab.value} label={reportTab.label} />
        ))}
      </Tabs>

      <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', alignItems: 'center' }}>
        {(tab === 'sales-history' || tab === 'purchase-history' || tab === 'product-movement') && (
          <>
            <TextField
              label="Start date"
              type="date"
              value={dateRange.startDate}
              onChange={(e) => dateRange.setStartDate(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ minWidth: 180 }}
            />
            <TextField
              label="End date"
              type="date"
              value={dateRange.endDate}
              onChange={(e) => dateRange.setEndDate(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ minWidth: 180 }}
            />
          </>
        )}
        {tab === 'product-movement' && (
          <TextField
            select
            label="Product"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            sx={{ minWidth: 240 }}
          >
            <MenuItem value="">Select a product</MenuItem>
            {products?.items.map((product) => (
              <MenuItem key={product.id} value={String(product.id)}>
                {product.sku} - {product.name}
              </MenuItem>
            ))}
          </TextField>
        )}

        <Box sx={{ flexGrow: 1 }} />

        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          disabled={downloadDisabled}
          onClick={() => handleDownload('csv')}
        >
          Download CSV
        </Button>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          disabled={downloadDisabled}
          onClick={() => handleDownload('xlsx')}
        >
          Download Excel
        </Button>
      </Stack>

      {tab === 'inventory-valuation' && (
        <>
          {inventoryValuationQuery.isPending && <PageLoading />}
          {inventoryValuationQuery.isError && (
            <Alert severity="error">Failed to load report.</Alert>
          )}
          {inventoryValuationQuery.data && (
            <InventoryValuationTable report={inventoryValuationQuery.data} />
          )}
        </>
      )}

      {tab === 'sales-history' && (
        <>
          {salesHistoryQuery.isPending && <PageLoading />}
          {salesHistoryQuery.isError && <Alert severity="error">Failed to load report.</Alert>}
          {salesHistoryQuery.data && <SalesHistoryTable report={salesHistoryQuery.data} />}
        </>
      )}

      {tab === 'purchase-history' && (
        <>
          {purchaseHistoryQuery.isPending && <PageLoading />}
          {purchaseHistoryQuery.isError && <Alert severity="error">Failed to load report.</Alert>}
          {purchaseHistoryQuery.data && <PurchaseHistoryTable report={purchaseHistoryQuery.data} />}
        </>
      )}

      {tab === 'product-movement' && (
        <>
          {!productId && (
            <Typography color="text.secondary">
              Select a product above to view its movement history.
            </Typography>
          )}
          {productId !== '' && productMovementQuery.isPending && <PageLoading />}
          {productMovementQuery.isError && <Alert severity="error">Failed to load report.</Alert>}
          {productId !== '' && productMovementQuery.data && (
            <ProductMovementTable report={productMovementQuery.data} />
          )}
        </>
      )}

      {tab === 'supplier-performance' && (
        <>
          {supplierPerformanceQuery.isPending && <PageLoading />}
          {supplierPerformanceQuery.isError && (
            <Alert severity="error">Failed to load report.</Alert>
          )}
          {supplierPerformanceQuery.data && (
            <SupplierPerformanceTable report={supplierPerformanceQuery.data} />
          )}
        </>
      )}
    </Stack>
  );
}
