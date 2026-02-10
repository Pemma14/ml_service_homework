import json
import logging
import aio_pika
from ml_worker.services.mltask_consumer import BaseWorker
from ml_worker.services.engine import ml_engine
from ml_worker.config import settings

logger = logging.getLogger("RPCWorker")

class RPCWorker(BaseWorker):
    """
    Воркер для обработки синхронных RPC-запросов.
    """
    def __init__(self, worker_id: str):
        super().__init__(
            worker_id=worker_id,
            queue_name=settings.mq.RPC_QUEUE_NAME,
            amqp_url=settings.mq.amqp_url
        )

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        Обработка RPC запроса.
        Ожидает JSON список данных для предсказания.
        """
        async with message.process(requeue=True):
            # Проверяем обязательные RPC-атрибуты
            if not message.reply_to or not message.correlation_id:
                logger.error(f"[{self.worker_id}] Некорректное RPC-сообщение: нет reply_to или correlation_id")
                return

            try:
                # Декодируем тело запроса
                payload = json.loads(message.body.decode())
                logger.info(f"[{self.worker_id}] Получен RPC запрос (corr_id: {message.correlation_id})")

                # Выполняем инференс
                # В нашем API RPCPublisher отправляет данные как список (prepared_data)
                predictions = ml_engine.predict(payload)

                response_obj = {"predictions": predictions}
                body = json.dumps(response_obj).encode()

                # Отправляем ответ
                await self._send_rpc_response(
                    body=body,
                    correlation_id=message.correlation_id,
                    reply_to=message.reply_to
                )
                logger.info(f"[{self.worker_id}] RPC-ответ успешно отправлен")

            except Exception as e:
                logger.error(f"[{self.worker_id}] Ошибка при обработке RPC запроса: {e}")
                # Отправляем информацию об ошибке клиенту, чтобы он не ждал по таймауту
                try:
                    error_obj = {"error": str(e)}
                    await self._send_rpc_response(
                        body=json.dumps(error_obj).encode(),
                        correlation_id=message.correlation_id,
                        reply_to=message.reply_to
                    )
                except Exception as send_err:
                    logger.critical(f"[{self.worker_id}] Не удалось отправить сообщение об ошибке: {send_err}")
                    # В этом случае message.process(requeue=True) сделает nack, если пробросим исключение
                    raise e

    async def _send_rpc_response(self, body: bytes, correlation_id: str, reply_to: str) -> None:
        """Вспомогательный метод для отправки ответа в RabbitMQ."""
        # Используем тот же канал, на котором слушаем, или создаем новый через соединение
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
