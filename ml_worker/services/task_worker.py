import json
import logging
import asyncio
from typing import Any, Optional

import aio_pika

from ml_worker.config import settings
from ml_worker.services.mq_consumer import BaseWorker
from ml_worker.schemas.tasks import MLTask
from ml_worker.services.mq_publisher import MQResultPublisher
from ml_worker.engine import ml_engine

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
        self._publisher = None

    @property
    def publisher(self) -> MQResultPublisher:
        if self._publisher is None:
            self._publisher = MQResultPublisher(self.connection, self.worker_id)
        return self._publisher

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

            # 2. Отправка результата
            await self.publisher.publish_result(task.task_id, prediction, status, error_msg)


#    async def save_result_to_db(self, task_id: str, prediction: Optional[Any], status: str, error: Optional[str]) -> None:
#        """Сохранение результата напрямую в БД."""
#        try:
#            # Валидация ID задачи
#            try:
#                request_id = int(task_id)
#            except ValueError:
#                logger.error(f"[{self.worker_id}] Некорректный ID задачи: {task_id}")
#                return
#
#            e_val = json.dumps([{'error': error}]) if error else None
#
#            with self.engine.begin() as conn:
#                query = text("""
#                    UPDATE ml_request
#                    SET prediction = :p, status = :s, errors = :e, completed_at = :c
#                    WHERE id = :id
#                """)
#                result = conn.execute(query, {
#                    'p': json.dumps(prediction),
#                    's': status,
#                    'e': e_val,
#                    'c': datetime.now(timezone.utc),
#                    'id': request_id
#                })
#
#                if result.rowcount == 0:
#                    logger.warning(f"[{self.worker_id}] Запись для задачи {request_id} не найдена в БД")
#                else:
#                    logger.info(f"[{self.worker_id}] Результат задачи {request_id} сохранен в БД")
#
#        except Exception as e:
#            logger.error(f"[{self.worker_id}] Ошибка при сохранении в БД: {e}")
#            raise
