import streamlit as st
from datetime import date
from decimal import Decimal
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.services.llm_factory import LLMFactory
from app.schemas.expense import ExpenseCreate
import os

st.set_page_config(page_title="Add Expense", page_icon="➕")

st.title("➕ Add New Expense")

tab1, tab2 = st.tabs(["📸 Upload Receipt (AI)", "✍️ Manual Entry"])

db = next(get_db())

# --- TAB 1: AI Upload ---
with tab1:
    st.header("Upload Receipt")
    uploaded_file = st.file_uploader("Choose a receipt image", type=["jpg", "jpeg", "png"])
    
    if "ai_data" not in st.session_state:
        st.session_state.ai_data = None

    if uploaded_file is not None:
        # Save temp file
        # Ensure uploads dir exists
        os.makedirs("uploads", exist_ok=True)
        file_path = os.path.join("uploads", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        col_img, col_form = st.columns([1, 1])
        
        with col_img:
            st.image(uploaded_file, caption="Uploaded Receipt", use_container_width=True)
            if st.button("🤖 Analyze Receipt", type="primary"):
                with st.spinner("AI is analyzing your receipt..."):
                    try:
                        scanner = LLMFactory.get_scanner()
                        st.session_state.ai_data = scanner.scan_receipt(file_path)
                        st.success("Analysis Complete!")
                    except Exception as e:
                        st.error(f"AI Analysis Failed: {e}")

        with col_form:
            if st.session_state.ai_data:
                st.subheader("Review & Save")
                with st.form("ai_form"):
                    # Pre-fill form with AI data
                    date_val = st.date_input("Date", value=st.session_state.ai_data.date)
                    category = st.text_input("Category", value=st.session_state.ai_data.category)
                    description = st.text_input("Description", value=st.session_state.ai_data.description)
                    amount = st.number_input("Amount", value=float(st.session_state.ai_data.amount), step=0.01)
                    currency = st.text_input("Currency", value=st.session_state.ai_data.currency)
                    
                    submitted = st.form_submit_button("💾 Save to Database")
                    
                    if submitted:
                        # Re-create schema from form data
                        expense_in = ExpenseCreate(
                            date=date_val,
                            category=category,
                            description=description,
                            amount=Decimal(str(amount)),
                            currency=currency,
                            amount_eur=Decimal(str(amount)), # No conversion
                            exchange_rate=Decimal("1.0"),
                            receipt_image_path=file_path,
                            is_verified=True
                        )
                        
                        ExpenseService.create_expense(db, expense_in)
                        st.success("Expense saved successfully!")
                        st.session_state.ai_data = None # Reset
                        # st.rerun() # Optional

# --- TAB 2: Manual Entry ---
with tab2:
    st.header("Manual Entry")
    with st.form("manual_form"):
        date_val = st.date_input("Date", value=date.today())
        category = st.selectbox("Category", ["Groceries", "Dining Out", "Transport", "Shopping", "Utilities", "Travel", "Other"])
        description = st.text_input("Description")
        col_amt, col_curr = st.columns([2, 1])
        with col_amt:
            amount = st.number_input("Amount", min_value=0.0, step=0.01)
        with col_curr:
            currency = st.selectbox("Currency", ["EUR", "USD", "GBP", "KRW", "JPY"])
        
        submitted = st.form_submit_button("Add Expense")
        
        if submitted:
            amount_dec = Decimal(str(amount))
            
            expense_in = ExpenseCreate(
                date=date_val,
                category=category,
                description=description,
                amount=amount_dec,
                currency=currency,
                amount_eur=amount_dec, # No conversion
                exchange_rate=Decimal("1.0"),
                is_verified=True
            )
            ExpenseService.create_expense(db, expense_in)
            st.success("Expense added!")
