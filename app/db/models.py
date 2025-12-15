"""SQLAlchemy models for persistent data."""

from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, TIMESTAMP, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(20), default="expense", nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="EUR")
    amount_eur = Column(Numeric(10, 2), nullable=False)
    exchange_rate = Column(Numeric(10, 4), default=1.0)
    receipt_image_path = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


__all__ = ["Expense"]
