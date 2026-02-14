import pytest
from fastapi import status

# Позитивные тесты

def test_admin_get_all_users(admin_client, test_user):
    response = admin_client.get("/api/v1/admin/users")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    emails = [user["email"] for user in data]
    assert test_user.email in emails

def test_admin_replenish_user_balance(session, admin_client, test_user):
    from decimal import Decimal
    amount = 100.0
    initial_balance = test_user.balance
    response = admin_client.post(
        f"/api/v1/admin/transactions/replenish/{test_user.id}",
        json={"amount": amount}
    )
    assert response.status_code == status.HTTP_200_OK
    assert float(response.json()["amount"]) == amount
    # Проверяем, что баланс пользователя обновился в БД
    session.refresh(test_user)
    assert test_user.balance == initial_balance + Decimal(str(amount))

def test_admin_get_all_transactions(admin_client):
    response = admin_client.get("/api/v1/admin/transactions")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_admin_update_user_full(admin_client, test_user):
    update_data = {
        "first_name": "AdminUpdated",
        "balance": 5000.0,
        "role": "admin"
    }
    response = admin_client.patch(f"/api/v1/admin/users/{test_user.id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["first_name"] == "AdminUpdated"
    assert float(data["balance"]) == 5000.0
    assert data["role"] == "admin"

# Негативные тесты

def test_admin_update_user_not_found(admin_client):
    update_data = {"first_name": "Ghost"}
    response = admin_client.patch("/api/v1/admin/users/9999", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_admin_replenish_user_not_found(admin_client):
    response = admin_client.post(
        "/api/v1/admin/transactions/replenish/9999",
        json={"amount": 100}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_admin_approve_transaction_not_found(admin_client):
    response = admin_client.post("/api/v1/admin/transactions/approve/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_admin_reject_transaction_not_found(admin_client):
    response = admin_client.post("/api/v1/admin/transactions/reject/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_admin_update_user_invalid_data(admin_client, test_user):
    update_data = {"balance": -100}
    response = admin_client.patch(f"/api/v1/admin/users/{test_user.id}", json=update_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.parametrize("method,url,payload", [
    ("GET", "/api/v1/admin/users", None),
    ("PATCH", "/api/v1/admin/users/1", {}),
    ("GET", "/api/v1/admin/transactions", None),
    ("POST", "/api/v1/admin/transactions/replenish/1", {"amount": 100}),
    ("POST", "/api/v1/admin/transactions/approve/1", None),
    ("POST", "/api/v1/admin/transactions/reject/1", None),
])
def test_admin_endpoints_unauthorized(client, method, url, payload):
    """Проверка всех админских эндпоинтов без токена (401)."""
    if method == "GET":
        response = client.get(url)
    elif method == "PATCH":
        response = client.patch(url, json=payload)
    else:
        response = client.post(url, json=payload or {})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("method,url,payload", [
    ("GET", "/api/v1/admin/users", None),
    ("PATCH", "/api/v1/admin/users/1", {}),
    ("GET", "/api/v1/admin/transactions", None),
    ("POST", "/api/v1/admin/transactions/replenish/1", {"amount": 100}),
    ("POST", "/api/v1/admin/transactions/approve/1", None),
    ("POST", "/api/v1/admin/transactions/reject/1", None),
])
def test_admin_endpoints_forbidden(auth_client, method, url, payload):
    """Проверка всех админских эндпоинтов под обычным пользователем (403)."""
    if method == "GET":
        response = auth_client.get(url)
    elif method == "PATCH":
        response = auth_client.patch(url, json=payload)
    else:
        response = auth_client.post(url, json=payload or {})
    assert response.status_code == status.HTTP_403_FORBIDDEN

