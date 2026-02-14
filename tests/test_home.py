import pytest
from fastapi import status


def test_home_page_api(client):
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert "Welcome to PsyPharmPredict" in data["message"]


def test_health_check_api_success(client):
    """Проверка health check возвращает корректный ответ."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # В тестовом окружении RabbitMQ может быть недоступен, проверяем только структуру
    assert "status" in data
    assert "database" in data
    assert "rabbitmq" in data


def test_health_check_response_structure(client):
    """Проверка структуры ответа health check независимо от статуса."""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "rabbitmq" in data
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

