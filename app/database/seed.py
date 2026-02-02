import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.config import settings
from app.models import (
    User, UserRole, Transaction, TransactionType, TransactionStatus,
    MLRequest, MLRequestStatus, MLModel
)
from datetime import datetime

logger = logging.getLogger(__name__)

def seed_db(session: Session):
    """Наполнение базы данных начальными данными."""
    logger.info("Проверка необходимости инициализации начальных данных...")

    # 1. Сидирование ML-моделей
    models_to_seed = [
        {
            "name": "Logistic Regression",
            "code_name": "log_reg",
            "description": "Классическая логистическая регрессия для бинарной классификации",
            "version": "1.0.0",
            "cost": 10.0
        },
        {
            "name": "Random Forest Classifier",
            "code_name": "rf_clf",
            "description": "Модель случайного леса для более точных предсказаний",
            "version": "1.1.0",
            "cost": 25.0
        }
    ]

    for model_data in models_to_seed:
        existing_model = session.execute(
            select(MLModel).where(MLModel.code_name == model_data["code_name"])
        ).scalars().first()

        if not existing_model:
            logger.info(f"Добавление ML-модели: {model_data['name']}")
            new_model = MLModel(**model_data)
            session.add(new_model)

    session.flush()

    # 2. Сидирование пользователей
    users_to_seed = [
        {
            "first_name": "Admin",
            "last_name": "System",
            "email": settings.seed.ADMIN_EMAIL,
            "hashed_password": settings.seed.ADMIN_PASSWORD,
            "phone_number": "+70000000000",
            "balance": 1000.0,
            "role": UserRole.admin,
            "initial_balance_desc": "Начальный баланс администратора"
        },
        {
            "first_name": "Demo",
            "last_name": "User",
            "email": settings.seed.DEMO_EMAIL,
            "hashed_password": settings.seed.DEMO_PASSWORD,
            "phone_number": "+79991234567",
            "balance": 100.0,
            "role": UserRole.user,
            "initial_balance_desc": "Начальный баланс демо-пользователя"
        }
    ]

    for user_data in users_to_seed:
        existing_user = session.execute(
            select(User).where(User.email == user_data["email"])
        ).scalars().first()

        if not existing_user:
            logger.info(f"Добавление пользователя: {user_data['email']}")
            initial_balance_desc = user_data.pop("initial_balance_desc")
            new_user = User(**user_data)
            session.add(new_user)
            session.flush()

            # Добавляем транзакцию пополнения
            session.add(Transaction(
                user_id=new_user.id,
                amount=new_user.balance,
                type=TransactionType.replenish,
                status=TransactionStatus.approved,
                description=initial_balance_desc
            ))

            # Если это демо-пользователь, добавим ему один тестовый запрос для истории
            if user_data["email"] == settings.seed.DEMO_EMAIL:
                log_reg = session.execute(
                    select(MLModel).where(MLModel.code_name == "log_reg")
                ).scalars().first()

                if log_reg:
                    test_request = MLRequest(
                        user_id=new_user.id,
                        model_id=log_reg.id,
                        input_data={"features": [1.0, 2.0, 3.0, 4.0, 5.0]},
                        prediction={"result": "Responder", "confidence": 0.85},
                        cost=log_reg.cost,
                        status=MLRequestStatus.success,
                        completed_at=datetime.now()
                    )
                    session.add(test_request)
                    session.flush()

                    session.add(Transaction(
                        user_id=new_user.id,
                        amount=-log_reg.cost,
                        type=TransactionType.payment,
                        status=TransactionStatus.approved,
                        description=f"Оплата ML-запроса №{test_request.id}",
                        ml_request_id=test_request.id
                    ))
                    new_user.balance -= log_reg.cost

    try:
        session.commit()
        logger.info("Инициализация базы данных успешно завершена.")
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
