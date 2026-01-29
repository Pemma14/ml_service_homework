from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC
from uuid import UUID, uuid4

@dataclass
class BaseEntity(ABC):
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
