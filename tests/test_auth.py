import pytest
from fastapi import status

# Позитивные сценарии для регистрации и аутентификации

def test_register_success(client):
    payload = {
        "email": "new_user@example.com",
        "password": "strongpassword",
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "phone_number": "+79001112233"
    }
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "message" in data
    assert "успешно зарегистрированы" in data["message"]


def test_login_success(client, test_user):
    login_data = {"email": test_user.email, "password": "password"}
    response = client.post("/api/v1/users/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"


def test_get_me_success(auth_client, test_user):
    response = auth_client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email
    assert "balance" in data


# Негативные сценарии для регистрации и аутентификации

def test_register_duplicate_email(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "anypassword",
        "first_name": "Duplicate",
        "last_name": "User",
        "phone_number": "+70000000000"
    }
    response = client.post("/api/v1/users/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert "message" in data
    assert "уже существует" in data["message"]


def test_login_invalid_password(client, test_user):e
    login_data = {"email": test_user.email, "password": "wrong_password"}
    response = client.post("/api/v1/users/login", json=login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "message" in data
    assert "Неверный" in data["message"]


def test_get_me_unauthorized(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_invalid_token(client):
    headers = {"Authorization": "Bearer invalid_token_value"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
