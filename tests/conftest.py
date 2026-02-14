import os

# Устанавливаем режим тестирования до загрузки приложения
os.environ["APP__MODE"] = "TEST"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import Base
from app.database import get_session
from fastapi.testclient import TestClient
from app.main import app

# Используем SQLite в памяти для тестов
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def active_model(session):
    from app.models import MLModel
    from decimal import Decimal
    model = MLModel(
        name="Test Model",
        code_name="test_model",
        version="1.0.0",
        is_active=True,
        cost=Decimal("10.0")
    )
    session.add(model)
    session.flush()
    session.refresh(model)
    return model

@pytest.fixture(scope="function")
def client(session, active_model):
    def override_get_session():
        yield session

    from unittest.mock import AsyncMock, MagicMock
    from app.services.mltask_client import get_mq_service, get_rpc_client
    app.dependency_overrides[get_session] = override_get_session

    # Мокаем MQ сервисы через dependency_overrides
    # mock_mq должен поддерживать mq_service.channel_pool.acquire() для health check
    mock_mq = MagicMock()
    mock_mq.channel_pool = MagicMock()
    # acquire() возвращает AsyncMock, который работает как асинхронный контекстный менеджер
    mock_mq.channel_pool.acquire.return_value = AsyncMock()
    mock_mq.send_task = AsyncMock(return_value=None)

    # mock_rpc должен возвращать байты при вызове call()
    mock_rpc = AsyncMock()
    mock_rpc.call.return_value = b'{"prediction": [0.5]}'

    app.dependency_overrides[get_mq_service] = lambda: mock_mq
    app.dependency_overrides[get_rpc_client] = lambda: mock_rpc

    with TestClient(app) as c:
        yield c

    # Чистим переопределения
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(session):
    """Фикстура для создания тестового пользователя."""
    from app.models import User
    from app.auth.hash_password import HashPassword
    from decimal import Decimal
    hasher = HashPassword()
    user = User(
        email="test_user@example.com",
        hashed_password=hasher.create_hash("password"),
        first_name="Test",
        last_name="User",
        phone_number="+70000000000",
        balance=Decimal("0.0")
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_client(client, test_user):
    """Клиент с подменой авторизации (сразу под тестовым пользователем)."""
    from app.routes.dependencies import authenticate
    app.dependency_overrides[authenticate] = lambda: str(test_user.id)
    yield client
    # После теста authenticate удалится через app.dependency_overrides.clear() в фикстуре client
    # или можно явно удалить, если мы не уверены в порядке
    if authenticate in app.dependency_overrides:
        del app.dependency_overrides[authenticate]
