import pytest

def test_jwt_auth_flow(client):
    # 1. Регистрация
    email = "jwt_test_flow@example.com"
    password = "testpassword"
    register_data = {
        "email": email,
        "password": password,
        "first_name": "JWT",
        "last_name": "Test",
        "phone_number": "+70000000000"
    }
    response = client.post("/api/v1/users/register", json=register_data)
    assert response.status_code == 201

    # 2. Логин
    login_data = {"email": email, "password": password}
    response = client.post("/api/v1/users/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]

    # 3. Доступ к защищенному эндпоинту /me с токеном
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email

    # 4. Доступ к защищенному эндпоинту без токена
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

    # 5. Доступ с неверным токеном
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
