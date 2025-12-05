# XpenseTracker 💰

A self-hosted, Python-based expense tracking application with AI receipt scanning.

## Features
- **Dashboard**: Overview of your expenses with charts and metrics.
- **AI Receipt Scanning**: Upload a receipt and let AI extract the details.
- **Manual Entry**: Add expenses manually.
- **History**: View all your transactions.

## Tech Stack
- **Frontend**: Streamlit
- **Backend**: Python, SQLAlchemy
- **Database**: PostgreSQL
- **AI**: Google Gemini API / OpenAI API

## Setup

1.  **Clone the repository**.
2.  **Configure Environment**:
    - Create a `.env` file in the root directory.
    - Copy the following content into it and fill in your API keys:

        ```env
        # Database Configuration
        POSTGRES_USER=xpense
        POSTGRES_PASSWORD=xpense
        POSTGRES_DB=xpense
        POSTGRES_HOST=xpense-db
        POSTGRES_PORT=5432

        # AI Configuration
        AI_PROVIDER=openai  # Options: 'gemini' or 'openai'
        GOOGLE_API_KEY=your_gemini_key_here
        OPENAI_API_KEY=your_openai_key_here
        ```

3.  **Run with Docker**:
    ```bash
    docker-compose up --build
    ```
4.  **Access the App**:
    - Open your browser and go to `http://localhost:8501`.

## Development

- Install dependencies: `pip install -r requirements.txt`
- Run locally (requires local Postgres or port forwarding): `streamlit run app/main.py`
