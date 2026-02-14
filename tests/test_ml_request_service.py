from decimal import Decimal
import pytest
from app.models import User, MLModel, MLRequest, MLRequestStatus
from app.services.ml_service import MLRequestService
from app.schemas import SUserRegister
from app.services.user_service import UserService



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
    service = UserService(session)
    user = service.create_user(user_data)

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
    ml_service = MLRequestService(session)
    history = ml_service.get_all_history(user.id)

    # 3. Проверки
    assert len(history) == 3
    # Проверка сортировки (desc - от новых к старым)
    assert history[0].cost == Decimal("20.0")  # r3
    assert history[1].cost == Decimal("15.0")  # r2
    assert history[2].cost == Decimal("10.0")  # r1

    # Проверка того, что связанная сущность (модель) подгружена
    assert history[0].ml_model.name == "History Model"


class MockMQService:
    async def send_task(self, task):
        return None


def test_create_and_send_task_prepares_data(session):
    """Тест того, что create_and_send_task корректно подготавливает данные из Pydantic моделей."""
    from app.schemas.ml_request_schemas import SMLFeatureItem
    from decimal import Decimal

    # 1. Подготовка данных
    user_data = SUserRegister(
        email="prepare_test@example.com",
        password="password",
        first_name="Prepare",
        last_name="Test",
        phone_number="+79990005557"
    )
    service = UserService(session)
    user = service.create_user(user_data)
    user.balance = Decimal("100.0")
    session.commit()

    model = MLModel(
        name="Test Model",
        code_name="test_model",
        version="1.0.0",
        is_active=True,
        cost=Decimal("10.0")
    )
    session.add(model)
    session.commit()

    feature_item = SMLFeatureItem(
        age=30,
        vnn_pp=1,
        clozapine=0,
        cyp2c19_1_2=0,
        cyp2c19_1_17=1,
        cyp2c19_17_17=0,
        cyp2d6_1_3=0
    )

    ml_service = MLRequestService(session)
    mq_service = MockMQService()

    # 2. Вызов метода с сырыми Pydantic моделями
    import asyncio
    db_request = asyncio.run(ml_service.create_and_send_task(
        user=user,
        input_data=[feature_item],
        mq_service=mq_service
    ))

    # 3. Проверки
    assert db_request.input_data[0]["Возраст"] == 30
    assert "Возраст" in db_request.input_data[0]
    assert db_request.is_published is True
    assert db_request.message == "Запрос принят и находится в обработке"



def test_process_task_result_success(session):
    """Тест успешной обработки результата задачи."""
    from app.schemas.ml_task_schemas import MLResult
    from decimal import Decimal

    # 1. Подготовка данных
    user_data = SUserRegister(
        email="result_test@example.com",
        password="password",
        first_name="Result",
        last_name="Test",
        phone_number="+79990005558"
    )
    service = UserService(session)
    user = service.create_user(user_data)

    model = MLModel(
        name="Test Model",
        code_name="test_model",
        version="1.0.0",
        is_active=True,
        cost=Decimal("10.0")
    )
    session.add(model)
    session.commit()

    db_request = MLRequest(
        user_id=user.id,
        model_id=model.id,
        input_data={"data": "test"},
        cost=Decimal("10.0"),
        status=MLRequestStatus.pending
    )
    session.add(db_request)
    session.commit()

    result_data = MLResult(
        task_id=str(db_request.id),
        prediction=[0.5],
        worker_id="worker-1",
        status="success"
    )

    # 2. Вызов метода
    import asyncio
    ml_service = MLRequestService(session)
    response = asyncio.run(ml_service.process_task_result(result_data))
    session.commit()

    # 3. Проверки
    assert response["message"] == "Результат успешно сохранен"
    session.refresh(db_request)
    assert db_request.status == MLRequestStatus.success
    assert db_request.prediction == [0.5]
    assert db_request.completed_at is not None


def test_process_task_result_fail_refunds_balance(session):
    """Тест того, что при ошибке выполнения (fail) баланс возвращается пользователю."""
    from app.schemas.ml_task_schemas import MLResult
    from decimal import Decimal

    # 1. Подготовка данных
    user_data = SUserRegister(
        email="refund_test@example.com",
        password="password",
        first_name="Refund",
        last_name="Test",
        phone_number="+79990005559"
    )
    service = UserService(session)
    user = service.create_user(user_data)
    user.balance = Decimal("100.0")
    session.commit()

    model = MLModel(
        name="Test Model",
        code_name="test_model",
        version="1.0.0",
        is_active=True,
        cost=Decimal("10.0")
    )
    session.add(model)
    session.commit()

    # Имитируем резервирование средств
    from app.services.billing_service import BillingService
    billing_service = BillingService(session)
    billing_service.reserve_funds(user, Decimal("10.0"))
    assert user.balance == Decimal("90.0")

    db_request = MLRequest(
        user_id=user.id,
        model_id=model.id,
        input_data={"data": "test"},
        cost=Decimal("10.0"),
        status=MLRequestStatus.pending
    )
    session.add(db_request)
    session.commit()

    result_data = MLResult(
        task_id=str(db_request.id),
        prediction=None,
        worker_id="worker-1",
        status="fail",
        error="Model error"
    )

    # 2. Вызов метода
    import asyncio
    ml_service = MLRequestService(session)
    asyncio.run(ml_service.process_task_result(result_data))
    session.commit()

    # 3. Проверки
    session.refresh(user)
    session.refresh(db_request)

    # Баланс должен вернуться к 100.0
    assert user.balance == Decimal("100.0")
    assert db_request.status == MLRequestStatus.fail
    assert db_request.errors == [{"error": "Model error"}]
