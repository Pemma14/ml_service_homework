import logging
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.utils import setup_exception_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app.NAME,
    description=settings.app.DESCRIPTION,
    version=settings.app.VERSION,
)

# Обработчики исключений
setup_exception_handlers(app)


@app.get("/", tags=["Home"])
async def home_page() -> Dict[str, Any]:
    """Главная страница с описанием сервиса."""
    return {
        "message": "Welcome to PsyPharmPredict.org!",
        "description": "Наш сервис позволяет выполнять предсказания на основе ваших данных. "
                       "Пополняйте баланс и получайте доступ к современным моделям машинного обучения.",
        "features": [
            "Регистрация и личный кабинет",
            "Управление балансом (кредиты)",
            "Предсказание",
            "История запросов и транзакций",
        ]
    }

@app.get("/health", tags=["Home"])
async def health_check() -> Dict[str, str]:
    """Проверка работоспособности приложения."""
    logger.info("Эндпоинт health_check успешно вызван")
    return {"status": "ok"}


# Тесты
if __name__ == '__main__':
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from app.database import get_database_engine, init_db
    from app.models import User, MLRequest, MLModel, Transaction, TransactionType, TransactionStatus, MLRequestStatus
    from app.services.user_service import get_all_users, create_user
    from app.services.billing_service import get_transactions_history

    init_db(drop_all=True)
    print('Init db has been success')

    test_user = User(
        email='test1@gmail.com',
        password='test',
        first_name='Test1',
        last_name='User',
        phone_number='+79991112233'
    )
    test_user_2 = User(
        email='test2@gmail.com',
        password='test',
        first_name='Test2',
        last_name='User',
        phone_number='+79992223344'
    )
    test_user_3 = User(
        email='test3@gmail.com',
        password='test',
        first_name='Test3',
        last_name='User',
        phone_number='+79993334455'
    )

    engine = get_database_engine()

    with Session(engine) as session:

        create_user(session, test_user)
        create_user(session, test_user_2)
        create_user(session, test_user_3)

        # 1. Тестируем пополнение баланса
        print('Тестирование баланса...')
        replenish_tx = Transaction(
            user=test_user,
            amount=500.0,
            type=TransactionType.replenish,
            status=TransactionStatus.approved,
            description="Тестовое пополнение баланса"
        )
        test_user.balance += 500.0
        session.add(replenish_tx)

        # 2. Тестируем создание запроса
        # Получаем модель для создания запросов (модели создаются в seed_db внутри init_db)
        ml_model = session.execute(select(MLModel)).scalars().first()

        test_request = MLRequest(
            user=test_user,
            ml_model=ml_model,
            input_data={"features": [1.0, 2.0, 3.0]},
            status=MLRequestStatus.success,
            cost=ml_model.cost if ml_model else 0.0
        )
        test_request_2 = MLRequest(
            user=test_user,
            ml_model=ml_model,
            input_data={"features": [0.5, 1.5, 2.5]},
            status=MLRequestStatus.pending,
            cost=ml_model.cost if ml_model else 0.0
        )
        session.add(test_request)
        session.add(test_request_2)
        session.flush()  # Получаем ID для запросов, чтобы использовать их ниже

        # 3. Тестируем списание
        if ml_model:
            payment_tx = Transaction(
                user=test_user,
                amount=-ml_model.cost,
                type=TransactionType.payment,
                status=TransactionStatus.approved,
                description=f"Оплата за модель {ml_model.name}",
                ml_request_id=test_request.id
            )
            test_user.balance -= ml_model.cost
            session.add(payment_tx)

        session.commit()

        users = get_all_users(session)

        transactions = get_transactions_history(session, test_user.id)

        print('-------')
        print(f'Id локального пользователя: {id(test_user)}')
        # В users могут быть сидовые данные, поэтому ищем нашего пользователя для корректности id check
        db_user = next((u for u in users if u.email == 'test1@gmail.com'), users[0])
        print(f'Id пользователя из БД: {id(db_user)}')
        print(f'Id одинаковые: {id(test_user) == id(db_user)}')
        print(f'Баланс пользователя в БД: {db_user.balance}')

        print('-------')
        print('История транзакций пользователя:')
        for tx in transactions:
            print(f"[{tx.type}] {tx.amount} credits: {tx.description} ({tx.status})")

        print('-------')
        print('Пользователи из БД:')
        for user in users:
            print(user)
            print('Пользовательские запросы:')
            if not user.ml_requests:
                print('Пользователь не имеет запросов')
            else:
                for request in user.ml_requests:
                    print(request)

    uvicorn.run(
        'app.main:app',
        host=settings.app.HOST,
        port=settings.app.PORT,
        reload=settings.app.DEBUG,
        log_level="debug" if settings.app.DEBUG else "info"
    )

