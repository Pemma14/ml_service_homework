from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

class MLTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    features: Any
    model: str
    user_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
