from fastapi import APIRouter, Depends, Response, status, Request
from typing import Any, Dict
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.database import get_session
from app.services.mltask_client import MLTaskPublisher, get_mq_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Главная страница",
    description="Возвращает приветственное сообщение и список основных возможностей сервиса PsyPharmPredict."
)
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

@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Проверка работоспособности",
    description="Мониторинг состояния сервиса: БД, RabbitMQ, ResultsConsumer и потребители очередей.",
    responses={
        200: {"description": "OK/Degraded"},
        503: {"description": "Critical: один или несколько ключевых сервисов недоступны"}
    }
)
async def health_check(
    response: Response,
    request: Request,
    session: Session = Depends(get_session),
    mq_service: MLTaskPublisher = Depends(get_mq_service)
) -> Dict[str, Any]:
    """Расширенная проверка: БД, RabbitMQ, ResultsConsumer, очереди и потребители.
    Статусы:
    - ok: всё в порядке
    - degraded: ядро доступно, но часть компонентов ограничена (нет воркеров/consumer'ов, consumer результатов остановлен)
    - error: критический сбой (БД или RabbitMQ недоступны)
    """
    from datetime import datetime, timezone

    result: Dict[str, Any] = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # для обратной совместимости с существующими проверками
        "database": "connected",
        "rabbitmq": "connected",
        # подробности
        "workers": {},
        "results_consumer": "unknown",
        "details": {}
    }

    # 1) База данных
    try:
        session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed: database error: {e}")
        result["database"] = "disconnected"
        result["status"] = "error"
        result["details"]["database_error"] = str(e)

    # 2) RabbitMQ + очереди и consumers
    rabbit_ok = True
    queues_info: Dict[str, Any] = {}
    if result["status"] != "error":  # продолжаем проверку MQ только если БД ок
        try:
            async with mq_service.channel_pool.acquire() as channel:
                async def q_info(name: str) -> Dict[str, Any]:
                    try:
                        q = await channel.declare_queue(name, durable=True, passive=True)
                        dr = getattr(q, "declaration_result", None)
                        msg = getattr(dr, "message_count", None) if dr else None
                        cons = getattr(dr, "consumer_count", None) if dr else None
                        return {"messages": msg, "consumers": cons}
                    except Exception as qe:
                        return {"error": str(qe)}

                queues_info["tasks_queue"] = await q_info(settings.mq.QUEUE_NAME)
                queues_info["rpc_queue"] = await q_info(getattr(settings.mq, "RPC_QUEUE_NAME", "rpc_queue"))
                queues_info["results_queue"] = await q_info(settings.mq.RESULTS_QUEUE_NAME)
        except Exception as e:
            logger.error(f"Health check failed: rabbitmq error: {e}")
            rabbit_ok = False
            result["rabbitmq"] = "disconnected"
            result["status"] = "error"
            result["details"]["rabbitmq_error"] = str(e)

    result["workers"] = queues_info

    # 3) ResultsConsumer (фоновая задача FastAPI)
    try:
        rc = getattr(request.app.state, "results_consumer", None)
        rc_ok = False
        if rc is not None:
            conn_ok = bool(rc.connection and not rc.connection.is_closed)
            ch_ok = bool(rc.channel and not rc.channel.is_closed)
            rc_ok = conn_ok and ch_ok
        result["results_consumer"] = "connected" if rc_ok else "disconnected"
    except Exception as e:
        result["results_consumer"] = "disconnected"
        result["details"]["results_consumer_error"] = str(e)

    # 4) Итоговый статус (degraded, если ядро ок, но нет воркеров/consumer'ов или consumer результатов упал)
    if result["status"] != "error":
        # Оценим наличие потребителей задач/результатов
        def _consumers(d: Dict[str, Any]) -> int:
            try:
                v = d.get("consumers")
                return int(v) if v is not None else 0
            except Exception:
                return 0
        total_consumers = sum(_consumers(v) for v in queues_info.values() if isinstance(v, dict))
        degraded_reasons: list[str] = []
        if total_consumers == 0:
            degraded_reasons.append("no_workers")
        if result["results_consumer"] != "connected":
            degraded_reasons.append("results_consumer_down")
        # добавим сводку
        result["workers"]["total_consumers"] = total_consumers
        if degraded_reasons:
            result["status"] = "degraded"
            result["details"]["degraded_reasons"] = degraded_reasons

    if result["status"] == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result
