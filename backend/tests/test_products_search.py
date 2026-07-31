from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import UserRole

PRODUCTS_URL = "/api/v1/products"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_category(client: TestClient, token: str, name: str) -> int:
    response = client.post("/api/v1/categories", json={"name": name}, headers=_auth_header(token))
    return int(response.json()["id"])


def _create_supplier(client: TestClient, token: str, company_name: str) -> int:
    slug = "".join(ch for ch in company_name.lower() if ch.isalnum())
    response = client.post(
        "/api/v1/suppliers",
        json={
            "company_name": company_name,
            "contact_person": "Jane Doe",
            "email": f"{slug}@example.com",
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


def _create_product(
    client: TestClient,
    token: str,
    *,
    sku: str,
    name: str,
    barcode: str | None,
    category_id: int,
    supplier_id: int,
    minimum_quantity: int = 10,
) -> int:
    response = client.post(
        PRODUCTS_URL,
        json={
            "sku": sku,
            "barcode": barcode,
            "name": name,
            "description": None,
            "category_id": category_id,
            "supplier_id": supplier_id,
            "purchase_price": "5.00",
            "selling_price": "9.99",
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


class Fixture:
    """Two categories, two suppliers, two warehouses, and four products with
    distinct names/SKUs/barcodes so search and filters have something real to
    tell apart."""

    def __init__(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        self.token = auth_token_for(UserRole.MANAGER, email="setup-manager@example.com")
        self.electronics = _create_category(client, self.token, "Electronics")
        self.furniture = _create_category(client, self.token, "Furniture")
        self.acme = _create_supplier(client, self.token, "Acme Supply Co.")
        self.globex = _create_supplier(client, self.token, "Globex Corp.")
        self.warehouse_a = _create_warehouse(client, self.token, "Warehouse A")
        self.warehouse_b = _create_warehouse(client, self.token, "Warehouse B")

        self.widget = _create_product(
            client,
            self.token,
            sku="WIDGET-001",
            name="Blue Widget",
            barcode="1111111111",
            category_id=self.electronics,
            supplier_id=self.acme,
            minimum_quantity=10,
        )
        self.gadget = _create_product(
            client,
            self.token,
            sku="GADGET-002",
            name="Red Gadget",
            barcode="2222222222",
            category_id=self.electronics,
            supplier_id=self.globex,
            minimum_quantity=10,
        )
        self.chair = _create_product(
            client,
            self.token,
            sku="CHAIR-003",
            name="Office Chair",
            barcode=None,
            category_id=self.furniture,
            supplier_id=self.acme,
            minimum_quantity=5,
        )
        self.desk = _create_product(
            client,
            self.token,
            sku="DESK-004",
            name="Standing Desk",
            barcode=None,
            category_id=self.furniture,
            supplier_id=self.globex,
            minimum_quantity=5,
        )


def _search(client: TestClient, token: str, **params: str | int) -> dict:
    response = client.get(PRODUCTS_URL, params=params, headers=_auth_header(token))
    assert response.status_code == 200, response.text
    return dict(response.json())


class TestSearch:
    def test_matches_product_name(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="Widget")

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget

    def test_matches_sku(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="GADGET-002")

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.gadget

    def test_matches_barcode(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="1111111111")

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget

    def test_matches_category_name(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="Furniture")

        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {fixture.chair, fixture.desk}

    def test_matches_supplier_name(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="Globex")

        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {fixture.gadget, fixture.desk}

    def test_is_case_insensitive(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="widget")

        assert body["total"] == 1

    def test_no_match_returns_empty(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="nonexistent-thing")

        assert body["total"] == 0
        assert body["items"] == []


class TestFilters:
    def test_category_id_filter(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, category_id=fixture.furniture)

        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {fixture.chair, fixture.desk}

    def test_supplier_id_filter(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, supplier_id=fixture.acme)

        assert body["total"] == 2
        assert {item["id"] for item in body["items"]} == {fixture.widget, fixture.chair}

    def test_warehouse_id_filter_only_matches_products_with_stock_there(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.widget, fixture.warehouse_a, 20)
        _set_level(client, fixture.token, fixture.gadget, fixture.warehouse_b, 20)

        body = _search(client, fixture.token, warehouse_id=fixture.warehouse_a)

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget

    def test_combining_search_and_category_filter(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, q="Acme", category_id=fixture.electronics)

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget


class TestStockStatus:
    def test_out_of_stock(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.widget, fixture.warehouse_a, 0)
        _set_level(client, fixture.token, fixture.gadget, fixture.warehouse_a, 20)

        body = _search(client, fixture.token, stock_status="out_of_stock")

        # widget has an explicit zero-quantity row; chair/desk were never
        # stocked at all - both count as out of stock.
        assert {item["id"] for item in body["items"]} == {
            fixture.widget,
            fixture.chair,
            fixture.desk,
        }

    def test_low_stock(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.widget, fixture.warehouse_a, 3)  # min is 10

        body = _search(client, fixture.token, stock_status="low_stock")

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget

    def test_in_stock(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.widget, fixture.warehouse_a, 50)  # min is 10

        body = _search(client, fixture.token, stock_status="in_stock")

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget

    def test_invalid_stock_status_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.get(
            PRODUCTS_URL, params={"stock_status": "bogus"}, headers=_auth_header(fixture.token)
        )

        assert response.status_code == 422


class TestQuantityRange:
    def test_min_quantity(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.widget, fixture.warehouse_a, 50)
        _set_level(client, fixture.token, fixture.gadget, fixture.warehouse_a, 5)

        body = _search(client, fixture.token, min_quantity=10)

        assert body["total"] == 1
        assert body["items"][0]["id"] == fixture.widget

    def test_max_quantity(self, client: TestClient, auth_token_for: Callable[..., str]) -> None:
        fixture = Fixture(client, auth_token_for)
        _set_level(client, fixture.token, fixture.widget, fixture.warehouse_a, 50)
        _set_level(client, fixture.token, fixture.gadget, fixture.warehouse_a, 5)

        body = _search(client, fixture.token, max_quantity=10)

        # chair/desk were never stocked (0), so both qualify alongside gadget.
        assert {item["id"] for item in body["items"]} == {
            fixture.gadget,
            fixture.chair,
            fixture.desk,
        }


class TestPagination:
    def test_default_page_size_and_total_count(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token)

        assert body["total"] == 4
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["items"]) == 4

    def test_page_size_limits_items_but_not_total(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, page_size=2)

        assert body["total"] == 4
        assert len(body["items"]) == 2

    def test_second_page_returns_remaining_items_without_overlap(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        page1 = _search(client, fixture.token, page=1, page_size=2)
        page2 = _search(client, fixture.token, page=2, page_size=2)

        ids_page1 = {item["id"] for item in page1["items"]}
        ids_page2 = {item["id"] for item in page2["items"]}
        assert len(ids_page1) == 2
        assert len(ids_page2) == 2
        assert ids_page1.isdisjoint(ids_page2)
        assert ids_page1 | ids_page2 == {
            fixture.widget,
            fixture.gadget,
            fixture.chair,
            fixture.desk,
        }

    def test_page_past_the_end_returns_no_items(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        body = _search(client, fixture.token, page=99, page_size=20)

        assert body["total"] == 4
        assert body["items"] == []

    def test_page_size_over_max_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        fixture = Fixture(client, auth_token_for)

        response = client.get(
            PRODUCTS_URL, params={"page_size": 500}, headers=_auth_header(fixture.token)
        )

        assert response.status_code == 422
