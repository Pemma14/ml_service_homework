from decimal import Decimal
import pytest
from app.services.user_service import UserService
from app.schemas import SUserRegister
from app.models import User, MLRequest, Transaction, TransactionType, TransactionStatus, MLRequestStatus, MLModel
from datetime import datetime, timezone

def test_create_user(session):
    service = UserService(session)
    user_data = SUserRegister(
        email="test@example.com",
        password="password123",
        first_name="Test",
        last_name="User",
        phone_number="+79991112233"
    )
    user = service.create_user(user_data)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.balance == Decimal("0.0")

    # Проверка загрузки из БД по ID
    loaded_user = service.get_user_by_id(user.id)
    assert loaded_user is not None
    assert loaded_user.email == "test@example.com"

def test_get_user_by_email(session):
    service = UserService(session)
    user_data = SUserRegister(
        email="email@example.com",
        password="password123",
        first_name="Email",
        last_name="User",
        phone_number="+79994445566"
    )
    service.create_user(user_data)

    user = service.get_user_by_email("email@example.com")
    assert user is not None
    assert user.first_name == "Email"

def test_user_balance_and_history(session):
    # 1. Создаем пользователя
    user_data = SUserRegister(
        email="history@example.com",
        password="password123",
        first_name="History",
        last_name="User",
        phone_number="+79997778899"
    )
    service = UserService(session)
    user = service.create_user(user_data)

    # 2. Создаем модель
    model = MLModel(
        name="Test Model",
        code_name="test_model",
        description="Test Description",
        version="1.0.0",
        cost=Decimal("10.0")
    )
    session.add(model)
    session.flush()

    # 3. Обновляем баланс напрямую (имитация пополнения)
    user.balance = Decimal("100.0")
    session.commit()
    session.refresh(user)
    assert user.balance == Decimal("100.0")

    # 4. Добавляем историю запросов
    request = MLRequest(
        user_id=user.id,
        model_id=model.id,
        input_data={"test": "data"},
        prediction={"result": "ok"},
        cost=Decimal("10.0"),
        status=MLRequestStatus.success,
        completed_at=datetime.now(timezone.utc)
    )
    session.add(request)
    session.flush()

    # 5. Добавляем транзакцию
    transaction = Transaction(
        user_id=user.id,
        amount=Decimal("-10.0"),
        type=TransactionType.payment,
        status=TransactionStatus.approved,
        description="Test Payment",
        ml_request_id=request.id
    )
    session.add(transaction)
    session.commit()
    session.refresh(user)

    # 6. Проверяем связи
    assert len(user.ml_requests) == 1
    assert user.ml_requests[0].cost == Decimal("10.0")
    assert len(user.transactions) == 1
    assert user.transactions[0].amount == Decimal("-10.0")
    assert user.transactions[0].ml_request_id == user.ml_requests[0].id

def test_update_user(session):
    user_data = SUserRegister(
        email="update@example.com",
        password="password123",
        first_name="Update",
        last_name="User",
        phone_number="+79998887766"
    )
    service = UserService(session)
    user = service.create_user(user_data)

    from app.schemas import SUserUpdate
    update_data = SUserUpdate(first_name="UpdatedName", phone_number="+70000000000")

    updated_user = service.update_user(user.id, update_data)

    assert updated_user.first_name == "UpdatedName"
    assert updated_user.phone_number == "+70000000000"
    assert updated_user.last_name == "User"  # Не должно измениться
