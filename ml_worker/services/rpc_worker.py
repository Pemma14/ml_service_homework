import json
import logging
import aio_pika
from ml_worker.services.mq_consumer import BaseWorker
from ml_worker.services.mq_publisher import MQResultPublisher
from ml_worker.engine import ml_engine
from ml_worker.config import settings

logger = logging.getLogger("RPCWorker")

class RPCWorker(BaseWorker):
    """Воркер для обработки синхронных RPC-запросов."""
    def __init__(self, worker_id: str):
        super().__init__(
            worker_id=worker_id,
            queue_name=settings.mq.RPC_QUEUE_NAME,
            amqp_url=settings.mq.amqp_url
        )
        self._publisher = None

    @property
    def publisher(self) -> MQResultPublisher:
        if self._publisher is None:
            self._publisher = MQResultPublisher(self.connection, self.worker_id)
        return self._publisher

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        Обработка RPC запроса.
        Ожидает JSON список данных для предсказания.
        """
        async with message.process(requeue=True):
            if not message.reply_to or not message.correlation_id:
                logger.error(f"[{self.worker_id}] Некорректное RPC-сообщение: нет reply_to или correlation_id")
                return

            try:
                payload = json.loads(message.body.decode())
                logger.info(f"[{self.worker_id}] Получен RPC запрос (corr_id: {message.correlation_id})")

                predictions = ml_engine.predict(payload)

                # Если результат один, возвращаем строку, иначе список строк
                if isinstance(predictions, list) and len(predictions) == 1:
                    predictions = predictions[0]

                # response_obj = {"predictions": predictions}
                body = json.dumps(predictions).encode()

                await self.publisher.publish_rpc_response(
                    body=body,
                    correlation_id=message.correlation_id,
                    reply_to=message.reply_to
                )
                logger.info(f"[{self.worker_id}] RPC-ответ успешно отправлен")

            except Exception as e:
                logger.error(f"[{self.worker_id}] Ошибка при обработке RPC запроса: {e}")
                try:
                    error_obj = {"error": str(e)}
                    await self.publisher.publish_rpc_response(
                        body=json.dumps(error_obj).encode(),
                        correlation_id=message.correlation_id,
                        reply_to=message.reply_to
                    )
                except Exception as send_err:
                    logger.critical(
                        f"[{self.worker_id}] Не удалось отправить сообщение об ошибке: {send_err}",
                        exc_info=True
                    )
                    raise send_err from e

