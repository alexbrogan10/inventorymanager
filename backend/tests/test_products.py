from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

import pytest
from fastapi.testclient import TestClient

import app.core.storage as storage_module
from app.core.config import Settings
from app.models.user import UserRole

PRODUCTS_URL = "/api/v1/products"


class ProductRefs(TypedDict):
    """Precise key set (unlike a plain dict[str, int]) so mypy knows `**refs`
    can never supply `_product_payload`'s `sku: str` parameter."""

    category_id: int
    supplier_id: int


@pytest.fixture(autouse=True)
def _isolate_uploads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Product image uploads write to a per-test temp directory instead of
    the real backend/uploads/ folder, so the test suite never leaves files
    behind and tests can't interfere with each other's uploads."""
    fake_settings = Settings(upload_dir=str(tmp_path))
    monkeypatch.setattr(storage_module, "get_settings", lambda: fake_settings)


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


def _product_payload(sku: str = "WIDGET-001", **overrides: object) -> dict:
    payload = {
        "sku": sku,
        "barcode": "012345678905",
        "name": "Widget",
        "description": "A fine widget",
        "purchase_price": "5.00",
        "selling_price": "9.99",
        "current_quantity": 50,
        "minimum_quantity": 10,
        "maximum_quantity": 200,
        "warehouse_location": "Aisle 3",
        "unit_type": "each",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def refs(client: TestClient, auth_token_for: Callable[..., str]) -> ProductRefs:
    """A category_id/supplier_id pair every product test needs to reference."""
    token = auth_token_for(UserRole.MANAGER, email="setup-manager@example.com")
    return {
        "category_id": _create_category(client, token),
        "supplier_id": _create_supplier(client, token),
    }


def _create_product(
    client: TestClient,
    token: str,
    refs: ProductRefs,
    sku: str = "WIDGET-001",
    **overrides: object,
) -> dict:
    response = client.post(
        PRODUCTS_URL,
        json=_product_payload(sku, **refs, **overrides),
        headers=_auth_header(token),
    )
    return response.json()


class TestReadAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(PRODUCTS_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(PRODUCTS_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.json() == []

    def test_get_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{PRODUCTS_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404


class TestCreate:
    def test_employee_cannot_create(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.post(
            PRODUCTS_URL, json=_product_payload(**refs), headers=_auth_header(token)
        )

        assert response.status_code == 403

    def test_manager_can_create_with_nested_category_and_supplier(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            PRODUCTS_URL, json=_product_payload(**refs), headers=_auth_header(token)
        )

        assert response.status_code == 201
        body = response.json()
        assert body["sku"] == "WIDGET-001"
        assert body["category"]["id"] == refs["category_id"]
        assert body["supplier"]["id"] == refs["supplier_id"]
        assert body["selling_price"] == "9.99"
        assert body["image_url"] is None

    def test_duplicate_sku_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_product(client, token, refs)

        response = client.post(
            PRODUCTS_URL,
            json=_product_payload(sku="WIDGET-001", barcode="999999999999", **refs),
            headers=_auth_header(token),
        )

        assert response.status_code == 409

    def test_duplicate_barcode_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_product(client, token, refs, sku="WIDGET-001")

        response = client.post(
            PRODUCTS_URL,
            json=_product_payload(sku="WIDGET-002", **refs),
            headers=_auth_header(token),
        )

        assert response.status_code == 409

    def test_invalid_category_id_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            PRODUCTS_URL,
            json=_product_payload(category_id=999, supplier_id=refs["supplier_id"]),
            headers=_auth_header(token),
        )

        assert response.status_code == 422

    def test_invalid_supplier_id_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            PRODUCTS_URL,
            json=_product_payload(category_id=refs["category_id"], supplier_id=999),
            headers=_auth_header(token),
        )

        assert response.status_code == 422

    def test_maximum_below_minimum_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            PRODUCTS_URL,
            json=_product_payload(minimum_quantity=100, maximum_quantity=10, **refs),
            headers=_auth_header(token),
        )

        assert response.status_code == 422


class TestUpdate:
    def test_manager_can_update(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        product = _create_product(client, token, refs)

        response = client.put(
            f"{PRODUCTS_URL}/{product['id']}",
            json=_product_payload(selling_price="12.50", **refs),
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.json()["selling_price"] == "12.50"

    def test_employee_cannot_update(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        product = _create_product(client, manager_token, refs)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.put(
            f"{PRODUCTS_URL}/{product['id']}",
            json=_product_payload(**refs),
            headers=_auth_header(employee_token),
        )

        assert response.status_code == 403

    def test_update_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.put(
            f"{PRODUCTS_URL}/999", json=_product_payload(**refs), headers=_auth_header(token)
        )

        assert response.status_code == 404

    def test_renaming_sku_to_another_products_sku_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_product(client, token, refs, sku="WIDGET-001", barcode="111111111111")
        other = _create_product(client, token, refs, sku="WIDGET-002", barcode="222222222222")

        response = client.put(
            f"{PRODUCTS_URL}/{other['id']}",
            json=_product_payload(sku="WIDGET-001", barcode="222222222222", **refs),
            headers=_auth_header(token),
        )

        assert response.status_code == 409

    def test_changing_barcode_to_another_products_barcode_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_product(client, token, refs, sku="WIDGET-001", barcode="111111111111")
        other = _create_product(client, token, refs, sku="WIDGET-002", barcode="222222222222")

        response = client.put(
            f"{PRODUCTS_URL}/{other['id']}",
            json=_product_payload(sku="WIDGET-002", barcode="111111111111", **refs),
            headers=_auth_header(token),
        )

        assert response.status_code == 409


class TestDelete:
    def test_manager_can_delete(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        product = _create_product(client, token, refs)

        delete_response = client.delete(
            f"{PRODUCTS_URL}/{product['id']}", headers=_auth_header(token)
        )
        get_response = client.get(f"{PRODUCTS_URL}/{product['id']}", headers=_auth_header(token))

        assert delete_response.status_code == 204
        assert get_response.status_code == 404

    def test_delete_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.delete(f"{PRODUCTS_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404


class TestImageUpload:
    def test_manager_can_upload_an_image(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        product = _create_product(client, token, refs)

        response = client.post(
            f"{PRODUCTS_URL}/{product['id']}/image",
            files={"file": ("photo.png", b"\x89PNG fake bytes", "image/png")},
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.json()["image_url"] == f"/static/products/{product['id']}.png"

    def test_employee_cannot_upload_an_image(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        product = _create_product(client, manager_token, refs)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.post(
            f"{PRODUCTS_URL}/{product['id']}/image",
            files={"file": ("photo.png", b"fake", "image/png")},
            headers=_auth_header(employee_token),
        )

        assert response.status_code == 403

    def test_rejects_a_disallowed_content_type(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        product = _create_product(client, token, refs)

        response = client.post(
            f"{PRODUCTS_URL}/{product['id']}/image",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
            headers=_auth_header(token),
        )

        assert response.status_code == 422

    def test_rejects_a_file_over_the_size_limit(
        self, client: TestClient, auth_token_for: Callable[..., str], refs: ProductRefs
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        product = _create_product(client, token, refs)
        oversized = b"0" * (5 * 1024 * 1024 + 1)

        response = client.post(
            f"{PRODUCTS_URL}/{product['id']}/image",
            files={"file": ("photo.png", oversized, "image/png")},
            headers=_auth_header(token),
        )

        assert response.status_code == 422

    def test_upload_for_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(
            f"{PRODUCTS_URL}/999/image",
            files={"file": ("photo.png", b"fake", "image/png")},
            headers=_auth_header(token),
        )

        assert response.status_code == 404
