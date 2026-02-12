from decimal import Decimal
import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.crud import billing as billing_crud

from app.config import settings
from app.models import (
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.utils import InsufficientFundsException, transactional, TransactionNotFoundException

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @transactional
    def create_replenishment(
        self,
        user: User,
        amount: Decimal
    ) -> Transaction:
        """
        Создаёт запрос на атомарное пополнение баланса.
        В DEV режиме транзакция сразу одобряется и баланс обновляется атомарно.
        В PROD режиме создается pending транзакция для последующего одобрения.

        """
        if settings.app.MODE == "DEV":
            return self._auto_approve_replenishment(user, amount)
        return self._create_pending_replenishment(user, amount)

    def _auto_approve_replenishment(self, user: User, amount: Decimal) -> Transaction:
        billing_crud.update_user_balance(self.session, user.id, amount)
        return billing_crud.create_transaction_record(
            session=self.session,
            user_id=user.id,
            amount=amount,
            type=TransactionType.replenish,
            status=TransactionStatus.approved,
            description="Пополнение баланса (DEV)"
        )

    def _create_pending_replenishment(self, user: User, amount: Decimal) -> Transaction:
        return billing_crud.create_transaction_record(
            session=self.session,
            user_id=user.id,
            amount=amount,
            type=TransactionType.replenish,
            status=TransactionStatus.pending,
            description="Пополнение баланса (ожидание)"
        )

    def get_user_balance(self, user_id: int) -> Decimal:
        query = select(User).where(User.id == user_id)
        result = self.session.execute(query)
        user = result.scalar_one_or_none()
        return user.balance if user else Decimal("0.0")

    def reserve_funds(
        self,
        user: User,
        cost: Decimal,
    ) -> None:
        """
        Атомарно списывает средства с баланса пользователя.

        """
        ok = billing_crud.update_user_balance(self.session, user.id, amount=-cost)
        if not ok:
            logger.error(f"Пользователь {user.id}: Недостаточно средств для списания {cost}")
            raise InsufficientFundsException

    def record_payment_audit(
        self,
        user_id: int,
        cost: Decimal,
        description: str,
        ml_request_id: int,
        status: TransactionStatus = TransactionStatus.approved,
    ) -> Transaction:
        """
        Создает запись в журнале финансовых транзакций для оплаты ML-запроса.
        Сумма записывается как отрицательная (списание).
        """
        return billing_crud.create_transaction_record(
            session=self.session,
            user_id=user_id,
            amount=-cost,
            type=TransactionType.payment,
            status=status,
            description=description,
            ml_request_id=ml_request_id,
        )

    def refund_funds(
        self,
        user: User,
        cost: Decimal,
        reason: str = "Возврат средств"
    ) -> None:
        billing_crud.update_user_balance(self.session, user.id, amount=cost)

        # Создаем транзакцию возврата для аудита
        billing_crud.create_transaction_record(
            session=self.session,
            user_id=user.id,
            amount=cost,
            type=TransactionType.replenish,
            status=TransactionStatus.approved,
            description=reason
        )
        logger.info(f"Средства {cost} подготовлены к возврату пользователю {user.id}. Причина: {reason}")

    def get_transactions_history(self, user_id: int) -> List[Transaction]:
        return billing_crud.get_by_user_id(self.session, user_id)

    def get_all_transactions(self) -> List[Transaction]:
        """Получить все транзакции в системе (Админ)."""
        return billing_crud.get_all(self.session)

    @transactional
    def admin_replenish(self, user_id: int, amount: Decimal) -> Transaction:
        """Прямое пополнение баланса пользователя администратором."""
        billing_crud.update_user_balance(self.session, user_id, amount)
        return billing_crud.create_transaction_record(
            session=self.session,
            user_id=user_id,
            amount=amount,
            type=TransactionType.replenish,
            status=TransactionStatus.approved,
            description="Пополнение баланса (Администратор)"
        )

    @transactional
    def approve_transaction(self, transaction_id: int) -> Transaction:
        """Одобрение ожидающей транзакции."""
        transaction = billing_crud.get_by_id(self.session, transaction_id)
        if not transaction:
            raise TransactionNotFoundException

        if transaction.status == TransactionStatus.pending:
            billing_crud.update_user_balance(self.session, transaction.user_id, transaction.amount)
            transaction.status = TransactionStatus.approved
            self.session.flush()
        return transaction

    @transactional
    def reject_transaction(self, transaction_id: int) -> Transaction:
        """Отклонение ожидающей транзакции."""
        transaction = billing_crud.get_by_id(self.session, transaction_id)
        if not transaction:
            raise TransactionNotFoundException

        if transaction.status == TransactionStatus.pending:
            transaction.status = TransactionStatus.rejected
            self.session.flush()
        return transaction
