from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class VisitResponse(BaseModel):
    total: int
    last_visit: Optional[datetime] = None
    