import logging
import uvicorn
import aio_pika
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.database import init_db
from app.services.mltask_client import MLTaskPublisher, RPCPublisher
from app.services.results_consumer import ResultsConsumer
from aio_pika.pool import Pool
from app.routes.transaction_router import router as transaction_router
from app.routes.ml_router import router as ml_router
from app.routes.user_router import router as user_router
from app.routes.admin_router import router as admin_router
from app.routes.home_router import router as home_router
from app.utils import setup_exception_handlers, setup_logging

# Подключаем логирование
setup_logging()
logger = logging.getLogger(__name__)


#Создадим контекстный менеджер для управления жизненным циклом app
@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.app.MODE != "TEST":
        logger.info("Initializing database...")
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

        logger.info("Connecting to RabbitMQ...")
        try:
            async def get_connection():
                return await aio_pika.connect_robust(
                    settings.mq.amqp_url,
                    timeout=settings.mq.TIMEOUT
                )

            connection_pool = Pool(get_connection, max_size=2)
            application.state.mq_service = MLTaskPublisher(connection_pool)
            application.state.rpc_client = RPCPublisher(connection_pool)
            # Запускаем consumer результатов как фонового работника
            application.state.results_consumer = ResultsConsumer()
            application.state.results_consumer_task = asyncio.create_task(
                application.state.results_consumer.run()
            )
            logger.info("RabbitMQ services initialized with pooling and results consumer started")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ service: {e}")
            application.state.mq_service = None
    else:
        logger.info("Running in TEST mode, skipping global initializations")
        application.state.mq_service = None
        application.state.rpc_client = None

    yield

    logger.info("Application shutting down...")
    # Останавливаем consumer результатов
    if hasattr(application.state, "results_consumer") and application.state.results_consumer:
        await application.state.results_consumer.stop()
    if application.state.mq_service:
        await application.state.mq_service.close()
        await application.state.mq_service.connection_pool.close()

    if application.state.rpc_client:
        await application.state.rpc_client.close()

    logger.info("RabbitMQ connections closed and results consumer stopped")


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
        allow_origins=settings.cors.ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключаем роутеры
    application.include_router(home_router, tags=["Home"])
    application.include_router(user_router, prefix="/api/v1/users", tags=["Users"])
    application.include_router(transaction_router, prefix="/api/v1/balance", tags=["Transactions"])
    application.include_router(ml_router, prefix="/api/v1/requests", tags=["Requests"])
    application.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])

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


