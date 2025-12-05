

# XpenseTracker - Project Initiation Plan

## 1. Project Overview
**XpenseTracker** is a self-hosted, Python-based expense tracking application. It allows users to track monthly and yearly expenses through a web interface. It features dual-mode entry: manual input and AI-powered receipt scanning using the Google Gemini API.

## 2. Technology Stack
* **Language:** Python 3.11+.
* **Frontend/UI Framework:** Streamlit (Chosen for rapid UI development and native data visualization).
* **Database:** PostgreSQL (Robust, relational storage).
* **AI Engine:** Google Gemini API (`google-generativeai` library) for OCR and entity extraction.
* **Containerization:** Docker & Docker Compose.
* **ORM:** SQLAlchemy (Recommended for cleaner code and object mapping).
* **Data Validation:** Pydantic (Crucial for validating AI JSON outputs and form data).
* **Testing:** Pytest (For unit and integration testing).
* **Utilities:** `Pillow` (Image processing), `python-dotenv` (Configuration), `pandas` (Data manipulation for charts).

## 3. System Architecture

The system follows a **Service Layer Pattern** to decouple the UI from the database logic, ensuring scalability and testability.

**Containers:**
1.  **`xpense-app`**: Runs the Python Streamlit application.
2.  **`xpense-db`**: Runs the PostgreSQL database.

**Logical Flow:**
`Streamlit UI (Pages)` -> `Service Layer (Business Logic)` -> `Repository/ORM (Data Access)` -> `PostgreSQL`

## 4. Database Schema (PostgreSQL)
We need a robust schema to handle currencies and categorization. *Note: We will use SQLAlchemy's `Base.metadata.create_all()` for simple table creation on startup. Schema updates will be handled manually or via SQL scripts to keep deployment simple.*

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    amount DECIMAL(10, 2) NOT NULL, -- Original Amount
    currency VARCHAR(3) DEFAULT 'EUR', -- Original Currency
    amount_eur DECIMAL(10, 2) NOT NULL, -- Converted to Base Currency
    exchange_rate DECIMAL(10, 4) DEFAULT 1.0,
    receipt_image_path TEXT, -- Path to saved image in volume
    is_verified BOOLEAN DEFAULT FALSE, -- True if user confirmed AI data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. AI Integration Logic (Gemini)
The application will send the uploaded image to Gemini with a system prompt to enforce a specific JSON output structure.

**System Prompt Strategy:**

> "Analyze this receipt image. Extract the following fields in JSON format: 'date' (YYYY-MM-DD), 'total_amount' (float), 'currency' (ISO code), 'category' (guess based on items: Groceries, Dining Out, Transport, etc.), and 'description' (shop name). If the currency is not EUR, estimate the exchange rate to EUR based on the date, or return 1.0. Return ONLY the raw JSON string, no markdown formatting."

## 6. Directory Structure
Refactored for scalability and separation of concerns.

```text
XpenseTracker/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Streamlit Entry Point (Dashboard/Home)
│   ├── pages/                   # Streamlit Native Multi-Page Routing
│   │   ├── 1_Add_Expense.py     # Manual Entry & AI Upload UI
│   │   └── 2_History.py         # Data Table & Editing UI
│   │
│   ├── core/                    # App Configuration
│   │   ├── __init__.py
│   │   ├── config.py            # Env var loading (Pydantic Settings)
│   │   └── database.py          # DB Session setup & connection logic
│   │
│   ├── models/                  # SQLAlchemy ORM Models (Database Layer)
│   │   ├── __init__.py
│   │   └── expense.py           # The 'Expense' DB Table definition
│   │
│   ├── schemas/                 # Pydantic Models (Data Validation Layer)
│   │   ├── __init__.py
│   │   └── expense.py           # Schemas for AI output & UI forms
│   │
│   ├── services/                # Business Logic (Service Layer)
│   │   ├── __init__.py
│   │   ├── expense_service.py   # CRUD logic, stats calculations
│   │   └── ai_service.py        # Gemini interaction & JSON parsing
│   │
│   └── utils/                   # Shared Utilities
│       ├── __init__.py
│       └── formatting.py        # Currency formatting, date helpers
│
├── tests/                       # Pytest Suite
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures (DB session, etc.)
│   └── test_services.py         # Unit tests for logic
│
├── uploads/                     # Docker Volume for images
├── .env                         # Secrets (API Keys, DB Creds)
├── .gitignore
├── docker-compose.yaml
├── Dockerfile
└── requirements.txt             # Python dependencies
```

## 7. Implementation Roadmap
1.  **Environment Setup:** Create `docker-compose.yaml` and `Dockerfile`. Set up `core/config.py` and `core/database.py`.
2.  **Data Layer:** Define SQLAlchemy models in `models/` and Pydantic schemas in `schemas/`.
3.  **Service Layer:** Implement `services/expense_service.py` (CRUD) and `services/ai_service.py` (Gemini logic).
4.  **UI Skeleton:** Create `main.py` and `pages/` structure.
5.  **Feature - Manual Mode:** Connect `pages/1_Add_Expense.py` to `expense_service.create_expense`.
6.  **Feature - AI Mode:** Connect `pages/1_Add_Expense.py` to `ai_service.scan_receipt`.
7.  **Feature - Dashboard:** Implement charts in `main.py` using data from `expense_service.get_stats`.
8.  **Polishing:** Apply "Budget Lens" styling and run tests.