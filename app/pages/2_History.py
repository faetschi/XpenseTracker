import streamlit as st
import pandas as pd
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency

st.set_page_config(page_title="History", page_icon="📜", layout="wide")

st.title("📜 Transaction History")

db = next(get_db())
expenses = ExpenseService.get_expenses(db, limit=1000)

if expenses:
    # Convert to DataFrame for easier display
    data = [
        {
            "ID": e.id,
            "Date": e.date,
            "Category": e.category,
            "Description": e.description,
            "Amount": float(e.amount),
            "Currency": e.currency,
            "EUR Amount": float(e.amount_eur),
            "Verified": e.is_verified
        }
        for e in expenses
    ]
    df = pd.DataFrame(data)
    
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No transactions found.")
