from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Expense
from app.db.schemas import ExpenseCreate

class ExpenseService:
    @staticmethod
    def create_expense(db: Session, expense: ExpenseCreate) -> Expense:
        # Simplified Logic: No currency conversion. 
        # amount_eur is always equal to amount, and exchange_rate is always 1.0
        expense.amount_eur = expense.amount
        expense.exchange_rate = 1.0

        db_expense = Expense(
            date=expense.date,
            type=expense.type,
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
    def update_expense(db: Session, expense_id: int, updates: Dict[str, Any]) -> Any:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if expense:
            for key, value in updates.items():
                if hasattr(expense, key):
                    setattr(expense, key, value)
            
            # Recalculate amount_eur if amount changed
            if 'amount' in updates:
                expense.amount_eur = expense.amount
                
            db.commit()
            db.refresh(expense)
            return expense
        return None

    @staticmethod
    def delete_expense(db: Session, expense_id: int) -> bool:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if expense:
            db.delete(expense)
            db.commit()
            return True
        return False

    @staticmethod
    def get_expenses(db: Session, skip: int = 0, limit: int = 100) -> List[Expense]:
        return db.query(Expense).order_by(Expense.date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_stats(db: Session, year: int = None, month: int = None) -> Dict[str, Any]:
        query = db.query(Expense)
        
        if year:
            query = query.filter(func.extract('year', Expense.date) == year)
        if month:
            query = query.filter(func.extract('month', Expense.date) == month)
            
        total_spent = query.filter(Expense.type == 'expense').with_entities(func.sum(Expense.amount_eur)).scalar() or 0
        total_income = query.filter(Expense.type == 'income').with_entities(func.sum(Expense.amount_eur)).scalar() or 0
        
        category_stats = query.filter(Expense.type == 'expense').with_entities(
            Expense.category, func.sum(Expense.amount_eur)
        ).group_by(Expense.category).all()
        
        return {
            "total_spent": total_spent,
            "total_income": total_income,
            "balance": total_income - total_spent,
            "by_category": {cat: float(amt) for cat, amt in category_stats}
        }
