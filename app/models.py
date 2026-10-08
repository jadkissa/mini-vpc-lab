from sqlalchemy import Column, Integer, DateTime, func
from database import Base

class VisitModel(Base):
    __tablename__="visits"

    id = Column(Integer, primary_key=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )