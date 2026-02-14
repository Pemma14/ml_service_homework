import pytest
from decimal import Decimal

def test_home_page_api(client):
    """Тест главной страницы."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to PsyPharmPredict" in response.json()["message"]

def test_health_check_api(client):
    """Тест эндпоинта /health."""
    # В тестах RabbitMQ может быть недоступен, но моки в conftest.py должны отрабатывать
    response = client.get("/health")
    # Допускаем 200 или 503 в зависимости от того, как отработают моки MQ
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "rabbitmq" in data

def test_balance_replenishment_api(auth_client):
    """Тест API пополнения баланса и проверки текущего баланса."""
    # 1. Проверка начального баланса
    resp = auth_client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert resp.json()["balance"] == "0.00"

    # 2. Пополнение
    amount = 500.50
    resp = auth_client.post("/api/v1/balance/replenish", json={"amount": amount})
    assert resp.status_code == 200

    # 3. Проверка обновленного баланса
    resp = auth_client.get("/api/v1/users/me")
    assert resp.status_code == 200
    assert float(resp.json()["balance"]) == amount

def test_ml_predict_api_validation(auth_client):
    """Тест валидации входных данных для ML запроса."""
    # 1. Отправка некорректных данных (пустой список в data)
    resp = auth_client.post("/api/v1/requests/send_task", json={"data": []})
    assert resp.status_code == 422

    # 2. Отправка некорректных типов
    resp = auth_client.post("/api/v1/requests/send_task", json={"data": [{"age": "not_a_number"}]})
    assert resp.status_code == 422

def test_insufficient_funds_api(auth_client):
    """Тест ошибки при недостаточном балансе через API."""
    # 1. Попытка запроса без денег
    feature_data = {
        "age": 30, "vnn_pp": 1, "clozapine": 0, "cyp2c19_1_2": 0,
        "cyp2c19_1_17": 1, "cyp2c19_17_17": 0, "cyp2d6_1_3": 0
    }
    resp = auth_client.post("/api/v1/requests/send_task", json={"data": [feature_data]})

    # Ожидаем 402 Payment Required
    assert resp.status_code == 402
    assert "Недостаточно кредитов" in resp.json()["message"]

def test_ml_history_api(auth_client):
    """Тест получения истории запросов через API."""
    # 1. Пополняем баланс
    auth_client.post("/api/v1/balance/replenish", json={"amount": 100})

    # 2. Отправляем запрос
    feature_data = {
        "age": 30, "vnn_pp": 1, "clozapine": 0, "cyp2c19_1_2": 0,
        "cyp2c19_1_17": 1, "cyp2c19_17_17": 0, "cyp2d6_1_3": 0
    }
    resp = auth_client.post("/api/v1/requests/send_task", json={"data": [feature_data]})
    assert resp.status_code == 202
    request_id = resp.json()["request_id"]

    # 3. Проверяем историю
    resp = auth_client.get("/api/v1/requests/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) > 0
    assert any(item["id"] == request_id for item in history)

def test_ml_request_details_api(auth_client):
    """Тест получения деталей конкретного запроса."""
    # 1. Пополняем и отправляем
    auth_client.post("/api/v1/balance/replenish", json={"amount": 100})
    feature_data = {
        "age": 30, "vnn_pp": 1, "clozapine": 0, "cyp2c19_1_2": 0,
        "cyp2c19_1_17": 1, "cyp2c19_17_17": 0, "cyp2d6_1_3": 0
    }
    resp = auth_client.post("/api/v1/requests/send_task", json={"data": [feature_data]})
    request_id = resp.json()["request_id"]

    # 2. Получаем детали
    resp = auth_client.get(f"/api/v1/requests/history/{request_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == request_id

def test_ml_predict_rpc_api(auth_client):
    """Тест RPC предсказания (синхронного)."""
    feature_data = {
        "age": 30, "vnn_pp": 1, "clozapine": 0, "cyp2c19_1_2": 0,
        "cyp2c19_1_17": 1, "cyp2c19_17_17": 0, "cyp2d6_1_3": 0
    }
    resp = auth_client.post("/api/v1/requests/send_task_rpc", json={"data": [feature_data]})

    assert resp.status_code == 200
    # В conftest.py мы настроили rpc_client так, чтобы он возвращал [0.5]
    assert resp.json()["prediction"] == [0.5]

def test_ml_request_details_not_found_api(auth_client):
    """Тест получения деталей несуществующего запроса."""
    resp = auth_client.get("/api/v1/requests/history/9999")
    assert resp.status_code == 404

def test_ml_send_result_api(client):
    """Тест эндпоинта для воркеров по сохранению результата (негативный)."""
    result_data = {
        "task_id": "9999",
        "prediction": [0.1],
        "status": "success",
        "worker_id": "test-worker"
    }
    resp = client.post("/api/v1/requests/results", json=result_data)
    # Т.к. ID 9999 не существует, ожидаем 404 (выбрасывается MLRequestNotFoundException)
    assert resp.status_code == 404
