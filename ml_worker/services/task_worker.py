import json
import logging
import asyncio
from typing import Any, Optional

import aio_pika
from sqlalchemy import create_engine, text
from datetime import datetime, timezone

from ml_worker.config import settings
from ml_worker.services.mq_consumer import BaseWorker
from ml_worker.schemas.tasks import MLTask
from ml_worker.schemas.results import MLResult
from ml_worker.engine import ml_engine

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("MLWorker")

class MLWorker(BaseWorker):
    """
    Воркер для выполнения ML задач в фоновом режиме.
    """
    def __init__(self, worker_id: str):
        super().__init__(
            worker_id=worker_id,
            queue_name=settings.mq.QUEUE_NAME,
            amqp_url=settings.mq.amqp_url
        )
        self.engine = create_engine(
            settings.db.url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Обработка входящего сообщения с задачей."""
        async with message.process():
            body = message.body.decode()
            data = json.loads(body)
            task = MLTask(**data)
            logger.info(f"[{self.worker_id}] Получена задача: {task.task_id}")

            prediction = None
            status = "success"
            error_msg = None

            # 1. Выполнение инференса
            try:
                logger.info(f"[{self.worker_id}] Выполнение инференса для задачи {task.task_id}...")
                if isinstance(task.features, list):
                    prediction = ml_engine.predict(task.features)
                else:
                    prediction = ml_engine.predict([task.features])

                # Если результат один, возвращаем строку, иначе список строк
                if isinstance(prediction, list) and len(prediction) == 1:
                    prediction = prediction[0]
            except Exception as e:
                logger.error(f"[{self.worker_id}] Ошибка инференса для задачи {task.task_id}: {e}")
                status = "fail"
                error_msg = str(e)

            # 2. Отправка результата в API (может выбросить Exception после ретраев)
            # Если это случится, message.process() nack-нет сообщение и оно вернется в очередь
            if settings.worker.SAVE_METHOD == "db":
                await self.save_result_to_db(task.task_id, prediction, status, error_msg)
            else:
                await self.publish_result_to_mq(task.task_id, prediction, status, error_msg)

    @retry(
        stop=stop_after_attempt(settings.worker.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=lambda retry_state: logger.info(
            f"Ретрай публикации (попытка {retry_state.attempt_number}) после ошибки: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )

    async def publish_result_to_mq(
        self,
        task_id: str,
        prediction: Optional[Any],
        status: str,
        error: Optional[str]
    ) -> None:
        """Публикация результата обработки в очередь результатов RabbitMQ с ретраями."""
        result = MLResult(
            task_id=task_id,
            prediction=prediction,
            worker_id=self.worker_id,
            status=status,
            error=error
        )

        payload = json.dumps(result.model_dump()).encode()

        logger.info(f"[{self.worker_id}] Публикация результата для {task_id} в MQ...")
        # Используем существующее соединение
        async with self.connection.channel() as channel:
            await channel.set_qos(prefetch_count=settings.worker.PREFETCH_COUNT)
            exchange = await channel.declare_exchange(
                settings.mq.RESULTS_EXCHANGE_NAME,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            # Убедимся, что очередь существует и привязана
            queue = await channel.declare_queue(
                settings.mq.RESULTS_QUEUE_NAME,
                durable=True,
            )
            await queue.bind(exchange, routing_key=settings.mq.RESULTS_ROUTING_KEY)

            message = aio_pika.Message(
                body=payload,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )
            await exchange.publish(message, routing_key=settings.mq.RESULTS_ROUTING_KEY, mandatory=True)

        logger.info(f"[{self.worker_id}] Результат для {task_id} опубликован в MQ.")

    async def save_result_to_db(self, task_id: str, prediction: Optional[Any], status: str, error: Optional[str]) -> None:
        """Сохранение результата напрямую в БД."""
        try:
            # Валидация ID задачи
            try:
                request_id = int(task_id)
            except ValueError:
                logger.error(f"[{self.worker_id}] Некорректный ID задачи: {task_id}")
                return

            e_val = json.dumps([{'error': error}]) if error else None

            with self.engine.begin() as conn:
                query = text("""
                    UPDATE ml_request
                    SET prediction = :p, status = :s, errors = :e, completed_at = :c
                    WHERE id = :id
                """)
                result = conn.execute(query, {
                    'p': json.dumps(prediction),
                    's': status,
                    'e': e_val,
                    'c': datetime.now(timezone.utc),
                    'id': request_id
                })

                if result.rowcount == 0:
                    logger.warning(f"[{self.worker_id}] Запись для задачи {request_id} не найдена в БД")
                else:
                    logger.info(f"[{self.worker_id}] Результат задачи {request_id} сохранен в БД")

        except Exception as e:
            logger.error(f"[{self.worker_id}] Ошибка при сохранении в БД: {e}")
            raise
