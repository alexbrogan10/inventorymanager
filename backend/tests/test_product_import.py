import csv
import io
from collections.abc import Callable

from fastapi.testclient import TestClient
from httpx2 import Response

from app.models.user import UserRole

IMPORT_URL = "/api/v1/products/import"
TEMPLATE_URL = "/api/v1/products/import/template"
PRODUCTS_URL = "/api/v1/products"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_category(client: TestClient, token: str, name: str = "Electronics") -> int:
    response = client.post("/api/v1/categories", json={"name": name}, headers=_auth_header(token))
    return int(response.json()["id"])


def _create_supplier(client: TestClient, token: str, company_name: str = "Acme Supply Co.") -> int:
    response = client.post(
        "/api/v1/suppliers",
        json={
            "company_name": company_name,
            "contact_person": "Jane Doe",
            "email": "jane@acme.example",
            "phone": "555-0100",
            "address": "123 Warehouse Rd",
            "lead_time_days": 7,
            "notes": None,
        },
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _upload_csv(
    client: TestClient, token: str, content: str, filename: str = "products.csv"
) -> Response:
    return client.post(
        IMPORT_URL,
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
        headers=_auth_header(token),
    )


class Fixture:
    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="import-manager@example.com")
        self.category_name = "Electronics"
        self.supplier_name = "Acme Supply Co."
        _create_category(client, self.token, self.category_name)
        _create_supplier(client, self.token, self.supplier_name)

    def row(self, **overrides: str) -> dict[str, str]:
        base = {
            "sku": "WIDGET-100",
            "name": "Widget",
            "category_name": self.category_name,
            "supplier_name": self.supplier_name,
            "purchase_price": "4.50",
            "selling_price": "9.99",
            "barcode": "",
            "description": "",
            "minimum_quantity": "10",
            "maximum_quantity": "",
            "unit_type": "each",
        }
        base.update(overrides)
        return base


def _to_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


class TestAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post(IMPORT_URL, files={"file": ("p.csv", b"sku\n", "text/csv")})
        assert response.status_code == 401

    def test_employee_cannot_import(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)
        header = "sku,name,category_name,supplier_name,purchase_price,selling_price\n"

        response = _upload_csv(client, token, header)

        assert response.status_code == 403

    def test_manager_can_import(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv([fixture.row()])

        response = _upload_csv(client, fixture.token, content)

        assert response.status_code == 200


class TestTemplate:
    def test_template_download_has_expected_header(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER, email="template-manager@example.com")

        response = client.get(TEMPLATE_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        rows = list(csv.DictReader(io.StringIO(response.text)))
        assert len(rows) == 1
        assert set(rows[0].keys()) >= {
            "sku",
            "name",
            "category_name",
            "supplier_name",
            "purchase_price",
            "selling_price",
        }


class TestSuccessfulImport:
    def test_imports_valid_rows_and_creates_products(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv(
            [fixture.row(sku="WIDGET-100"), fixture.row(sku="WIDGET-200", name="Gadget")]
        )

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["total_rows"] == 2
        assert body["imported_count"] == 2
        assert body["failed_count"] == 0
        assert body["row_errors"] == []
        assert set(body["imported_skus"]) == {"WIDGET-100", "WIDGET-200"}

        products = client.get(PRODUCTS_URL, headers=_auth_header(fixture.token)).json()
        skus = {item["sku"] for item in products["items"]}
        assert {"WIDGET-100", "WIDGET-200"}.issubset(skus)

    def test_optional_columns_can_be_omitted_entirely(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "sku",
                "name",
                "category_name",
                "supplier_name",
                "purchase_price",
                "selling_price",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "sku": "WIDGET-300",
                "name": "Minimal Widget",
                "category_name": fixture.category_name,
                "supplier_name": fixture.supplier_name,
                "purchase_price": "1.00",
                "selling_price": "2.00",
            }
        )

        response = _upload_csv(client, fixture.token, buffer.getvalue())

        body = response.json()
        assert body["imported_count"] == 1
        assert body["row_errors"] == []


class TestValidationErrors:
    def test_missing_required_column_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = "sku,name\nWIDGET-1,Widget\n"

        response = _upload_csv(client, fixture.token, content)

        assert response.status_code == 422
        assert "category_name" in response.json()["detail"]

    def test_missing_required_value_is_reported_per_row(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv([fixture.row(name="")])

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["imported_count"] == 0
        assert body["failed_count"] == 1
        assert body["row_errors"][0]["row"] == 2
        assert any("name" in message for message in body["row_errors"][0]["messages"])

    def test_invalid_price_is_reported(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv([fixture.row(purchase_price="not-a-number")])

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["failed_count"] == 1
        assert any("purchase_price" in message for message in body["row_errors"][0]["messages"])

    def test_invalid_quantity_is_reported(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv([fixture.row(minimum_quantity="not-an-int")])

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["failed_count"] == 1
        assert any("minimum_quantity" in message for message in body["row_errors"][0]["messages"])

    def test_unknown_category_is_reported(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv([fixture.row(category_name="Nonexistent Category")])

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["failed_count"] == 1
        assert any("category" in message.lower() for message in body["row_errors"][0]["messages"])

    def test_unknown_supplier_is_reported(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv([fixture.row(supplier_name="Nonexistent Supplier")])

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["failed_count"] == 1
        assert any("supplier" in message.lower() for message in body["row_errors"][0]["messages"])

    def test_duplicate_sku_within_file_fails_second_occurrence(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv(
            [fixture.row(sku="WIDGET-DUP"), fixture.row(sku="WIDGET-DUP", name="Second")]
        )

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["imported_count"] == 1
        assert body["failed_count"] == 1
        assert body["row_errors"][0]["row"] == 3
        assert any("already exists" in message for message in body["row_errors"][0]["messages"])

    def test_duplicate_sku_against_existing_product_fails(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _upload_csv(client, fixture.token, _to_csv([fixture.row(sku="WIDGET-EXISTING")]))

        response = _upload_csv(client, fixture.token, _to_csv([fixture.row(sku="WIDGET-EXISTING")]))

        body = response.json()
        assert body["imported_count"] == 0
        assert body["failed_count"] == 1

    def test_valid_and_invalid_rows_in_the_same_file_both_get_processed(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        content = _to_csv(
            [
                fixture.row(sku="WIDGET-GOOD-1"),
                fixture.row(sku="", name="Missing SKU"),
                fixture.row(sku="WIDGET-GOOD-2"),
            ]
        )

        response = _upload_csv(client, fixture.token, content)

        body = response.json()
        assert body["total_rows"] == 3
        assert body["imported_count"] == 2
        assert body["failed_count"] == 1
        assert body["row_errors"][0]["row"] == 3
        assert set(body["imported_skus"]) == {"WIDGET-GOOD-1", "WIDGET-GOOD-2"}


class TestFileValidation:
    def test_non_csv_filename_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.post(
            IMPORT_URL,
            files={"file": ("products.txt", b"sku,name\n", "text/plain")},
            headers=_auth_header(fixture.token),
        )

        assert response.status_code == 422

    def test_oversized_file_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        oversized = b"a" * (3 * 1024 * 1024)

        response = client.post(
            IMPORT_URL,
            files={"file": ("products.csv", oversized, "text/csv")},
            headers=_auth_header(fixture.token),
        )

        assert response.status_code == 422
