"""Pydantic models describing API payloads."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ExpenseBase(BaseModel):
    date: date
    type: str = "expense"
    category: str
    description: Optional[str] = None
    amount: Decimal
    currency: str = "EUR"


class ExpenseCreate(ExpenseBase):
    amount_eur: Optional[Decimal] = None
    exchange_rate: Decimal = Decimal("1.0")
    receipt_image_path: Optional[str] = None
    is_verified: bool = False


class Expense(ExpenseBase):
    id: int
    amount_eur: Decimal
    exchange_rate: Decimal
    receipt_image_path: Optional[str]
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "ExpenseBase",
    "ExpenseCreate",
    "Expense",
]
