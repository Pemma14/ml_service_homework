import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import ml as ml_crud
from app.models import (
    User,
    MLRequest,
    MLRequestStatus,
)
from app.schemas.ml_task_schemas import MLTask, MLResult
from app.services.billing_service import BillingService
from app.services.mltask_client import MLTaskPublisher, RPCPublisher
from app.utils import (
    MLModelNotFoundException,
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

    def _prepare_input_data(self, input_data: Any) -> Any:
        if isinstance(input_data, list) and len(input_data) > 0 and isinstance(input_data[0], BaseModel):
            return [item.model_dump(by_alias=True) for item in input_data]
        return input_data

    #Функция для создания запроса (выбор модели, резервирвоание кредитов, создание записи в БД)
    def create_pending_request(
        self,
        user: User,
        input_data: List[Dict[str, Any]]
    ) -> MLRequest:
        logger.info(f"Создание запроса для пользователя {user.id}")

        model = ml_crud.get_active_model(self.session)
        if not model:
            raise MLModelNotFoundException

        total_cost = settings.app.DEFAULT_REQUEST_COST
        logger.info(f"Стоимость запроса: {total_cost}")

        self.billing_service.reserve_funds(user, total_cost)

        new_request = ml_crud.create_request_record(session=self.session, user_id=user.id, model_id=model.id,
                                                    cost=total_cost, input_data=input_data,
                                                    status=MLRequestStatus.pending)

        self.billing_service.record_payment_audit(
            user_id=user.id,
            cost=total_cost,
            description=f"Оплата ML-запроса №{new_request.id} (ожидание)",
            ml_request_id=new_request.id
        )

        return new_request

    #Функция для создания MLтаски из запроса
    def _build_ml_task(self, db_request: MLRequest, features: Any, user_id: int) -> MLTask:
        # Берем первый элемент из списка признаков, если API прислал список
        feat_data = features[0] if isinstance(features, list) and len(features) > 0 else features

        return MLTask(
            task_id=str(db_request.id),
            features=feat_data,
            model=db_request.ml_model.code_name,
            user_id=user_id,
        )

    #Откатить запись в БД и резервирование кредитов в случае ошибки
    def _handle_mq_error(self, request_id: int) -> None:
        logger.error(f"Не удалось отправить задачу {request_id} в RabbitMQ")
        self.session.rollback()
        raise MQServiceException()

    @transactional
    async def create_and_send_task(
        self,
        user: User,
        input_data: Any,
        mq_service: MLTaskPublisher,
    ) -> MLRequest:
        """
        Полный цикл: создание запроса, формирование из него таски и отправка в MQ.
        """
        # 1. Подготавливаем данные
        prepared_data = self._prepare_input_data(input_data)

        # 2. Создаём запрос
        db_request = self.create_pending_request(user, prepared_data)

        # 3. Формируем MLтакску из запроса для MQ
        task = self._build_ml_task(db_request, prepared_data, user.id)

        # 4. Отправляем в очередь (теперь выбрасывает MQServiceException при ошибке)
        await mq_service.send_task(task)

        # 5. Оповещаем пользователя
        self.session.refresh(db_request)

        db_request.is_published = True
        db_request.message = "Запрос принят и находится в обработке"
        return db_request

    async def execute_rpc_predict(
        self,
        input_data: Any,
        rpc_client: RPCPublisher,
    ) -> Any:
        import json
        # 1. Подготавливаем данные
        prepared_data = self._prepare_input_data(input_data)

        # 2. Делаем RPC вызов
        payload = json.dumps(prepared_data).encode()
        response_bytes = await rpc_client.call(
            payload,
            routing_key=settings.mq.RPC_QUEUE_NAME,
            timeout=15.0
        )

        # 3. Возвращаем результат
        return json.loads(response_bytes)

    @transactional
    async def process_task_result(self, result: MLResult) -> Dict[str, str]:
        """
        Обрабатывает результат выполнения задачи от воркера.
        """
        status_enum = MLRequestStatus.success if result.status == "success" else MLRequestStatus.fail
        errors = [{"error": result.error}] if result.error else None

        self.update_request_result(
            request_id=int(result.task_id),
            status=status_enum,
            prediction=result.prediction,
            errors=errors
        )
        return {"message": "Результат успешно сохранен"}

    def update_request_result(self, request_id: int, status: MLRequestStatus, prediction: Any = None,
                              errors: Any = None) -> MLRequest:

        db_request = ml_crud.update_request(
            self.session,
            request_id,
            status=status,
            prediction=prediction,
            errors=errors,
            completed_at=datetime.now(timezone.utc)
        )

        if not db_request:
            raise MLRequestNotFoundException

        if status == MLRequestStatus.fail:
            user = self.session.get(User, db_request.user_id)
            if user:
                self.billing_service.refund_funds(user, db_request.cost, reason=f"Ошибка выполнения запроса №{request_id}")

        return db_request

    def get_all_history(self, user_id: int) -> List[MLRequest]:
        return ml_crud.get_history(self.session, user_id)

    def get_history_by_id(self, request_id: int, user_id: int) -> Optional[MLRequest]:
        return ml_crud.get_request_by_id(self.session, request_id, user_id)

    @transactional
    def create_request_history(
        self,
        user: User,
        model_id: int,
        cost: Decimal,
        input_data: List[Any],
        predictions: Optional[List[Any]] = None,
        errors: Optional[List[Any]] = None,
        status: MLRequestStatus = MLRequestStatus.success,
    ) -> MLRequest:
        """
        Создает запись в истории ML-запросов и соответствующую транзакцию оплаты.
        """
        # 1. Создаем запись в истории ML-запросов
        new_request = ml_crud.create_request_record(
            session=self.session,
            user_id=user.id,
            model_id=model_id,
            cost=cost,
            input_data=input_data,
            status=status,
        )
        new_request.prediction = predictions or []
        new_request.errors = errors or []
        new_request.completed_at = datetime.now(timezone.utc)

        # 2. Аудит платежа через биллинг-сервис
        self.billing_service.record_payment_audit(
            user_id=user.id,
            cost=cost,
            description=f"Оплата ML-запроса №{new_request.id}",
            ml_request_id=new_request.id,
        )

        logger.info(f"Запрос №{new_request.id} сохранен в истории для пользователя {user.id}.")
        return new_request
