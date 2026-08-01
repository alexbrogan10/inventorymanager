import DownloadIcon from '@mui/icons-material/Download';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import {
  Alert,
  Box,
  Button,
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
import { useMutation } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { useRef, useState } from 'react';

import { downloadImportTemplate, importProducts } from './api';
import type { ProductImportReport } from './types';

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail;
  }
  return 'Import failed. Please try again.';
}

export function ImportPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [report, setReport] = useState<ProductImportReport | null>(null);

  const importMutation = useMutation({
    mutationFn: importProducts,
    onSuccess: (result) => setReport(result),
  });

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    setReport(null);
    setSelectedFile(event.target.files?.[0] ?? null);
  }

  function handleUpload() {
    if (selectedFile) {
      importMutation.mutate(selectedFile);
    }
  }

  return (
    <Stack spacing={3}>
      <Typography variant="h4">Import Products</Typography>

      <Typography color="text.secondary">
        Upload a CSV file to create products in bulk. Required columns: <code>sku</code>,{' '}
        <code>name</code>, <code>category_name</code>, <code>supplier_name</code>,{' '}
        <code>purchase_price</code>, <code>selling_price</code>. Optional columns:{' '}
        <code>barcode</code>, <code>description</code>, <code>minimum_quantity</code>,{' '}
        <code>maximum_quantity</code>, <code>unit_type</code>. <code>category_name</code> and{' '}
        <code>supplier_name</code> must match an existing category/supplier exactly.
      </Typography>

      <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={() => void downloadImportTemplate()}
        >
          Download Template
        </Button>

        <input ref={fileInputRef} type="file" accept=".csv" hidden onChange={handleFileChange} />
        <Button
          variant="outlined"
          startIcon={<UploadFileIcon />}
          onClick={() => fileInputRef.current?.click()}
        >
          Choose File
        </Button>
        {selectedFile && <Typography color="text.secondary">{selectedFile.name}</Typography>}

        <Button
          variant="contained"
          disabled={!selectedFile || importMutation.isPending}
          onClick={handleUpload}
        >
          Upload
        </Button>
      </Stack>

      {importMutation.isPending && <CircularProgress />}
      {importMutation.isError && (
        <Alert severity="error">{extractErrorMessage(importMutation.error)}</Alert>
      )}

      {report && (
        <Box>
          <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
            <Chip label={`${report.total_rows} rows`} />
            <Chip label={`${report.imported_count} imported`} color="success" />
            <Chip
              label={`${report.failed_count} failed`}
              color={report.failed_count > 0 ? 'error' : 'default'}
            />
          </Stack>

          {report.row_errors.length > 0 && (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Row</TableCell>
                    <TableCell>Errors</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {report.row_errors.map((rowError) => (
                    <TableRow key={rowError.row} hover>
                      <TableCell>{rowError.row}</TableCell>
                      <TableCell>{rowError.messages.join('; ')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}
    </Stack>
  );
}
