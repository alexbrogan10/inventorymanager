"""CSV/Excel export helpers shared by every reports endpoint.

CSV uses the stdlib `csv` module - no dependency needed. XLSX needs an
actual spreadsheet writer, so `openpyxl` is added for that alone (see
docs/ARCHITECTURE.md, Milestone 10, for why `pandas` is deliberately not
pulled in here - it's reserved for Milestone 12's forecasting pipeline).
Both `Response`s stream from an in-memory buffer since these reports are
small enough that a temp file on disk would be unnecessary overhead.
"""

import csv
import io
from typing import Any

from fastapi import Response
from openpyxl import Workbook


def _content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"'


def to_csv_response(rows: list[dict[str, Any]], filename: str) -> Response:
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": _content_disposition(filename)},
    )


def to_xlsx_response(rows: list[dict[str, Any]], filename: str) -> Response:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    if rows:
        headers = list(rows[0].keys())
        sheet.append(headers)
        for row in rows:
            sheet.append([row[header] for header in headers])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(filename)},
    )
