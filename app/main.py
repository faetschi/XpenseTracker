import streamlit as st
import plotly.express as px
import pandas as pd
from app.core.database import Base, engine, get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency

# Initialize DB tables
Base.metadata.create_all(bind=engine)

st.set_page_config(page_title="XpenseTracker", page_icon="💰", layout="wide")

st.title("💰 XpenseTracker Dashboard")

# Get DB session
db = next(get_db())

# Get Stats
stats = ExpenseService.get_stats(db)

# Metrics
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Spent (All Time)", format_currency(stats["total_spent"]))
with col2:
    if stats["by_category"]:
        top_category = max(stats["by_category"], key=stats["by_category"].get)
        st.metric("Top Category", f"{top_category} ({format_currency(stats['by_category'][top_category])})")
    else:
        st.metric("Top Category", "N/A")

# Charts
if stats["by_category"]:
    df = pd.DataFrame(list(stats["by_category"].items()), columns=["Category", "Amount"])
    fig = px.pie(df, values="Amount", names="Category", title="Expenses by Category", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No expenses found. Go to 'Add Expense' to get started!")

# Recent Transactions (Mini Table)
st.subheader("Recent Transactions")
expenses = ExpenseService.get_expenses(db, limit=5)
if expenses:
    data = [
        {
            "Date": e.date,
            "Category": e.category,
            "Description": e.description,
            "Amount": format_currency(e.amount, e.currency),
            "EUR Amount": format_currency(e.amount_eur)
        }
        for e in expenses
    ]
    st.dataframe(data, use_container_width=True)
