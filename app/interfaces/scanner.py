from abc import ABC, abstractmethod
from app.schemas.expense import ExpenseCreate

class ReceiptScanner(ABC):
    @abstractmethod
    def scan_receipt(self, image_path: str) -> ExpenseCreate:
        """
        Scans a receipt image and returns an ExpenseCreate schema.
        """
        pass
