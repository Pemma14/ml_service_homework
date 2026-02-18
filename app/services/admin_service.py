from decimal import Decimal
from typing import List
import logging

from sqlalchemy.orm import Session
from app.crud import user as user_crud
from app.crud import billing as billing_crud
from app.crud import admin as admin_crud
from app.crud import ml as ml_crud
from app.models import Transaction, TransactionStatus, TransactionType, User, MLRequest
from app.schemas.user_schemas import SUserAdminUpdate
from app.utils import TransactionNotFoundException, UserIsNotPresentException, transactional

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all_users(self) -> List[User]:
        return admin_crud.get_all_users(self.session)

    def get_all_transactions(self) -> List[Transaction]:
        return admin_crud.get_all_transactions(self.session)

    def get_all_requests(self) -> List[MLRequest]:
        return admin_crud.get_all_requests(self.session)

    @transactional
    def admin_replenish(self, user_id: int, amount: Decimal) -> Transaction:
        ok = billing_crud.update_user_balance(self.session, user_id, amount)
        if not ok:
            raise UserIsNotPresentException

        return billing_crud.create_transaction_record(
            session=self.session,
            user_id=user_id,
            amount=amount,
            type=TransactionType.replenish,
            status=TransactionStatus.approved,
            description="Пополнение баланса (Администратор)"
        )

    @transactional
    def update_user(self, user_id: int, user_update: SUserAdminUpdate) -> User:
        user = user_crud.get_by_id(self.session, user_id)
        if not user:
            raise UserIsNotPresentException

        update_data = user_update.model_dump(exclude_unset=True)
        user_crud.update(self.session, user, update_data)
        return user

    def get_user_transactions(self, user_id: int) -> List[Transaction]:
        return billing_crud.get_by_user_id(self.session, user_id)
