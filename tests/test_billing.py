import pytest
from fastapi import status
from app.config import settings
from tests.helpers import (
    get_user_balance,
    replenish_user_balance,
    DEFAULT_REPLENISH_AMOUNT
)

# Позитивные сценарии

def test_get_balance_success(auth_client, test_user):
    response = auth_client.get("/api/v1/balance/check_balance")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "balance" in data
    assert float(data["balance"]) == float(test_user.balance)


def test_replenish_balance_status(auth_client):
    amount = 500.0
    response = replenish_user_balance(auth_client, amount)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert float(data["amount"]) == amount
    assert data["type"] == "replenish"
    assert "status" in data


def test_balance_increased_after_replenishment(auth_client):
    initial_balance = get_user_balance(auth_client)
    amount = 100.0
    replenish_user_balance(auth_client, amount)
    new_balance = get_user_balance(auth_client)
    assert new_balance == initial_balance + amount

def test_get_transaction_history_success(auth_client):
    replenish_user_balance(auth_client, 100)
    response = auth_client.get("/api/v1/balance/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()
    assert isinstance(history, list)
    assert len(history) >= 1
    # Проверяем структуру первой транзакции
    assert "type" in history[0]
    assert "amount" in history[0]


# Негативные сценарии

@pytest.mark.parametrize("amount", [-100, 0])
def test_replenish_invalid_amount(auth_client, amount):
    """Проверка валидации некорректных сумм пополнения."""
    response = auth_client.post("/api/v1/balance/replenish", json={"amount": amount})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_replenish_amount_too_large(auth_client):
    """Проверка валидации слишком большой суммы пополнения."""
    too_large_amount = float(settings.app.MAX_REPLENISH_AMOUNT) + 1.0
    response = auth_client.post("/api/v1/balance/replenish", json={"amount": too_large_amount})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("method,url,payload", [
    ("GET", "/api/v1/balance/check_balance", None),
    ("POST", "/api/v1/balance/replenish", {"amount": 100}),
    ("GET", "/api/v1/balance/history", None),
])
def test_billing_unauthorized(client, method, url, payload):
    """Проверка всех биллинговых эндпоинтов без авторизации (401)."""
    if method == "GET":
        response = client.get(url)
    else:
        response = client.post(url, json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

