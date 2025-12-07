from datetime import date
from decimal import Decimal
import time
from app.interfaces.scanner import ReceiptScanner
from app.schemas.expense import ExpenseCreate
from app.utils.logger import get_logger
from app.core.config import settings

"""
Testing scanner adapter for simulating receipt scanning during development and testing
without calling actual AI services (& save costs).
"""

class TestingScanner(ReceiptScanner):
    
    logger = get_logger(__name__)
    
    def scan_receipt(self, image_path: str) -> ExpenseCreate:
        # Simulate processing delay
        time.sleep(1.5)
        
        # Debugging logger level
        # print(f"Logger Level: {self.logger.getEffectiveLevel()}, Config Level: {settings.LOG_LEVEL}")
        
        self.logger.info(f"Simulating receipt scan for image: {image_path}")
        
        return ExpenseCreate(
            date=date.today(),
            category="Lebensmittel",
            description="Test Receipt (Billa)",
            amount=Decimal("25.99"),
            currency="EUR",
            amount_eur=Decimal("25.99"),
            exchange_rate=Decimal("1.0"),
            receipt_image_path=image_path,
            is_verified=False
        )
