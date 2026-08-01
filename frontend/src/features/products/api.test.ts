import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '../../api/client';
import {
  createProduct,
  deleteProduct,
  downloadImportTemplate,
  getProduct,
  getProductInventory,
  importProducts,
  listProducts,
  setProductInventoryLevel,
  transferProductInventory,
  updateProduct,
  uploadProductImage,
} from './api';
import type { InventoryLevel, PaginatedProducts, Product, ProductInput } from './types';

vi.mock('../../api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}));

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const CATEGORY = { id: 1, name: 'Electronics', description: null, created_at: '', updated_at: '' };
const SUPPLIER = {
  id: 1,
  company_name: 'Acme Supply Co.',
  contact_person: 'Jane Doe',
  email: 'jane@acme.example',
  phone: '555-0100',
  address: '123 Warehouse Rd',
  lead_time_days: 7,
  notes: null,
  created_at: '',
  updated_at: '',
};

const PRODUCT: Product = {
  id: 1,
  sku: 'WIDGET-001',
  barcode: null,
  name: 'Widget',
  description: null,
  category_id: 1,
  supplier_id: 1,
  category: CATEGORY,
  supplier: SUPPLIER,
  purchase_price: '5.00',
  selling_price: '9.99',
  minimum_quantity: 0,
  maximum_quantity: null,
  unit_type: 'each',
  image_url: null,
  total_quantity: 20,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const PAGE: PaginatedProducts = { items: [PRODUCT], total: 1, page: 1, page_size: 20 };

const INPUT: ProductInput = {
  sku: 'WIDGET-001',
  barcode: null,
  name: 'Widget',
  description: null,
  category_id: 1,
  supplier_id: 1,
  purchase_price: '5.00',
  selling_price: '9.99',
  minimum_quantity: 0,
  maximum_quantity: null,
  unit_type: 'each',
};

describe('products api', () => {
  it('listProducts fetches a paginated page with the given search params', async () => {
    mockedClient.get.mockResolvedValue({ data: PAGE });

    const result = await listProducts({ q: 'widget', page: 2 });

    expect(mockedClient.get).toHaveBeenCalledWith('/products', {
      params: { q: 'widget', page: 2 },
    });
    expect(result).toEqual(PAGE);
  });

  it('getProduct fetches a single product by id', async () => {
    mockedClient.get.mockResolvedValue({ data: PRODUCT });

    const result = await getProduct(1);

    expect(mockedClient.get).toHaveBeenCalledWith('/products/1');
    expect(result).toEqual(PRODUCT);
  });

  it('createProduct posts the input', async () => {
    mockedClient.post.mockResolvedValue({ data: PRODUCT });

    const result = await createProduct(INPUT);

    expect(mockedClient.post).toHaveBeenCalledWith('/products', INPUT);
    expect(result).toEqual(PRODUCT);
  });

  it('updateProduct puts to the id path', async () => {
    mockedClient.put.mockResolvedValue({ data: PRODUCT });

    const result = await updateProduct(1, INPUT);

    expect(mockedClient.put).toHaveBeenCalledWith('/products/1', INPUT);
    expect(result).toEqual(PRODUCT);
  });

  it('deleteProduct deletes the id path', async () => {
    mockedClient.delete.mockResolvedValue({ data: undefined });

    await deleteProduct(1);

    expect(mockedClient.delete).toHaveBeenCalledWith('/products/1');
  });

  it('uploadProductImage posts a FormData containing the file', async () => {
    mockedClient.post.mockResolvedValue({ data: { ...PRODUCT, image_url: '/static/x.png' } });
    const file = new File(['fake-bytes'], 'photo.png', { type: 'image/png' });

    const result = await uploadProductImage(1, file);

    expect(mockedClient.post).toHaveBeenCalledWith('/products/1/image', expect.any(FormData));
    const formData = mockedClient.post.mock.calls[0][1] as FormData;
    expect(formData.get('file')).toBe(file);
    expect(result.image_url).toBe('/static/x.png');
  });

  it('getProductInventory fetches the inventory levels for a product', async () => {
    const levels: InventoryLevel[] = [
      {
        warehouse: {
          id: 1,
          name: 'Main',
          address: '',
          notes: null,
          created_at: '',
          updated_at: '',
        },
        quantity: 10,
      },
    ];
    mockedClient.get.mockResolvedValue({ data: levels });

    const result = await getProductInventory(1);

    expect(mockedClient.get).toHaveBeenCalledWith('/products/1/inventory');
    expect(result).toEqual(levels);
  });

  it('setProductInventoryLevel puts the quantity for a warehouse', async () => {
    mockedClient.put.mockResolvedValue({ data: [] });

    await setProductInventoryLevel(1, 2, 50);

    expect(mockedClient.put).toHaveBeenCalledWith('/products/1/inventory/2', { quantity: 50 });
  });

  it('transferProductInventory posts the transfer input', async () => {
    mockedClient.post.mockResolvedValue({ data: [] });
    const transfer = { from_warehouse_id: 1, to_warehouse_id: 2, quantity: 5 };

    await transferProductInventory(1, transfer);

    expect(mockedClient.post).toHaveBeenCalledWith('/products/1/transfer', transfer);
  });

  it('importProducts posts a FormData containing the CSV file', async () => {
    const report = {
      total_rows: 1,
      imported_count: 1,
      failed_count: 0,
      imported_skus: ['WIDGET-001'],
      row_errors: [],
    };
    mockedClient.post.mockResolvedValue({ data: report });
    const file = new File(['sku,name\n'], 'products.csv', { type: 'text/csv' });

    const result = await importProducts(file);

    expect(mockedClient.post).toHaveBeenCalledWith('/products/import', expect.any(FormData));
    const formData = mockedClient.post.mock.calls[0][1] as FormData;
    expect(formData.get('file')).toBe(file);
    expect(result).toEqual(report);
  });

  it('downloadImportTemplate fetches the blob and triggers a browser download', async () => {
    const blob = new Blob(['sku,name'], { type: 'text/csv' });
    mockedClient.get.mockResolvedValue({ data: blob });
    const createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    await downloadImportTemplate();

    expect(mockedClient.get).toHaveBeenCalledWith('/products/import/template', {
      responseType: 'blob',
    });
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });
});
