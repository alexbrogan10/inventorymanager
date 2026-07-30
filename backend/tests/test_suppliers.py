from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.user import UserRole

SUPPLIERS_URL = "/api/v1/suppliers"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _supplier_payload(company_name: str = "Acme Supply Co.") -> dict:
    return {
        "company_name": company_name,
        "contact_person": "Jane Doe",
        "email": "jane@acmesupply.example",
        "phone": "+1-555-0100",
        "address": "123 Warehouse Rd",
        "lead_time_days": 7,
        "notes": "Preferred supplier for electronics.",
    }


def _create_supplier(client: TestClient, token: str, company_name: str = "Acme Supply Co.") -> dict:
    response = client.post(
        SUPPLIERS_URL, json=_supplier_payload(company_name), headers=_auth_header(token)
    )
    return response.json()


class TestReadAccess:
    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get(SUPPLIERS_URL).status_code == 401

    def test_any_authenticated_role_can_list(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(SUPPLIERS_URL, headers=_auth_header(token))

        assert response.status_code == 200
        assert response.json() == []

    def test_get_missing_supplier_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.get(f"{SUPPLIERS_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404


class TestWriteAccess:
    def test_employee_cannot_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.EMPLOYEE)

        response = client.post(SUPPLIERS_URL, json=_supplier_payload(), headers=_auth_header(token))

        assert response.status_code == 403

    def test_manager_can_create(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.post(SUPPLIERS_URL, json=_supplier_payload(), headers=_auth_header(token))

        assert response.status_code == 201
        body = response.json()
        assert body["company_name"] == "Acme Supply Co."
        assert body["lead_time_days"] == 7

    def test_duplicate_company_name_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_supplier(client, token)

        response = client.post(SUPPLIERS_URL, json=_supplier_payload(), headers=_auth_header(token))

        assert response.status_code == 409

    def test_invalid_email_is_rejected(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        payload = _supplier_payload() | {"email": "not-an-email"}

        response = client.post(SUPPLIERS_URL, json=payload, headers=_auth_header(token))

        assert response.status_code == 422


class TestUpdate:
    def test_manager_can_update(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        supplier = _create_supplier(client, token)

        updated_payload = _supplier_payload() | {"lead_time_days": 14}
        response = client.put(
            f"{SUPPLIERS_URL}/{supplier['id']}", json=updated_payload, headers=_auth_header(token)
        )

        assert response.status_code == 200
        assert response.json()["lead_time_days"] == 14

    def test_employee_cannot_update(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        supplier = _create_supplier(client, manager_token)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.put(
            f"{SUPPLIERS_URL}/{supplier['id']}",
            json=_supplier_payload(),
            headers=_auth_header(employee_token),
        )

        assert response.status_code == 403

    def test_update_missing_supplier_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.put(
            f"{SUPPLIERS_URL}/999", json=_supplier_payload(), headers=_auth_header(token)
        )

        assert response.status_code == 404

    def test_renaming_to_another_suppliers_name_conflicts(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        _create_supplier(client, token, company_name="Acme Supply Co.")
        other = _create_supplier(client, token, company_name="Globex Supply")

        response = client.put(
            f"{SUPPLIERS_URL}/{other['id']}",
            json=_supplier_payload(company_name="Acme Supply Co."),
            headers=_auth_header(token),
        )

        assert response.status_code == 409


class TestDelete:
    def test_manager_can_delete(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)
        supplier = _create_supplier(client, token)

        delete_response = client.delete(
            f"{SUPPLIERS_URL}/{supplier['id']}", headers=_auth_header(token)
        )
        get_response = client.get(f"{SUPPLIERS_URL}/{supplier['id']}", headers=_auth_header(token))

        assert delete_response.status_code == 204
        assert get_response.status_code == 404

    def test_employee_cannot_delete(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        manager_token = auth_token_for(UserRole.MANAGER, email="manager@example.com")
        supplier = _create_supplier(client, manager_token)
        employee_token = auth_token_for(UserRole.EMPLOYEE, email="employee@example.com")

        response = client.delete(
            f"{SUPPLIERS_URL}/{supplier['id']}", headers=_auth_header(employee_token)
        )

        assert response.status_code == 403

    def test_delete_missing_supplier_is_404(
        self, client: TestClient, auth_token_for: Callable[..., str]
    ) -> None:
        token = auth_token_for(UserRole.MANAGER)

        response = client.delete(f"{SUPPLIERS_URL}/999", headers=_auth_header(token))

        assert response.status_code == 404
