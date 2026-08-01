from collections.abc import Callable

import pytest
import redis
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.api.v1.endpoints.dashboard as dashboard_module
from app.core.config import Settings, get_settings
from app.models.user import UserRole

DASHBOARD_URL = "/api/v1/dashboard/summary"
PRODUCTS_URL = "/api/v1/products"


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch: pytest.MonkeyPatch, redis_client: redis.Redis) -> None:
    """Every test in this file hits the same `dashboard:summary` cache key,
    so without per-test isolation a cached response from one test would leak
    into the next. Points the endpoint's Redis at the dedicated test DB
    (already flushed by the `redis_client` fixture) instead of dev/prod's
    DB 0."""
    test_settings = Settings(redis_url=get_settings().test_redis_url)
    monkeypatch.setattr(dashboard_module, "get_settings", lambda: test_settings)


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
    client: TestClient,
    token: str,
    category_id: int,
    supplier_id: int,
    sku: str,
    purchase_price: str = "5.00",
    selling_price: str = "9.99",
    minimum_quantity: int = 10,
) -> int:
    response = client.post(
        PRODUCTS_URL,
        json={
            "sku": sku,
            "barcode": None,
            "name": f"Product {sku}",
            "description": None,
            "category_id": category_id,
            "supplier_id": supplier_id,
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "minimum_quantity": minimum_quantity,
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


def _create_sale(
    client: TestClient,
    token: str,
    warehouse_id: int,
    product_id: int,
    quantity: int,
    unit_price: str,
) -> int:
    response = client.post(
        "/api/v1/sales",
        json={
            "warehouse_id": warehouse_id,
            "customer_name": "Dashboard Customer",
            "items": [{"product_id": product_id, "quantity": quantity, "unit_price": unit_price}],
        },
        headers=_auth_header(token),
    )
    return int(response.json()["id"])


def _create_purchase_order(
    client: TestClient, token: str, supplier_id: int, warehouse_id: int, product_id: int
) -> dict:
    response = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_id,
            "items": [{"product_id": product_id, "quantity_ordered": 5, "unit_cost": "1.00"}],
        },
        headers=_auth_header(token),
    )
    return dict(response.json())


class Fixture:
    """A category/supplier/warehouse plus two products: one kept in stock,
    one left at zero (before the caller sets up whatever stock scenario the
    test needs)."""

    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="setup-manager@example.com")
        self.category_id = _create_category(client, self.token)
        self.supplier_id = _create_supplier(client, self.token)
        self.warehouse_id = _create_warehouse(client, self.token)
        self.product_a = _create_product(
            client,
            self.token,
            self.category_id,
            self.supplier_id,
            sku="PROD-A",
            minimum_quantity=10,
        )
        self.product_b = _create_product(
            client,
            self.token,
            self.category_id,
            self.supplier_id,
            sku="PROD-B",
            minimum_quantity=10,
        )


class TestAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(DASHBOARD_URL).status_code == 401

    def test_any_authenticated_role_can_read(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(DASHBOARD_URL, headers=_auth_header(token))

        assert response.status_code == 200


class TestEmptyState:
    def test_zero_products_gives_zeroed_summary(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(DASHBOARD_URL, headers=_auth_header(token))

        body = response.json()
        assert body["inventory_value"] == "0"
        assert body["total_products"] == 0
        assert body["low_stock_count"] == 0
        assert body["out_of_stock_count"] == 0
        assert body["pending_purchase_orders_count"] == 0
        assert body["top_selling_products"] == []
        assert body["recent_activity"] == []


class TestInventoryValueAndStockCounts:
    def test_inventory_value_sums_quantity_times_purchase_price(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_a, fixture.warehouse_id, 20)
        _set_level(client, fixture.token, fixture.product_b, fixture.warehouse_id, 10)

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        # Both products created with purchase_price=5.00 -> (20 + 10) * 5.00
        assert response.json()["inventory_value"] == "150.00"

    def test_total_products_counts_every_product(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        assert response.json()["total_products"] == 2

    def test_out_of_stock_and_low_stock_are_counted_separately(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        # product_a: left at zero stock -> out of stock.
        # product_b: some stock, but below its minimum_quantity of 10 -> low stock.
        _set_level(client, fixture.token, fixture.product_b, fixture.warehouse_id, 3)

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        body = response.json()
        assert body["out_of_stock_count"] == 1
        assert body["low_stock_count"] == 1

    def test_stock_above_minimum_is_not_counted_as_low_or_out(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_a, fixture.warehouse_id, 50)
        _set_level(client, fixture.token, fixture.product_b, fixture.warehouse_id, 50)

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        body = response.json()
        assert body["out_of_stock_count"] == 0
        assert body["low_stock_count"] == 0


class TestPendingPurchaseOrders:
    def test_ordered_and_shipped_count_as_pending_received_and_cancelled_do_not(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        ordered = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_a
        )
        shipped = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_a
        )
        client.post(
            f"/api/v1/purchase-orders/{shipped['id']}/ship", headers=_auth_header(fixture.token)
        )
        received = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_a
        )
        client.post(
            f"/api/v1/purchase-orders/{received['id']}/ship", headers=_auth_header(fixture.token)
        )
        client.post(
            f"/api/v1/purchase-orders/{received['id']}/receive", headers=_auth_header(fixture.token)
        )
        cancelled = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_a
        )
        client.post(
            f"/api/v1/purchase-orders/{cancelled['id']}/cancel", headers=_auth_header(fixture.token)
        )
        assert ordered["status"] == "ordered"

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        assert response.json()["pending_purchase_orders_count"] == 2


class TestTopSellingProducts:
    def test_ranks_by_total_quantity_sold_descending(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_a, fixture.warehouse_id, 100)
        _set_level(client, fixture.token, fixture.product_b, fixture.warehouse_id, 100)
        _create_sale(client, fixture.token, fixture.warehouse_id, fixture.product_a, 3, "9.99")
        _create_sale(client, fixture.token, fixture.warehouse_id, fixture.product_b, 8, "5.00")
        # A second sale of product_a should accumulate with the first.
        _create_sale(client, fixture.token, fixture.warehouse_id, fixture.product_a, 10, "9.99")

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        top = response.json()["top_selling_products"]
        assert len(top) == 2
        assert top[0]["id"] == fixture.product_a
        assert top[0]["total_quantity_sold"] == 13
        assert top[1]["id"] == fixture.product_b
        assert top[1]["total_quantity_sold"] == 8

    def test_products_never_sold_are_excluded(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        assert response.json()["top_selling_products"] == []


class TestRecentActivity:
    def test_merges_sales_and_purchase_orders_sorted_by_recency(
        self, client: TestClient, auth_token_for: Callable[..., str], db_session: Session
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.product_a, fixture.warehouse_id, 100)

        sale_id = _create_sale(
            client, fixture.token, fixture.warehouse_id, fixture.product_a, 1, "9.99"
        )
        order = _create_purchase_order(
            client, fixture.token, fixture.supplier_id, fixture.warehouse_id, fixture.product_a
        )

        # Within a single test transaction, Postgres's now() (used for the
        # created_at server default) returns the same transaction-start value
        # for every statement, so the sale and the purchase order above tie on
        # created_at - insertion order alone doesn't produce the distinct
        # timestamps this test needs to assert an ordering. Force them apart
        # directly to make the sort under test deterministic.
        db_session.execute(
            text("UPDATE sales SET created_at = created_at - interval '1 minute' WHERE id = :id"),
            {"id": sale_id},
        )
        db_session.commit()

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        activity = response.json()["recent_activity"]
        assert len(activity) == 2
        # The purchase order was created after the sale, so it should lead.
        assert activity[0] == {
            "type": "purchase_order",
            "id": order["id"],
            "timestamp": order["created_at"],
            "summary": f"Purchase order #{order['id']} from Acme Supply Co. (ordered)",
        }
        assert activity[1]["type"] == "sale"
        assert activity[1]["id"] == sale_id
        assert activity[1]["summary"] == f"Sale #{sale_id} to Dashboard Customer"


class TestCaching:
    def test_second_request_is_served_from_cache(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        first = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))
        assert first.json()["total_products"] == 2

        _create_product(client, fixture.token, fixture.category_id, fixture.supplier_id, "PROD-C")

        second = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        # A third product now exists, but the cached response from the first
        # request is still served within the TTL window.
        assert second.json()["total_products"] == 2

    def test_returns_fresh_data_after_the_cache_entry_is_cleared(
        self,
        client: TestClient,
        auth_token_for: Callable[..., str],
        redis_client: redis.Redis,
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        redis_client.flushdb()
        _create_product(client, fixture.token, fixture.category_id, fixture.supplier_id, "PROD-C")

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        assert response.json()["total_products"] == 3

    def test_serves_fresh_data_when_redis_is_unreachable(
        self,
        client: TestClient,
        auth_token_for: Callable[..., str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Port 1 is not a Redis instance, so every call fails fast (a 1s
        # connect timeout) rather than hanging - the endpoint should still
        # succeed by falling back to computing the summary directly.
        unreachable_settings = Settings(redis_url="redis://localhost:1/0")
        monkeypatch.setattr(dashboard_module, "get_settings", lambda: unreachable_settings)
        fixture = Fixture(client, auth_token_for)

        response = client.get(DASHBOARD_URL, headers=_auth_header(fixture.token))

        assert response.status_code == 200
        assert response.json()["total_products"] == 2
