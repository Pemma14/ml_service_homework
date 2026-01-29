from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict, TYPE_CHECKING
from uuid import UUID, uuid4

from .base_model import BaseEntity

if TYPE_CHECKING:
    pass

class RequestStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "pending"
    SUCCESS = "success"
    ERROR = "fail"

@dataclass
class MLRequest(BaseEntity):
    user_id: UUID = field(default_factory=uuid4)
    input_data: Dict[str, Any] = field(default_factory=dict)
    prediction: Optional[Any] = None
    status: RequestStatus = RequestStatus.CREATED
    cost: float = 10.0
    error_message: Optional[str] = None

    def complete(self, result: Any):
        self.prediction = result
        self.status = RequestStatus.SUCCESS

    def fail(self, message: str):
        self.status = RequestStatus.ERROR
        self.error_message = message
