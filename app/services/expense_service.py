from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate
from typing import List, Dict, Any

class ExpenseService:
    @staticmethod
    def create_expense(db: Session, expense: ExpenseCreate) -> Expense:
        db_expense = Expense(
            date=expense.date,
            category=expense.category,
            description=expense.description,
            amount=expense.amount,
            currency=expense.currency,
            amount_eur=expense.amount_eur,
            exchange_rate=expense.exchange_rate,
            receipt_image_path=expense.receipt_image_path,
            is_verified=expense.is_verified
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        return db_expense

    @staticmethod
    def get_expenses(db: Session, skip: int = 0, limit: int = 100) -> List[Expense]:
        return db.query(Expense).order_by(Expense.date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        total_spent = db.query(func.sum(Expense.amount_eur)).scalar() or 0
        
        category_stats = db.query(
            Expense.category, func.sum(Expense.amount_eur)
        ).group_by(Expense.category).all()
        
        return {
            "total_spent": total_spent,
            "by_category": {cat: float(amt) for cat, amt in category_stats}
        }
