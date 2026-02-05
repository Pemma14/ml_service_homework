import pytest
from app.models import User, MLModel, Transaction, TransactionType, TransactionStatus
from app.services.billing_service import (
    create_replenishment_request,
    check_balance,
    process_prediction_payment,
    get_user_balance,
    get_transactions_history
)
from app.schemas import STransactionCreate, SUserRegister
from app.services.user_service import create_user
from app.utils import InsufficientFundsException
from app.config import settings

def test_replenishment_dev_mode(session):
    """Тест пополнения баланса в режиме DEV (мгновенное одобрение)."""
    # Подготовка
    user_data = SUserRegister(
        email="test_replenish@example.com",
        password="password",
        first_name="Test",
        last_name="User",
        phone_number="+79990001111"
    )
    user = create_user(session, user_data)
    initial_balance = user.balance

    # Устанавливаем режим DEV для теста
    old_mode = settings.app.MODE
    settings.app.MODE = "DEV"

    try:
        amount = 150.0
        transaction_data = STransactionCreate(amount=amount)

        transaction = create_replenishment_request(session, user, transaction_data)

        # Проверки
        assert transaction.id is not None
        assert transaction.amount == amount
        assert transaction.status == TransactionStatus.approved
        assert user.balance == initial_balance + amount

        # Проверка через отдельный запрос баланса
        assert get_user_balance(session, user.id) == initial_balance + amount
    finally:
        settings.app.MODE = old_mode

def test_check_balance_logic(session):
    """Тест логики проверки баланса."""
    user_data = SUserRegister(
        email="test_balance@example.com",
        password="password",
        first_name="Balance",
        last_name="Test",
        phone_number="+79990002222"
    )
    user = create_user(session, user_data)
    user.balance = 20.0
    session.add(user)
    session.commit()

    # 1. Денег достаточно
    check_balance(session, user.id, 15.0) # Не должно вызывать исключение

    # 2. Денег недостаточно
    with pytest.raises(InsufficientFundsException):
        check_balance(session, user.id, 25.0)

def test_process_prediction_payment_atomicity(session):
    """Тест атомарности списания средств за предсказание."""
    # 1. Создаем пользователя и модель
    user_data = SUserRegister(
        email="test_payment@example.com",
        password="password",
        first_name="Payer",
        last_name="Test",
        phone_number="+79990003333"
    )
    user = create_user(session, user_data)
    user.balance = 50.0

    model = MLModel(
        name="Test Model",
        code_name="test_model",
        version="1.0"
    )
    session.add(model)
    session.flush()

    # 2. Выполняем списание
    cost = 12.5
    input_data = [{"features": [1, 2, 3, 4, 5]}]
    predictions = ["Result: Responder"]

    request = process_prediction_payment(
        session=session,
        user=user,
        model_id=model.id,
        cost=cost,
        input_data=input_data,
        predictions=predictions
    )

    # 3. Проверяем результат
    assert request.id is not None
    assert user.balance == 37.5

    # Проверяем транзакцию в базе
    history = get_transactions_history(session, user.id)
    payment_tx = next((tx for tx in history if tx.type == TransactionType.payment), None)

    assert payment_tx is not None
    assert payment_tx.amount == -cost
    assert payment_tx.ml_request_id == request.id
    assert payment_tx.status == TransactionStatus.approved

def test_transactions_history_retrieval(session):
    """Тест получения истории транзакций."""
    user_data = SUserRegister(
        email="test_history@example.com",
        password="password",
        first_name="History",
        last_name="User",
        phone_number="+79990004444"
    )
    user = create_user(session, user_data)

    # Создаем несколько транзакций вручную
    tx1 = Transaction(user_id=user.id, amount=100.0, type=TransactionType.replenish, status=TransactionStatus.approved)
    tx2 = Transaction(user_id=user.id, amount=-10.0, type=TransactionType.payment, status=TransactionStatus.approved)
    session.add_all([tx1, tx2])
    session.commit()

    history = get_transactions_history(session, user.id)
    assert len(history) == 2
    assert any(tx.amount == 100.0 for tx in history)
    assert any(tx.amount == -10.0 for tx in history)
