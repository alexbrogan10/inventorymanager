from collections.abc import Callable

from fastapi.testclient import TestClient
from httpx2 import Response

from app.models.user import UserRole

SALES_URL = "/api/v1/sales"
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


def _create_warehouse(client: TestClient, token: str, name: str = "Main Warehouse") -> int:
    response = client.post(
        "/api/v1/warehouses",
        json={"name": name, "address": "Somewhere", "notes": None},
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _create_product(
    client: TestClient, token: str, category_id: int, supplier_id: int, sku: str = "WIDGET-001"
) -> int:
    response = client.post(
        PRODUCTS_URL,
        json={
            "sku": sku,
            "barcode": None,
            "name": "Widget",
            "description": None,
            "category_id": category_id,
            "supplier_id": supplier_id,
            "purchase_price": "5.00",
            "selling_price": "9.99",
            "minimum_quantity": 0,
            "maximum_quantity": None,
            "unit_type": "each",
        },
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _set_level(
    client: TestClient, token: str, product_id: int, warehouse_id: int, quantity: int
) -> None:
    client.put(
        f"{PRODUCTS_URL}/{product_id}/inventory/{warehouse_id}",
        json={"quantity": quantity},
        headers=_auth_header(token),
    )


class Fixture:
    """Bundles the warehouse + product every sale test needs, with 20 units
    of stock already in place."""

    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="setup-manager@example.com")
        category_id = _create_category(client, self.token)
        supplier_id = _create_supplier(client, self.token)
        self.warehouse_id = _create_warehouse(client, self.token)
        self.product_id = _create_product(client, self.token, category_id, supplier_id)
        _set_level(client, self.token, self.product_id, self.warehouse_id, 20)


def _create_sale(
    client: TestClient,
    token: str,
    warehouse_id: int,
    items: list[dict[str, object]],
    customer_name: str = "Jane Customer",
) -> Response:
    return client.post(
        SALES_URL,
        json={
            "warehouse_id": warehouse_id,
            "customer_name": customer_name,
            "customer_email": "jane.customer@example.com",
            "customer_phone": "555-0001",
            "notes": "Test sale",
            "items": items,
        },
        headers=_auth_header(token),
    )


class TestCreate:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.post(SALES_URL, json={}).status_code == 401

    def test_employee_cannot_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = _create_sale(
            client,
            employee_token,
            fixture.warehouse_id,
            [{"product_id": fixture.product_id, "quantity": 1, "unit_price": "9.99"}],
        )

        assert response.status_code == 403

    def test_manager_can_create_and_inventory_is_deducted(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [{"product_id": fixture.product_id, "quantity": 5, "unit_price": "9.99"}],
        )

        assert response.status_code == 201
        body = response.json()
        assert body["customer_name"] == "Jane Customer"
        assert body["warehouse"]["id"] == fixture.warehouse_id
        assert len(body["items"]) == 1
        assert body["items"][0]["product"]["id"] == fixture.product_id
        assert body["items"][0]["quantity"] == 5
        assert body["items"][0]["unit_price"] == "9.99"

        product_response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert product_response.json()["total_quantity"] == 15

    def test_repeated_product_on_one_sale_aggregates_before_deducting(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [
                {"product_id": fixture.product_id, "quantity": 8, "unit_price": "9.99"},
                {"product_id": fixture.product_id, "quantity": 8, "unit_price": "9.99"},
            ],
        )

        assert response.status_code == 201
        product_response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert product_response.json()["total_quantity"] == 4

    def test_insufficient_stock_is_rejected_and_nothing_is_deducted(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [{"product_id": fixture.product_id, "quantity": 100, "unit_price": "9.99"}],
        )

        assert response.status_code == 409
        product_response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert product_response.json()["total_quantity"] == 20

    def test_insufficient_stock_across_repeated_product_lines_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        # Neither line alone exceeds the 20 in stock, but together they do -
        # this only fails if quantities are aggregated per product before
        # the availability check runs.
        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [
                {"product_id": fixture.product_id, "quantity": 15, "unit_price": "9.99"},
                {"product_id": fixture.product_id, "quantity": 15, "unit_price": "9.99"},
            ],
        )

        assert response.status_code == 409
        product_response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert product_response.json()["total_quantity"] == 20

    def test_invalid_warehouse_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            999,
            [{"product_id": fixture.product_id, "quantity": 1, "unit_price": "9.99"}],
        )

        assert response.status_code == 422

    def test_invalid_product_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [{"product_id": 999, "quantity": 1, "unit_price": "9.99"}],
        )

        assert response.status_code == 422

    def test_empty_items_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.post(
            SALES_URL,
            json={
                "warehouse_id": fixture.warehouse_id,
                "customer_name": "Jane Customer",
                "items": [],
            },
            headers=_auth_header(fixture.token),
        )

        assert response.status_code == 422

    def test_zero_quantity_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [{"product_id": fixture.product_id, "quantity": 0, "unit_price": "9.99"}],
        )

        assert response.status_code == 422

    def test_blank_customer_name_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [{"product_id": fixture.product_id, "quantity": 1, "unit_price": "9.99"}],
            customer_name="",
        )

        assert response.status_code == 422


class TestReadAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(SALES_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(SALES_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}

    def test_list_is_paginated_newest_first(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        sale_ids = [
            _create_sale(
                client,
                fixture.token,
                fixture.warehouse_id,
                [{"product_id": fixture.product_id, "quantity": 1, "unit_price": "9.99"}],
            ).json()["id"]
            for _ in range(3)
        ]

        response = client.get(
            SALES_URL,
            params={"page": 1, "page_size": 2},
            headers=_auth_header(fixture.token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert [item["id"] for item in body["items"]] == list(reversed(sale_ids))[:2]

    def test_get_missing_sale_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{SALES_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404

    def test_employee_can_read_a_sale_created_by_a_manager(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        created = _create_sale(
            client,
            fixture.token,
            fixture.warehouse_id,
            [{"product_id": fixture.product_id, "quantity": 1, "unit_price": "9.99"}],
        ).json()
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.get(f"{SALES_URL}/{created['id']}", headers=_auth_header(employee_token))

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
