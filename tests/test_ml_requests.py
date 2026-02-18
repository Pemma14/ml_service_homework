import pytest
from fastapi import status
from tests.helpers import (
    get_valid_feature_data,
    replenish_user_balance,
    get_user_balance,
    create_ml_request,
    create_ml_request_rpc,
    TEST_MODEL_COST,
    DEFAULT_REPLENISH_AMOUNT
)

# Позитивные сценарии

def test_send_task_async_success(funded_client):
    feature_data = get_valid_feature_data()
    response = create_ml_request(funded_client, feature_data)
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "request_id" in data
    assert data["status"] == "pending"


def test_send_task_rpc_success(funded_client):
    feature_data = get_valid_feature_data()
    response = create_ml_request_rpc(funded_client, feature_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["prediction"] == "выраженные побочные эффекты будут с вероятностью 0.15"

def test_send_result_success(client, funded_client):
    feature_data = get_valid_feature_data()
    resp_send = create_ml_request(funded_client, feature_data)
    request_id = resp_send.json()["request_id"]

    result_data = {
        "task_id": str(request_id),
        "prediction": "выраженные побочные эффекты будут с вероятностью 0.15",
        "status": "success",
        "worker_id": "test-worker-01"
    }
    response = client.post("/api/v1/requests/post_result", json=result_data)
    assert response.status_code == status.HTTP_200_OK
    resp_details = funded_client.get(f"/api/v1/requests/history/{request_id}")
    assert resp_details.json()["status"] == "success"
    assert resp_details.json()["prediction"] == "выраженные побочные эффекты будут с вероятностью 0.15"

def test_get_ml_history_empty(auth_client):
    """Получение пустой истории для нового пользователя."""
    response = auth_client.get("/api/v1/requests/history")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_get_history_with_data(funded_client):
    """Получение истории с данными после создания запроса."""
    feature_data = get_valid_feature_data()
    resp_send = create_ml_request(funded_client, feature_data)
    request_id = resp_send.json()["request_id"]
    response = funded_client.get("/api/v1/requests/history")
    assert response.status_code == status.HTTP_200_OK
    history = response.json()
    assert len(history) >= 1
    assert any(item["id"] == request_id for item in history)


def test_get_request_details_success(funded_client):
    feature_data = get_valid_feature_data()
    resp_send = create_ml_request(funded_client, feature_data)
    request_id = resp_send.json()["request_id"]
    response = funded_client.get(f"/api/v1/requests/history/{request_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == request_id

# Негативные сценарии

def test_send_task_insufficient_funds(auth_client):
    feature_data = get_valid_feature_data()
    response = create_ml_request(auth_client, feature_data)
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    data = response.json()
    assert "message" in data
    assert "Недостаточно кредитов" in data["message"]


def test_send_task_rpc_insufficient_funds(auth_client):
    feature_data = get_valid_feature_data()
    response = create_ml_request_rpc(auth_client, feature_data)
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    data = response.json()
    assert "message" in data
    assert "Недостаточно кредитов" in data["message"]

def test_send_task_validation_error(auth_client):
    response = auth_client.post("/api/v1/requests/send_task", json={"data": []})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response = auth_client.post("/api/v1/requests/send_task", json={"data": [{"age": "old"}]})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_send_result_not_found(client):
    result_data = {
        "task_id": "9999",
        "prediction": [0.1],
        "status": "success",
        "worker_id": "test-worker"
    }
    response = client.post("/api/v1/requests/post_result", json=result_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_request_details_not_found(auth_client):
    response = auth_client.get("/api/v1/requests/history/9999")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_send_result_fail_refund(client, funded_client):
    """При ошибке воркера средства должны вернуться на баланс пользователя."""
    initial_balance = get_user_balance(funded_client)
    feature_data = get_valid_feature_data()
    resp_send = create_ml_request(funded_client, feature_data)
    request_id = resp_send.json()["request_id"]

    # Проверяем, что средства списались
    balance_after_request = get_user_balance(funded_client)
    assert balance_after_request == initial_balance - float(TEST_MODEL_COST)

    # Act - имитируем ошибку от воркера
    result_data = {
        "task_id": str(request_id),
        "prediction": None,
        "status": "fail",
        "error": "Model computation error",
        "worker_id": "test-worker-01"
    }
    response = client.post("/api/v1/requests/post_result", json=result_data)
    assert response.status_code == status.HTTP_200_OK
    balance_after_refund = get_user_balance(funded_client)
    assert balance_after_refund == initial_balance

@pytest.mark.parametrize("method,url,json_data", [
    ("POST", "/api/v1/requests/send_task", {"data": []}),
    ("POST", "/api/v1/requests/predict", {"data": []}),
    ("GET", "/api/v1/requests/history", None),
    ("GET", "/api/v1/requests/history/1", None),
])
def test_ml_endpoints_unauthorized(client, method, url, json_data):
    """Проверка всех ML эндпоинтов без авторизации (401)."""
    if method == "POST":
        response = client.post(url, json=json_data)
    else:
        response = client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED




