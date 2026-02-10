import asyncio
import logging
from typing import Optional
import aio_pika
from ml_worker.config import settings

logger = logging.getLogger("BaseWorker")

class BaseWorker:
    """
    Базовый класс для воркеров RabbitMQ.
    Обеспечивает подключение и прослушивание очереди.
    """
    def __init__(self, worker_id: str, queue_name: str, amqp_url: str) -> None:
        self.worker_id = worker_id
        self.queue_name = queue_name
        self.amqp_url = amqp_url
        self.connection: Optional[aio_pika.RobustConnection] = None
        self._stop_event = asyncio.Event()

    async def stop(self) -> None:
        """Остановка воркера."""
        logger.info(f"[{self.worker_id}] Остановка воркера...")
        self._stop_event.set()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def connect(self) -> None:
        """Установка устойчивого соединения с RabbitMQ."""
        logger.info(f"[{self.worker_id}] Подключение к RabbitMQ...")
        while not self.connection or self.connection.is_closed:
            try:
                self.connection = await aio_pika.connect_robust(self.amqp_url)
                logger.info(f"[{self.worker_id}] Соединение установлено.")
            except Exception as e:
                logger.warning(f"[{self.worker_id}] Ошибка подключения, повтор через 5 сек... ({e})")
                await asyncio.sleep(5)

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Метод для переопределения в подклассах."""
        raise NotImplementedError

    async def run(self) -> None:
        """Запуск цикла прослушивания очереди."""
        await self.connect()
        async with self.connection:
            channel = await self.connection.channel()
            await channel.set_qos(prefetch_count=settings.worker.PREFETCH_COUNT)

            queue = await channel.declare_queue(self.queue_name, durable=True)
            logger.info(f"[{self.worker_id}] Ожидание сообщений в очереди '{self.queue_name}'...")

            await queue.consume(self.process_message)

            await self._stop_event.wait()
