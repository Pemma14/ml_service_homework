import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.crud import ml as ml_crud
from app.models import (
    User,
    MLRequest,
    MLRequestStatus,
)
from app.schemas.ml_task_schemas import MLResult
from app.services.billing_service import BillingService
from app.services.ml_service_helpers import (
    prepare_input_data,
    build_ml_task,
    create_pending_request,
    update_request_result
)
from app.services.mq_publisher import MLTaskPublisher, RPCPublisher
from app.utils import (
    MLRequestNotFoundException,
    MQServiceException,
    transactional,
)

# Настроим логгер
logger = logging.getLogger(__name__)


class MLRequestService:
    def __init__(self, session: Session):
        self.session = session
        self.billing_service = BillingService(session)

    #Подготовка и отправка таски в RabbitMQ
    @transactional
    async def create_and_send_task(
        self,
        user: User,
        input_data: Any,
        mq_service: MLTaskPublisher,
    ) -> MLRequest:

        # 1. Подготавливаем данные
        prepared_data = prepare_input_data(input_data)

        # 2. Создаём запрос
        db_request = create_pending_request(self.session, self.billing_service, user, prepared_data)

        # 3. Формируем MLтаску из запроса
        task = build_ml_task(db_request, prepared_data, user.id)

        # 4. Отправляем в очередь
        await mq_service.send_task(task)

        # 5. Оповещаем пользователя
        self.session.refresh(db_request)

        db_request.is_published = True
        db_request.message = "Запрос принят и находится в обработке"
        return db_request

#Подготовка и возврат ответа клиенту из RabbitMQ
    @transactional
    async def process_and_post_result(self, result: MLResult) -> Dict[str, str]:
        request_id = int(result.task_id)
        db_request = ml_crud.get_request_by_id(self.session, request_id)

        if not db_request:
            raise MLRequestNotFoundException

        if db_request.status != MLRequestStatus.pending:
            logger.warning(f"Запрос {request_id} уже обработан (статус: {db_request.status})")
            return {"message": "Результат уже был обработан ранее"}

        status_enum = MLRequestStatus.success if result.status == "success" else MLRequestStatus.fail
        errors = [{"error": result.error}] if result.error else None

        update_request_result(
            session=self.session,
            billing_service=self.billing_service,
            request_id=request_id,
            status=status_enum,
            prediction=result.prediction,
            errors=errors
        )
        return {"message": "Результат успешно сохранен"}

    #Выполнение rpc предсказания
    @transactional
    async def execute_rpc_predict(
        self,
        user: User,
        input_data: Any,
        rpc_client: RPCPublisher,
    ) -> Any:
        import json
        # 1. Подготавливаем данные
        prepared_data = prepare_input_data(input_data)
        num_rows = len(prepared_data) if isinstance(prepared_data, list) else 1

        # 2. Создаем запрос и резервируем средства
        db_request = create_pending_request(self.session, self.billing_service, user, prepared_data)
        self.session.flush()

        # 3. Вычисляем динамический таймаут
        dynamic_timeout = max(15.0, 10.0 + (num_rows * 0.2))
        logger.info(f"Выполнение RPC-запроса №{db_request.id} для {num_rows} строк. Таймаут: {dynamic_timeout}с")

        # 4. Делаем RPC вызов
        payload = json.dumps(prepared_data).encode()
        try:
            response_bytes = await rpc_client.call(
                payload,
                routing_key=settings.mq.RPC_QUEUE_NAME,
                timeout=dynamic_timeout
            )
            prediction = json.loads(response_bytes)

            # 5. Обновляем результат (в той же транзакции)
            update_request_result(
                session=self.session,
                billing_service=self.billing_service,
                request_id=db_request.id,
                status=MLRequestStatus.success,
                prediction=prediction
            )
            return prediction
        except MQServiceException as e:
            e.request_id = str(db_request.id)
            raise e
        except Exception as e:
            raise e

    def get_all_history(self, user_id: int) -> List[MLRequest]:
        return ml_crud.get_history(self.session, user_id)

    def get_history_by_id(self, request_id: int, user_id: int) -> MLRequest:
        db_request = ml_crud.get_request_by_id(self.session, request_id, user_id)
        if not db_request:
            raise MLRequestNotFoundException
        return db_request

