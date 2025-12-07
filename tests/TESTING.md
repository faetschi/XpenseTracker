# Tests

This directory contains the test suite for the **`XpenseTracker`** application. The tests are designed to verify the functionality of key components, particularly the AI receipt scanning pipeline and expense creation logic.

## Structure

- **`test_ai_scanning.py`**: <br>Contains tests for the AI scanning workflow.
    - `test_ai_scanning_with_testing_provider`: <br>Iterates through images in `test_receipts/`, processes them using the `TestingScanner` (stub), and asserts that valid `ExpenseCreate` objects are returned. This verifies the pipeline without making external API calls.
    - `test_create_expense_from_scan_result`: Verifies that a scanned result object can be successfully persisted to the database using `ExpenseService`.
- **`test_receipts/`**: <br>A directory containing sample receipt images (`.jpg`, `.png`, etc.) used by the tests. You can add more images here to test different formats or scenarios.

## Prerequisites

Ensure you have the project dependencies installed, including `pytest` and `pytest-asyncio`.

```bash
pip install -r requirements.txt
```

## Running Tests

You can run the tests using `pytest` from the root of the repository. Make sure to use the Python executable from your virtual environment (`.venv`).

### Windows (PowerShell)

```powershell
# Run all tests
& .venv/Scripts/python.exe -m pytest tests/

# Run a specific test file
& .venv/Scripts/python.exe -m pytest tests/test_ai_scanning.py

# Run with verbose output
& .venv/Scripts/python.exe -m pytest -v tests/
```

### Alternative (Activate venv first)

```powershell
# Activate
.venv/Scripts/Activate.ps1

# Run
python -m pytest tests/
```

## Adding New Tests

1.  Create a new test file (e.g., `test_new_feature.py`) or add to an existing one.
2.  Use the `TestingScanner` provider in `app.core.config.settings` if you want to avoid real API calls during testing.
3.  Place any required static assets (images, files) in a dedicated subdirectory (like `test_receipts/`).
