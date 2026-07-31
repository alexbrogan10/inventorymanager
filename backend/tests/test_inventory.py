from collections.abc import Callable

from fastapi.testclient import TestClient
from httpx2 import Response

from app.models.user import UserRole

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


def _create_warehouse(client: TestClient, token: str, name: str) -> int:
    response = client.post(
        "/api/v1/warehouses",
        json={"name": name, "address": "Somewhere", "notes": None},
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _create_product(client: TestClient, token: str, category_id: int, supplier_id: int) -> int:
    response = client.post(
        PRODUCTS_URL,
        json={
            "sku": "WIDGET-001",
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
    """Bundles the product + two warehouses every inventory test needs."""

    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="setup-manager@example.com")
        category_id = _create_category(client, self.token)
        supplier_id = _create_supplier(client, self.token)
        self.product_id = _create_product(client, self.token, category_id, supplier_id)
        self.warehouse_a = _create_warehouse(client, self.token, "Warehouse A")
        self.warehouse_b = _create_warehouse(client, self.token, "Warehouse B")


def _set_level(
    client: TestClient, token: str, product_id: int, warehouse_id: int, quantity: int
) -> Response:
    return client.put(
        f"{PRODUCTS_URL}/{product_id}/inventory/{warehouse_id}",
        json={"quantity": quantity},
        headers=_auth_header(token),
    )


class TestGetInventory:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(f"{PRODUCTS_URL}/1/inventory").status_code == 401

    def test_new_product_has_no_levels(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}/inventory", headers=_auth_header(fixture.token)
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{PRODUCTS_URL}/999/inventory", headers=_auth_header(token))

        assert response.status_code == 404


class TestSetLevel:
    def test_employee_cannot_set_level(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = _set_level(client, employee_token, fixture.product_id, fixture.warehouse_a, 50)

        assert response.status_code == 403

    def test_manager_can_set_level(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        assert response.status_code == 200
        levels = response.json()
        assert len(levels) == 1
        assert levels[0]["warehouse"]["id"] == fixture.warehouse_a
        assert levels[0]["quantity"] == 50

    def test_setting_level_again_overwrites_rather_than_adds(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        response = _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 30)

        assert response.json()[0]["quantity"] == 30

    def test_negative_quantity_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, -1)

        assert response.status_code == 422

    def test_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _set_level(client, fixture.token, 999, fixture.warehouse_a, 10)

        assert response.status_code == 404

    def test_missing_warehouse_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = _set_level(client, fixture.token, fixture.product_id, 999, 10)

        assert response.status_code == 404

    def test_total_quantity_reflects_the_sum_across_warehouses(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 30)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_b, 20)

        response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )

        assert response.json()["total_quantity"] == 50


class TestTransfer:
    def _transfer(
        self, client: TestClient, token: str, product_id: int, **payload: object
    ) -> Response:
        return client.post(
            f"{PRODUCTS_URL}/{product_id}/transfer", json=payload, headers=_auth_header(token)
        )

    def test_employee_cannot_transfer(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = self._transfer(
            client,
            employee_token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_b,
            quantity=10,
        )

        assert response.status_code == 403

    def test_manager_can_transfer_stock(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        response = self._transfer(
            client,
            fixture.token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_b,
            quantity=20,
        )

        assert response.status_code == 200
        levels = {level["warehouse"]["id"]: level["quantity"] for level in response.json()}
        assert levels[fixture.warehouse_a] == 30
        assert levels[fixture.warehouse_b] == 20

    def test_transfer_preserves_total_quantity(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        self._transfer(
            client,
            fixture.token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_b,
            quantity=20,
        )

        response = client.get(
            f"{PRODUCTS_URL}/{fixture.product_id}", headers=_auth_header(fixture.token)
        )
        assert response.json()["total_quantity"] == 50

    def test_insufficient_stock_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 5)

        response = self._transfer(
            client,
            fixture.token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_b,
            quantity=10,
        )

        assert response.status_code == 409

    def test_transferring_to_the_same_warehouse_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        response = self._transfer(
            client,
            fixture.token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_a,
            quantity=10,
        )

        assert response.status_code == 422

    def test_zero_quantity_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        response = self._transfer(
            client,
            fixture.token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_b,
            quantity=0,
        )

        assert response.status_code == 422

    def test_missing_product_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = self._transfer(
            client,
            fixture.token,
            999,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=fixture.warehouse_b,
            quantity=10,
        )

        assert response.status_code == 404

    def test_missing_destination_warehouse_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_id, fixture.warehouse_a, 50)

        response = self._transfer(
            client,
            fixture.token,
            fixture.product_id,
            from_warehouse_id=fixture.warehouse_a,
            to_warehouse_id=999,
            quantity=10,
        )

        assert response.status_code == 404
