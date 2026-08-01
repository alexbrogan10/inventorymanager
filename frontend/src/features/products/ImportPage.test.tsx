import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, AxiosHeaders } from 'axios';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';

import * as productsApi from './api';
import { ImportPage } from './ImportPage';
import type { ProductImportReport } from './types';

vi.mock('./api');

const mockedApi = vi.mocked(productsApi);

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeFile(name = 'products.csv'): File {
  return new File(['sku,name\n'], name, { type: 'text/csv' });
}

describe('ImportPage', () => {
  it('disables the upload button until a file is chosen', async () => {
    renderWithProviders(<ImportPage />);

    expect(screen.getByRole('button', { name: /upload/i })).toBeDisabled();
  });

  it('uploads the chosen file and shows the report summary', async () => {
    const report: ProductImportReport = {
      total_rows: 2,
      imported_count: 1,
      failed_count: 1,
      imported_skus: ['WIDGET-100'],
      row_errors: [{ row: 3, messages: ["Missing required value for 'name'"] }],
    };
    mockedApi.importProducts.mockResolvedValue(report);
    const user = userEvent.setup();

    renderWithProviders(<ImportPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeFile());
    await user.click(screen.getByRole('button', { name: /upload/i }));

    expect(await screen.findByText('2 rows')).toBeInTheDocument();
    expect(screen.getByText('1 imported')).toBeInTheDocument();
    expect(screen.getByText('1 failed')).toBeInTheDocument();
    expect(screen.getByText("Missing required value for 'name'")).toBeInTheDocument();
    expect(mockedApi.importProducts.mock.calls[0]?.[0]).toBeInstanceOf(File);
  });

  it('shows the server error message when the upload fails', async () => {
    const error = new AxiosError('Request failed', '422', undefined, undefined, {
      status: 422,
      statusText: 'Unprocessable Content',
      headers: new AxiosHeaders(),
      config: { headers: new AxiosHeaders() },
      data: { detail: 'Missing required column(s): category_name' },
    });
    mockedApi.importProducts.mockRejectedValue(error);
    const user = userEvent.setup();

    renderWithProviders(<ImportPage />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, makeFile());
    await user.click(screen.getByRole('button', { name: /upload/i }));

    expect(
      await screen.findByText('Missing required column(s): category_name'),
    ).toBeInTheDocument();
  });

  it('downloads the template when the Download Template button is clicked', async () => {
    mockedApi.downloadImportTemplate.mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderWithProviders(<ImportPage />);
    await user.click(screen.getByRole('button', { name: /download template/i }));

    expect(mockedApi.downloadImportTemplate).toHaveBeenCalled();
  });
});
