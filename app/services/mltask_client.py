import logging
import aio_pika
import asyncio
import uuid
from typing import Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import Request
from aio_pika.pool import Pool
from app.config import settings
from app.schemas.ml_task_schemas import MLTask
from app.utils import MQServiceException

logger = logging.getLogger(__name__)

class MLTaskPublisher:
    """
    Клиент для взаимодействия с RabbitMQ.
    - Использует пулы соединений и каналов
    - Объявляет Exchange и Queue
    - Использует настраиваемые ретраи
    """
    def __init__(self, connection_pool: Pool[aio_pika.RobustConnection]) -> None:
        self.connection_pool = connection_pool
        self.channel_pool: Pool[aio_pika.RobustChannel] = Pool(
            self._get_channel,
            max_size=10
        )
        self._infrastructure_ready: bool = False

    async def _get_channel(self) -> aio_pika.RobustChannel:
        async with self.connection_pool.acquire() as connection:
            return await connection.channel(publisher_confirms=True)

    async def ensure_infrastructure(self) -> None:
        """
        Гарантирует, что Exchange объявлен и привязан к очереди.
        """
        if self._infrastructure_ready:
            return

        async with self.channel_pool.acquire() as channel:
            # Объявляем обменник (Exchange)
            exchange = await channel.declare_exchange(
                settings.mq.EXCHANGE_NAME,
                type=aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            # Объявляем очередь
            queue = await channel.declare_queue(
                settings.mq.QUEUE_NAME,
                durable=True
            )
            # Привязываем очередь к обменнику
            await queue.bind(exchange, routing_key=settings.mq.QUEUE_NAME)

            self._infrastructure_ready = True
            logger.info("RabbitMQ infrastructure (Exchange/Queue) ensured")

    @retry(
        stop=stop_after_attempt(settings.mq.RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=settings.mq.RETRY_MULTIPLIER,
            min=settings.mq.RETRY_MIN,
            max=settings.mq.RETRY_MAX
        ),
        reraise=True
    )
    async def _publish_with_retry(self, message: aio_pika.Message) -> None:
        """
        Внутренний метод для публикации с ретраями через пул каналов.
        """
        async with self.channel_pool.acquire() as channel:
            exchange = await channel.get_exchange(settings.mq.EXCHANGE_NAME)
            await exchange.publish(
                message,
                routing_key=settings.mq.QUEUE_NAME,
                mandatory=True
            )

    async def send_task(self, task: MLTask) -> None:
        """
        Отправляет ML задачу в RabbitMQ.
        """
        try:
            await self.ensure_infrastructure()

            message = aio_pika.Message(
                body=task.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                message_id=task.task_id,
                app_id=settings.app.NAME,
                timestamp=task.timestamp,
                headers={"user_id": task.user_id}
            )

            await self._publish_with_retry(message)
            logger.info(f"Задача {task.task_id} успешно отправлена в RabbitMQ")

        except aio_pika.exceptions.AMQPError as e:
            logger.error(f"Ошибка RabbitMQ при отправке задачи: {e}")
            raise MQServiceException()
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при отправке задачи в RabbitMQ: {e}")
            raise MQServiceException()

    async def close(self) -> None:
        """
        Закрывает пулы.
        """
        await self.channel_pool.close()

class RPCPublisher:
    def __init__(self, connection_pool: Pool[aio_pika.RobustConnection]) -> None:
        self.connection_pool = connection_pool
        self.futures: Dict[str, asyncio.Future] = {}
        self._callback_queue: Optional[aio_pika.abc.AbstractRobustQueue] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
        self._loop = asyncio.get_event_loop()

    async def _get_channel(self) -> aio_pika.RobustChannel:
        async with self.connection_pool.acquire() as connection:
            return await connection.channel()

    async def ensure_ready(self) -> None:
        """
        Подготавливает канал и очередь для ответов.
        """
        if self._channel and not self._channel.is_closed:
            return

        async with self.connection_pool.acquire() as connection:
            self._channel = await connection.channel()
            self._callback_queue = await self._channel.declare_queue(
                exclusive=True,
                auto_delete=True
            )
            await self._callback_queue.consume(self.on_response, no_ack=True)
            logger.info(f"RPC Client ready, callback queue: {self._callback_queue.name}")

    async def on_response(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """
        Обработчик ответов из callback очереди.
        """
        if message.correlation_id is None:
            logger.warning(f"Получено сообщение без correlation_id: {message!r}")
            return

        future = self.futures.pop(message.correlation_id, None)
        if future:
            future.set_result(message.body)

    async def call(self, payload: bytes, routing_key: str, timeout: float = 10.0) -> bytes:
        """
        Выполняет RPC запрос.
        """
        await self.ensure_ready()

        correlation_id = str(uuid.uuid4())
        future = self._loop.create_future()
        self.futures[correlation_id] = future

        await self._channel.default_exchange.publish(
            aio_pika.Message(
                payload,
                content_type="application/json",
                correlation_id=correlation_id,
                reply_to=self._callback_queue.name,
            ),
            routing_key=routing_key,
        )

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            await self.futures.pop(correlation_id, None)
            raise MQServiceException(f"RPC call timed out after {timeout}s")
        finally:
            self.futures.pop(correlation_id, None)

    async def close(self) -> None:
        """
        Закрывает ресурсы клиента.
        """
        if self._channel:
            await self._channel.close()

def get_mq_service(request: Request) -> MLTaskPublisher:
    """
    Зависимость для получения сервиса RabbitMQ из состояния приложения.
    """
    mq_service = request.app.state.mq_service
    if mq_service is None:
        raise MQServiceException()
    return mq_service

def get_rpc_client(request: Request) -> RPCPublisher:
    """
    Зависимость для получения RPC клиента из состояния приложения.
    """
    rpc_client = request.app.state.rpc_client
    if rpc_client is None:
        raise MQServiceException()
    return rpc_client
