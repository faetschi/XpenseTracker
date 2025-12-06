# XpenseTracker 💰

A self-hosted, Python-based expense and income tracking application with AI receipt scanning.

## Features
- **Modern UI**: Built with the web-based NiceGUI framework.
- **Financial Dashboard**: Overview of your income, expenses, balance, and savings rate with interactive charts.
- **AI Receipt Scanning**: Upload a receipt and let AI extract the details automatically.
- **Income & Expense Tracking**: Log both earnings and spendings.
- **Transaction History**: View all your transactions with inline editing capabilities.

## Tech Stack
- **Frontend**: NiceGUI
- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: PostgreSQL
- **AI**: Google Gemini API / OpenAI API

## Setup

1.  **Clone the repository**.
2.  **Configure Environment**:
    - Rename `.env.example` to `.env` and and fill the content & API keys.

3.  **Run with Docker**:
    ```bash
    docker compose up --build
    ```
4.  **Access the App**:
    - Open your browser and go to `http://localhost:8501`.