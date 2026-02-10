from pydantic import BaseModel
from typing import Any, List, Optional

class MLResult(BaseModel):
    task_id: str
    prediction: Any = None
    worker_id: str
    status: str
    error: Optional[str] = None
