import pytest
import os

if "APP__MODE" not in os.environ:
    os.environ["APP__MODE"] = "TEST"
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
    """Сессия с автоматическим откатом транзакции после теста."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def active_model(session):
    """Создаёт активную ML модель для тестирования."""
    from app.models import MLModel
    from tests.helpers import TEST_MODEL_COST

    model = MLModel(
        name="Test Model",
        code_name="test_model",
        version="1.0.0",
        is_active=True,
        cost=TEST_MODEL_COST
    )
    session.add(model)
    session.flush()
    session.refresh(model)
    return model

@pytest.fixture(scope="function")
def mock_mq_service():
    """Мок для MQ сервиса."""
    from unittest.mock import AsyncMock, MagicMock

    mock_mq = MagicMock()
    mock_mq.channel_pool = MagicMock()
    mock_mq.channel_pool.acquire.return_value = AsyncMock()
    mock_mq.send_task = AsyncMock(return_value=None)
    return mock_mq


@pytest.fixture(scope="function")
def mock_rpc_client():
    """Мок для RPC клиента."""
    from unittest.mock import AsyncMock

    mock_rpc = AsyncMock()
    mock_rpc.call.return_value = b'{"prediction": [0.5]}'
    return mock_rpc


@pytest.fixture(scope="function")
def client(session, active_model, mock_mq_service, mock_rpc_client):
    """TestClient с замоканными зависимостями."""
    def override_get_session():
        yield session

    from app.services.mltask_client import get_mq_service, get_rpc_client

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_mq_service] = lambda: mock_mq_service
    app.dependency_overrides[get_rpc_client] = lambda: mock_rpc_client

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(session):
    """Фикстура для создания тестового пользователя."""
    from app.models import User, UserRole
    from app.auth.hash_password import HashPassword
    from decimal import Decimal
    hasher = HashPassword()
    user = User(
        email="test_user@example.com",
        hashed_password=hasher.create_hash("password"),
        first_name="Test",
        last_name="User",
        phone_number="+70000000000",
        balance=Decimal("0.0"),
        role=UserRole.user
    )
    session.add(user)
    session.flush()
    session.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_user(session):
    """Фикстура для создания администратора."""
    from app.models import User, UserRole
    from app.auth.hash_password import HashPassword
    from decimal import Decimal
    hasher = HashPassword()
    user = User(
        email="admin@example.com",
        hashed_password=hasher.create_hash("password"),
        first_name="Admin",
        last_name="User",
        phone_number="+71111111111",
        balance=Decimal("0.0"),
        role=UserRole.admin
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
    try:
        yield client
    finally:
        if authenticate in app.dependency_overrides:
            del app.dependency_overrides[authenticate]


@pytest.fixture(scope="function")
def admin_client(client, admin_user):
    """Клиент с подменой авторизации"""
    from app.routes.dependencies import authenticate

    app.dependency_overrides[authenticate] = lambda: str(admin_user.id)
    try:
        yield client
    finally:
        if authenticate in app.dependency_overrides:
            del app.dependency_overrides[authenticate]


@pytest.fixture(scope="function")
def funded_user(session, test_user):
    """Тестовый пользователь с положительным балансом."""
    from decimal import Decimal
    from tests.helpers import DEFAULT_REPLENISH_AMOUNT

    test_user.balance = Decimal(str(DEFAULT_REPLENISH_AMOUNT))
    session.flush()
    session.refresh(test_user)
    return test_user


@pytest.fixture(scope="function")
def funded_client(client, funded_user):
    """Клиент, авторизованный под пользователя с положительным балансом."""
    from app.routes.dependencies import authenticate

    app.dependency_overrides[authenticate] = lambda: str(funded_user.id)
    try:
        yield client
    finally:
        if authenticate in app.dependency_overrides:
            del app.dependency_overrides[authenticate]
