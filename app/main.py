from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict
import uvicorn
import logging

from models.user_model import User

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Service API",
    description="API для домашнего задания (Урок 2)",
    version="1.0.0"
)

@app.get("/", response_model=Dict[str, str])
async def index() -> Dict[str, str]:
    """
    Корневой эндпоинт, возвращающий приветственное сообщение c информацией о пользователе.
    """
    try:
        # создаем тестового пользователя через нашу модель
        user = User(email="Nick@gmail.com", first_name="Nick", password="password123")
        logger.info(f"Успешный вызов корневого эндпоинта для: {user.email}")
        return {"message": f"Hello world! User: {user.full_name} ({user.email})"}
    except Exception as e:
        logger.error(f"Ошибка в маршруте index: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Эндпоинт проверки работоспособности.
    """
    logger.info("Эндпоинт health_check успешно вызван")
    return {"status": "healthy"}

# Обработчик ошибок
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(f"HTTP Error: {exc.detail} для запроса {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=8000,
        reload=True,
        log_level="debug"
    )

