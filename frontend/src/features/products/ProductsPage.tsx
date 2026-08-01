import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SearchIcon from '@mui/icons-material/Search';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router';

import { apiOrigin } from '../../api/client';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { useAuth } from '../auth/useAuth';
import { listCategories } from '../categories/api';
import { listSuppliers } from '../suppliers/api';
import { listWarehouses } from '../warehouses/api';
import {
  createProduct,
  deleteProduct,
  listProducts,
  updateProduct,
  uploadProductImage,
} from './api';
import { ProductFormDialog } from './ProductFormDialog';
import type { Product, ProductInput, StockStatus } from './types';

type DialogState = { mode: 'create' } | { mode: 'edit'; product: Product };

const STOCK_STATUS_LABELS: Record<StockStatus, string> = {
  in_stock: 'In stock',
  low_stock: 'Low stock',
  out_of_stock: 'Out of stock',
};

export function ProductsPage() {
  const { user } = useAuth();
  const canWrite = user?.role === 'admin' || user?.role === 'manager';
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dialogState, setDialogState] = useState<DialogState | null>(null);

  const [searchInput, setSearchInput] = useState('');
  const search = useDebouncedValue(searchInput, 400);
  const [categoryId, setCategoryId] = useState('');
  const [supplierId, setSupplierId] = useState('');
  const [warehouseId, setWarehouseId] = useState('');
  const [stockStatus, setStockStatus] = useState('');
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  const { data: categories } = useQuery({ queryKey: ['categories'], queryFn: listCategories });
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: listSuppliers });
  const { data: warehouses } = useQuery({ queryKey: ['warehouses'], queryFn: listWarehouses });

  const searchParams = {
    q: search || undefined,
    category_id: categoryId ? Number(categoryId) : undefined,
    supplier_id: supplierId ? Number(supplierId) : undefined,
    warehouse_id: warehouseId ? Number(warehouseId) : undefined,
    stock_status: (stockStatus || undefined) as StockStatus | undefined,
    page: page + 1,
    page_size: pageSize,
  };

  const {
    data: result,
    isPending,
    isError,
  } = useQuery({
    queryKey: ['products', searchParams],
    queryFn: () => listProducts(searchParams),
  });

  function resetToFirstPage() {
    setPage(0);
  }

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['products'] });
  const createMutation = useMutation({ mutationFn: createProduct, onSuccess: invalidate });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ProductInput }) => updateProduct(id, input),
    onSuccess: invalidate,
  });
  const deleteMutation = useMutation({ mutationFn: deleteProduct, onSuccess: invalidate });
  const uploadImageMutation = useMutation({
    mutationFn: ({ id, file }: { id: number; file: File }) => uploadProductImage(id, file),
    onSuccess: invalidate,
  });

  async function handleSubmit(input: ProductInput, imageFile: File | null) {
    const product =
      dialogState?.mode === 'edit'
        ? await updateMutation.mutateAsync({ id: dialogState.product.id, input })
        : await createMutation.mutateAsync(input);
    if (imageFile) {
      await uploadImageMutation.mutateAsync({ id: product.id, file: imageFile });
    }
  }

  function handleDelete(product: Product) {
    if (window.confirm(`Delete product "${product.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(product.id);
    }
  }

  const products = result?.items ?? [];

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">Products</Typography>
        {canWrite && (
          <Stack direction="row" spacing={2}>
            <Button
              variant="outlined"
              startIcon={<UploadFileIcon />}
              onClick={() => navigate('/products/import')}
            >
              Import CSV
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setDialogState({ mode: 'create' })}
            >
              Add Product
            </Button>
          </Stack>
        )}
      </Box>

      <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap' }}>
        <TextField
          label="Search"
          placeholder="Name, SKU, barcode, category, or supplier"
          value={searchInput}
          onChange={(e) => {
            setSearchInput(e.target.value);
            resetToFirstPage();
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
          sx={{ minWidth: 280 }}
        />
        <TextField
          select
          label="Category"
          value={categoryId}
          onChange={(e) => {
            setCategoryId(e.target.value);
            resetToFirstPage();
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {categories?.map((category) => (
            <MenuItem key={category.id} value={String(category.id)}>
              {category.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Supplier"
          value={supplierId}
          onChange={(e) => {
            setSupplierId(e.target.value);
            resetToFirstPage();
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {suppliers?.map((supplier) => (
            <MenuItem key={supplier.id} value={String(supplier.id)}>
              {supplier.company_name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Warehouse"
          value={warehouseId}
          onChange={(e) => {
            setWarehouseId(e.target.value);
            resetToFirstPage();
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {warehouses?.map((warehouse) => (
            <MenuItem key={warehouse.id} value={String(warehouse.id)}>
              {warehouse.name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Stock status"
          value={stockStatus}
          onChange={(e) => {
            setStockStatus(e.target.value);
            resetToFirstPage();
          }}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          {(Object.keys(STOCK_STATUS_LABELS) as StockStatus[]).map((status) => (
            <MenuItem key={status} value={status}>
              {STOCK_STATUS_LABELS[status]}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      {isPending && <CircularProgress />}
      {isError && <Alert severity="error">Failed to load products.</Alert>}

      {result && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell />
                <TableCell>SKU</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Supplier</TableCell>
                <TableCell align="right">Selling price</TableCell>
                <TableCell align="right">Quantity</TableCell>
                {canWrite && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {products.length === 0 && (
                <TableRow>
                  <TableCell colSpan={canWrite ? 8 : 7}>
                    <Typography color="text.secondary">
                      No products match your search and filters.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
              {products.map((product) => {
                const isLowStock = product.total_quantity < product.minimum_quantity;
                return (
                  <TableRow key={product.id} hover>
                    <TableCell padding="checkbox">
                      <Avatar
                        variant="rounded"
                        src={product.image_url ? `${apiOrigin}${product.image_url}` : undefined}
                        sx={{ width: 32, height: 32, ml: 1 }}
                      >
                        {product.name.slice(0, 1).toUpperCase()}
                      </Avatar>
                    </TableCell>
                    <TableCell>{product.sku}</TableCell>
                    <TableCell>
                      <RouterLink to={`/products/${product.id}`}>{product.name}</RouterLink>
                    </TableCell>
                    <TableCell>{product.category.name}</TableCell>
                    <TableCell>{product.supplier.company_name}</TableCell>
                    <TableCell align="right">${product.selling_price}</TableCell>
                    <TableCell align="right">
                      <Stack
                        direction="row"
                        spacing={1}
                        sx={{ justifyContent: 'flex-end', alignItems: 'center' }}
                      >
                        <span>{product.total_quantity}</span>
                        {isLowStock && <Chip label="Low stock" color="warning" size="small" />}
                      </Stack>
                    </TableCell>
                    {canWrite && (
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          aria-label={`Edit ${product.name}`}
                          onClick={() => setDialogState({ mode: 'edit', product })}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          aria-label={`Delete ${product.name}`}
                          onClick={() => handleDelete(product)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <TablePagination
            component="div"
            count={result.total}
            page={page}
            onPageChange={(_event, newPage) => setPage(newPage)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(event) => {
              setPageSize(Number(event.target.value));
              resetToFirstPage();
            }}
            rowsPerPageOptions={[10, 20, 50]}
          />
        </TableContainer>
      )}

      {dialogState && (
        <ProductFormDialog
          mode={dialogState.mode}
          initialValue={dialogState.mode === 'edit' ? dialogState.product : undefined}
          onClose={() => setDialogState(null)}
          onSubmit={async (input, imageFile) => {
            await handleSubmit(input, imageFile);
            setDialogState(null);
          }}
        />
      )}
    </Stack>
  );
}
