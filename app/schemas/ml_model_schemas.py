from typing import Optional
from app.schemas.base_schema import SBase

class SMLModel(SBase):
    id: int
    name: str
    code_name: str
    description: Optional[str] = None
    version: str
    is_active: bool
    cost: float

class SMLModelCreate(SBase):
    name: str
    code_name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    cost: float = 10.0
