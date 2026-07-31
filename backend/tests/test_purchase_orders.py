from collections.abc import Callable

from fastapi.testclient import TestClient
from httpx2 import Response

from app.models.user import UserRole

PURCHASE_ORDERS_URL = "/api/v1/purchase-orders"
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


class Fixture:
    """Bundles the supplier + warehouse + product every purchase order test
    needs."""

    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="setup-manager@example.com")
        category_id = _create_category(client, self.token)
        self.supplier_id = _create_supplier(client, self.token)
        self.warehouse_id = _create_warehouse(client, self.token)
        self.product_id = _create_product(client, self.token, category_id, self.supplier_id)


def _create_purchase_order(
    client: TestClient,
    token: str,
    supplier_id: int,
    warehouse_id: int,
    product_id: int,
    quantity_ordered: int = 10,
) -> Response:
    return client.post(
        PURCHASE_ORDERS_URL,
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_id,
            "notes": "Restock",
            "items": [
                {
                    "product_id": product_id,
                    "quantity_ordered": quantity_ordered,
                    "unit_cost": "4.25",
                }
            ],
        },
        headers=_auth_header(token),
    )


class TestCreate:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.post(PURCHASE_ORDERS_URL, json={}).status_code == 401

    def test_employee_cannot_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = _create_purchase_order(
            client, employee_token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        )

        assert response.status_code == 403

    def test_manager_can_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        )

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "ordered"
        assert body["supplier"]["id"] == fixture.supplier_id
        assert body["warehouse"]["id"] == fixture.warehouse_id
        assert len(body["items"]) == 1
        assert body["items"][0]["product"]["id"] == fixture.product_id
        assert body["items"][0]["quantity_ordered"] == 10
        assert body["items"][0]["quantity_received"] == 0
        assert body["items"][0]["unit_cost"] == "4.25"

    def test_invalid_supplier_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_purchase_order(
            client, fixture.token, 999, fixture.warehouse_id, fixture.product_id
        )

        assert response.status_code == 422

    def test_invalid_warehouse_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, 999, fixture.product_id
        )

        assert response.status_code == 422

    def test_invalid_product_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, 999
        )

        assert response.status_code == 422

    def test_empty_items_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.post(
            PURCHASE_ORDERS_URL,
            json={
                "supplier_id": fixture.supplier_id,
                "warehouse_id": fixture.warehouse_id,
                "items": [],
            },
            headers=_auth_header(fixture.token),
        )

        assert response.status_code == 422


class TestReadAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(PURCHASE_ORDERS_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(PURCHASE_ORDERS_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.json() == []

    def test_get_missing_purchase_order_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{PURCHASE_ORDERS_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404


class TestShip:
    def test_employee_cannot_ship(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(employee_token)
        )

        assert response.status_code == 403

    def test_manager_can_ship(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json()["status"] == "shipped"

    def test_shipping_twice_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 409

    def test_missing_purchase_order_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(f"{PURCHASE_ORDERS_URL}/999/ship", headers=_auth_header(token))

        assert response.status_code == 404


class TestReceive:
    def test_employee_cannot_receive(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(employee_token)
        )

        assert response.status_code == 403

    def test_receiving_before_shipping_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 409

    def test_manager_can_receive_and_inventory_increments(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client,
            fixture.token,
            fixture.supplier_id,
            fixture.warehouse_id,
            fixture.product_id,
            quantity_ordered=15,
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "received"
        assert body["items"][0]["quantity_received"] == 15

        product_response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert product_response.json()["total_quantity"] == 15

    def test_receiving_adds_to_existing_stock_rather_than_overwriting(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        client.put(
            f"{PRODUCTS_URL}/{fixture.product_id}/inventory/{fixture.warehouse_id}",
            json={"quantity": 20},
            headers=_auth_header(fixture.token),
        )
        order = _create_purchase_order(
            client,
            fixture.token,
            fixture.supplier_id,
            fixture.warehouse_id,
            fixture.product_id,
            quantity_ordered=15,
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )

        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(fixture.token)
        )

        product_response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert product_response.json()["total_quantity"] == 35

    def test_receiving_twice_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(fixture.token)
        )

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 409

    def test_missing_purchase_order_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(f"{PURCHASE_ORDERS_URL}/999/receive", headers=_auth_header(token))

        assert response.status_code == 404


class TestCancel:
    def test_employee_cannot_cancel(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/cancel", headers=_auth_header(employee_token)
        )

        assert response.status_code == 403

    def test_manager_can_cancel_an_ordered_purchase_order(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/cancel", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_manager_can_cancel_a_shipped_purchase_order(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/cancel", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cannot_cancel_a_received_purchase_order(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/ship", headers=_auth_header(fixture.token)
        )
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/receive", headers=_auth_header(fixture.token)
        )

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/cancel", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 409

    def test_cannot_cancel_an_already_cancelled_purchase_order(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_id
        ).json()
        client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/cancel", headers=_auth_header(fixture.token)
        )

        response = client.post(
            f"{PURCHASE_ORDERS_URL}/{order['id']}/cancel", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 409

    def test_missing_purchase_order_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(f"{PURCHASE_ORDERS_URL}/999/cancel", headers=_auth_header(token))

        assert response.status_code == 404
