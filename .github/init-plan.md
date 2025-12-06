# XpenseTracker - Project Initiation Plan

## 1. Project Overview
**XpenseTracker** is a self-hosted, Python-based expense tracking application. It allows users to track monthly and yearly expenses through a web interface. It features dual-mode entry: manual input and AI-powered receipt scanning using the Google Gemini API.

## 2. Technology Stack
* **Language:** Python 3.11+.
* **Frontend/UI Framework:** NiceGui (Vue.js/FastAPI based) - Chosen for full UI customization and modern look.
* **Database:** PostgreSQL (Robust, relational storage).
* **AI Engine:** Google Gemini API (`google-generativeai` library) for OCR and entity extraction.
* **Containerization:** Docker & Docker Compose.
* **ORM:** SQLAlchemy (Clean code & object mapping).
* **Data Validation:** Pydantic (Validating AI JSON outputs & form data).
* **Testing:** Pytest (Unit and integration testing).
* **Utilities:** `Pillow` (Image processing), `python-dotenv` (Configuration), `pandas` (Data manipulation for charts).

## 3. System Architecture

The system follows **Clean Architecture** principles to ensure the UI and AI components are replaceable.

**1. Service Layer Pattern (UI Decoupling):**
*   The **UI** (NiceGui) acts purely as a presentation layer. It captures input and displays output.
*   The **Service Layer** contains all business logic. It accepts Pydantic models and returns Pydantic models.
*   **Rule:** `app/services/` must NEVER import `nicegui`. This ensures we can swap the UI framework later without touching the logic.

**2. Strategy Pattern (AI Decoupling):**
*   We define an abstract interface `ReceiptScanner` (in `app/interfaces/`).
*   The `GeminiScanner` implements this interface.
*   The application depends on the *interface*, not the concrete class. This allows us to easily add an `OllamaScanner` or `OpenAIScanner` in the future by simply changing a config setting.

**Containers:**
1.  **`xpense-app`**: Runs the Python NiceGui application.
2.  **`xpense-db`**: Runs the PostgreSQL database.

**Logical Flow:**
`UI` -> `Service Layer` -> `AI Interface (Strategy)` -> `Gemini/Ollama Implementation`

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
│   ├── main.py                  # NiceGUI Entry Point & Routing
│   ├── ui/                      # UI Components & Pages
│   │   ├── __init__.py
│   │   ├── layout.py            # Common layout (sidebar, header)
│   │   ├── dashboard.py         # Dashboard Page
│   │   ├── add_expense.py       # Add Expense Page
│   │   └── history.py           # History Page
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
│   ├── interfaces/              # Abstract Base Classes (Contracts)
│   │   ├── __init__.py
│   │   └── scanner.py           # Defines the 'ReceiptScanner' interface
│   │
│   ├── services/                # Business Logic (Service Layer)
│   │   ├── __init__.py
│   │   ├── expense_service.py   # CRUD logic, stats calculations
│   │   └── llm_factory.py       # Returns the correct AI scanner based on config
│   │
│   ├── adapters/                # External System Implementations
│   │   ├── __init__.py
│   │   └── gemini_scanner.py    # Implements 'ReceiptScanner' using Google Gemini
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
3.  **AI Core:** Define the `ReceiptScanner` interface in `interfaces/`. Implement `GeminiScanner` in `adapters/`.
4.  **Service Layer:** Implement `services/expense_service.py` (CRUD) and `services/llm_factory.py`.
5.  **UI Skeleton:** Create `main.py` and `ui/` structure with NiceGUI routing.
6.  **Feature - Manual Mode:** Connect `ui/add_expense.py` to `expense_service.create_expense`.
7.  **Feature - AI Mode:** Connect `ui/add_expense.py` to `llm_factory.get_scanner().scan_receipt()`.
8.  **Feature - Dashboard:** Implement charts in `ui/dashboard.py` using data from `expense_service.get_stats`.
9.  **Polishing:** Apply "Budget Lens" styling using Tailwind CSS classes.