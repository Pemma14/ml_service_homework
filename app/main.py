import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.database import init_db
from app.routes.transaction_router import router as transaction_router
from app.routes.ml_router import router as ml_router
from app.routes.user_router import router as user_router
from app.routes.home_router import router as home_router
from app.utils import setup_exception_handlers, setup_logging

# Подключаем логирование
setup_logging()
logger = logging.getLogger(__name__)


#Создадим контекстный менеджер для управления жизненным циклом app
@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

    yield

    logger.info("Application shutting down...")


def create_application() -> FastAPI:
    """Функция для создания и конфигурации приложения"""
    application = FastAPI(
        title=settings.app.NAME,
        description=settings.app.DESCRIPTION,
        version=settings.app.VERSION,
        docs_url="/api/docs" if settings.app.DEBUG else None,
        redoc_url="/api/redoc" if settings.app.DEBUG else None,
        lifespan=lifespan,
    )

    # Подключаем обработчики исключений
    setup_exception_handlers(application)

    # Настраиваем CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], #в звёздочку вставлю реальный адрес
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключаем роутеры
    application.include_router(home_router, tags=["Home"])
    application.include_router(user_router, prefix="/api/v1/users", tags=["Users"])
    application.include_router(transaction_router, prefix="/api/v1/balance", tags=["Transactions"])
    application.include_router(ml_router, prefix="/api/v1/requests", tags=["Requests"])

    return application


#Создадим объект класса FastAPI
app = create_application()

#Запустим приложение на сервере uvicorn
if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host=settings.app.HOST,
        port=settings.app.PORT,
        reload=settings.app.DEBUG,
        log_level="debug" if settings.app.DEBUG else "info"
    )


