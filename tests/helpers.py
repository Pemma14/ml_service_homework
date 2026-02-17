from decimal import Decimal

# Константы для тестирования
TEST_MODEL_COST = Decimal("10.0")
DEFAULT_REPLENISH_AMOUNT = 100.0
VALID_FEATURE_DATA = {
    "patient_id": "TEST-PATIENT",
    "age": 30,
    "vnn_pp": 1,
    "clozapine": 0,
    "cyp2c19_1_2": 0,
    "cyp2c19_1_17": 1,
    "cyp2c19_17_17": 0,
    "cyp2d6_1_3": 0
}


def get_valid_feature_data(**overrides):
    data = VALID_FEATURE_DATA.copy()
    data.update(overrides)
    return data


def replenish_user_balance(client, amount: float = DEFAULT_REPLENISH_AMOUNT):
    return client.post("/api/v1/balance/replenish", json={"amount": amount})


def get_user_balance(client) -> float:
    response = client.get("/api/v1/balance/check_balance")
    return float(response.json()["balance"])


def create_ml_request(client, feature_data: dict = None):
    if feature_data is None:
        feature_data = VALID_FEATURE_DATA
    return client.post("/api/v1/requests/send_task", json={"data": [feature_data]})


def create_ml_request_rpc(client, feature_data: dict = None):
    if feature_data is None:
        feature_data = VALID_FEATURE_DATA
    return client.post("/api/v1/requests/send_task_rpc", json={"data": [feature_data]})


def assert_user_data(response_data: dict, expected_user):
    assert response_data["email"] == expected_user.email
    assert response_data["first_name"] == expected_user.first_name
    assert response_data["last_name"] == expected_user.last_name
    assert response_data["phone_number"] == expected_user.phone_number
    assert "balance" in response_data
