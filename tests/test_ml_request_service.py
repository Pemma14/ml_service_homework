from decimal import Decimal
import pytest
from app.models import User, MLModel, MLRequest
from app.services.ml_request_service import predict, get_all_history
from app.schemas import SUserRegister
from app.services.user_service import create_user
from app.ml import ml_engine

def test_predict_full_flow(session):
    """Интеграционный тест полного цикла предсказания с биллингом."""
    # 1. Подготовка данных
    user_data = SUserRegister(
        email="test_predict_flow@example.com",
        password="password",
        first_name="Flow",
        last_name="Test",
        phone_number="+79990005555"
    )
    user = create_user(session, user_data)
    user.balance = Decimal("50.0")
    session.commit()

    # Создаем активную модель с конкретной стоимостью
    model = MLModel(
        name="Test Logistic Regression",
        code_name="log_reg",
        version="1.0.0",
        is_active=True,
        cost=Decimal("15.0")
    )
    session.add(model)
    session.commit()

    # Параметры запроса
    items = [{
        "Возраст": 40.0,
        "ВНН/ПП": 1,
        "Клозапин": 0,
        "CYP2C19 1/2": 0,
        "CYP2C19 1/17": 0,
        "CYP2C19 *17/*17": 1,
        "CYP2D6 1/3": 0
    }]

    # 2. Вызов оркестратора
    response = predict(session, items, user, ml_engine)

    # 3. Проверки
    assert response.cost == Decimal("15.0")
    assert len(response.predictions) == 1
    assert user.balance == Decimal("50.0") - Decimal("15.0")

    # Проверка записи в истории
    history_query = session.query(MLRequest).filter(MLRequest.user_id == user.id).all()
    assert len(history_query) == 1
    assert history_query[0].cost == response.cost
    assert history_query[0].model_id == model.id


def test_get_all_history_sorting(session):
    """Тест получения истории с корректной сортировкой и данными о модели."""
    from datetime import datetime, timedelta, timezone

    # 1. Подготовка данных
    user_data = SUserRegister(
        email="history_test@example.com",
        password="password",
        first_name="History",
        last_name="Test",
        phone_number="+79990005556"
    )
    user = create_user(session, user_data)

    model = MLModel(
        name="History Model",
        code_name="hist_reg",
        version="1.0.0",
        is_active=True,
        cost=Decimal("10.0")
    )
    session.add(model)
    session.commit()

    # Создаем 3 запроса с разными датами (ручная установка для надежности теста)
    now = datetime.now(timezone.utc)
    r1 = MLRequest(
        user_id=user.id,
        model_id=model.id,
        input_data={"data": 1},
        cost=Decimal("10.0"),
        status="success",
        created_at=now - timedelta(days=2)
    )
    r2 = MLRequest(
        user_id=user.id,
        model_id=model.id,
        input_data={"data": 2},
        cost=Decimal("15.0"),
        status="success",
        created_at=now - timedelta(days=1)
    )
    r3 = MLRequest(
        user_id=user.id,
        model_id=model.id,
        input_data={"data": 3},
        cost=Decimal("20.0"),
        status="success",
        created_at=now
    )
    session.add_all([r1, r2, r3])
    session.commit()

    # 2. Вызов сервиса
    history = get_all_history(session, user.id)

    # 3. Проверки
    assert len(history) == 3
    # Проверка сортировки (desc - от новых к старым)
    assert history[0].cost == Decimal("20.0")  # r3
    assert history[1].cost == Decimal("15.0")  # r2
    assert history[2].cost == Decimal("10.0")  # r1

    # Проверка того, что связанная сущность (модель) подгружена
    assert history[0].ml_model.name == "History Model"
