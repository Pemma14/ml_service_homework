import json
import logging
from typing import Any, Optional
import aio_pika
from tenacity import retry, stop_after_attempt, wait_exponential

from ml_worker.config import settings
from ml_worker.schemas.results import MLResult

logger = logging.getLogger("MQPublisher")

class MQResultPublisher:
    def __init__(self, connection: aio_pika.RobustConnection, worker_id: str):
        self.connection = connection
        self.worker_id = worker_id

    @retry(
        stop=stop_after_attempt(settings.worker.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=lambda retry_state: logger.info(
            f"Ретрай публикации результата (попытка {retry_state.attempt_number}) после ошибки: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    async def publish_result(
        self,
        task_id: str,
        prediction: Optional[Any],
        status: str,
        error: Optional[str] = None
    ) -> None:
        """Публикация результата обработки в очередь результатов RabbitMQ."""
        result = MLResult(
            task_id=task_id,
            prediction=prediction,
            worker_id=self.worker_id,
            status=status,
            error=error
        )

        payload = json.dumps(result.model_dump()).encode()

        logger.info(f"[{self.worker_id}] Публикация результата для {task_id} в MQ...")
        async with self.connection.channel() as channel:
            await channel.set_qos(prefetch_count=settings.worker.PREFETCH_COUNT)
            exchange = await channel.declare_exchange(
                settings.mq.RESULTS_EXCHANGE_NAME,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
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

    @retry(
        stop=stop_after_attempt(settings.worker.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=lambda retry_state: logger.info(
            f"Ретрай отправки RPC ответа (попытка {retry_state.attempt_number}) после ошибки: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    async def publish_rpc_response(self, body: bytes, correlation_id: str, reply_to: str) -> None:
        """Отправка RPC ответа в RabbitMQ."""
        async with self.connection.channel() as channel:
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=body,
                    correlation_id=correlation_id,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.NOT_PERSISTENT
                ),
                routing_key=reply_to
            )
