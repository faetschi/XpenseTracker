from pydantic import BaseModel
from datetime import date
from typing import Optional
from decimal import Decimal

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
    
    class Config:
        from_attributes = True
