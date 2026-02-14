import pytest
from fastapi import status
from tests.helpers import assert_user_data

# Позитивные сценарии

def test_get_my_profile_success(auth_client, test_user):
    response = auth_client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert_user_data(data, test_user)


def test_update_profile_success(auth_client):
    update_data = {
        "first_name": "Newname",
        "last_name": "Newlast"
    }
    response = auth_client.patch("/api/v1/users/me", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["first_name"] == "Newname"
    assert data["last_name"] == "Newlast"

    # Проверяем, что изменения сохранились
    get_response = auth_client.get("/api/v1/users/me")
    assert get_response.json()["first_name"] == "Newname"


def test_update_profile_phone_success(auth_client):
    new_phone = "+79998887766"
    update_data = {"phone_number": new_phone}
    response = auth_client.patch("/api/v1/users/me", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["phone_number"] == new_phone


# Негативные сценарии

def test_get_profile_unauthorized(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_profile_invalid_phone(auth_client):
    update_data = {"phone_number": "invalid-phone"}
    response = auth_client.patch("/api/v1/users/me", json=update_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_profile_readonly_fields(auth_client, test_user):
    """Проверка, что чувствительные поля (balance, role) нельзя обновить через PATCH /me."""
    update_data = {
        "balance": 1000000,
        "role": "admin"
    }
    response = auth_client.patch("/api/v1/users/me", json=update_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

