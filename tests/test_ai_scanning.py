import pytest
import os
import io
import asyncio
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date

from app.services.receipt_service import ReceiptService
from app.services.expense_service import ExpenseService
from app.core.config import settings
from app.db.schemas import ExpenseCreate

# Path to test receipts
TEST_RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), 'test_receipts')

def run_async(coro):
    """Helper to run async code in sync tests if pytest-asyncio is missing"""
    return asyncio.run(coro)

def test_ai_scanning_with_testing_provider():
    """
    Test the receipt scanning pipeline using the 'testing' provider (stub).
    This ensures the service logic works without calling external APIs.
    """
    # Force the provider to 'testing'
    original_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "testing"
    
    try:
        # Get list of test files
        if not os.path.exists(TEST_RECEIPTS_DIR):
            pytest.skip(f"Test receipts directory not found: {TEST_RECEIPTS_DIR}")
            
        test_files = [f for f in os.listdir(TEST_RECEIPTS_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.heic'))]
        
        if not test_files:
            pytest.skip("No test receipts found in tests/test_receipts")

        for filename in test_files:
            print(f"Testing file: {filename}")
            file_path = os.path.join(TEST_RECEIPTS_DIR, filename)
            
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
                
            # Process receipt
            file_obj = io.BytesIO(content)
            
            # Run the async method
            result, saved_path = run_async(ReceiptService.process_receipt(file_obj, filename))
            
            # Assertions
            assert isinstance(result, ExpenseCreate)
            assert result.amount is not None
            assert result.category in settings.EXPENSE_CATEGORIES
            assert os.path.exists(saved_path)
            
            print(f"Successfully scanned {filename}: {result.description} - {result.amount} {result.currency}")
            
            # Cleanup the saved file in uploads/
            if os.path.exists(saved_path):
                os.remove(saved_path)
                
    finally:
        # Restore setting
        settings.AI_PROVIDER = original_provider

def test_create_expense_from_scan_result():
    """
    Test that the result from the scanner can be saved to the database.
    """
    # Mock DB Session
    mock_db = MagicMock(spec=Session)
    
    # Create a sample result (like what the scanner returns)
    scan_result = ExpenseCreate(
        date=date.today(),
        category="Lebensmittel",
        description="Test Receipt",
        amount=Decimal("10.00"),
        currency="EUR",
        receipt_image_path="uploads/test.jpg"
    )
    
    # Call service
    created_expense = ExpenseService.create_expense(mock_db, scan_result)
    
    # Verify DB interactions
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    
    # Verify attributes
    assert created_expense.amount == Decimal("10.00")
    assert created_expense.amount_eur == Decimal("10.00") # Logic in service
    assert created_expense.description == "Test Receipt"
