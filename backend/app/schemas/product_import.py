from pydantic import BaseModel


class ProductImportRowError(BaseModel):
    # 1-indexed against the uploaded file, header line counted as row 1, so a
    # user can jump straight to the offending line in their spreadsheet editor.
    row: int
    messages: list[str]


class ProductImportReport(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    imported_skus: list[str]
    row_errors: list[ProductImportRowError]
