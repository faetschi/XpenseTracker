from nicegui import ui
import plotly.express as px
import pandas as pd
from datetime import date
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency
from app.core.config import settings
from app.ui.layout import theme

def dashboard_page():
    theme()
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6'):
        # Header Row with Date Filters
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('💰 XpenseTracker Dashboard').classes('text-2xl font-bold text-gray-800')
            
            # Date Filter Controls
            current_year = date.today().year
            current_month = date.today().month
            
            with ui.row().classes('gap-2'):
                year_select = ui.select(
                    options=[current_year - i for i in range(settings.DASHBOARD_YEARS_LOOKBACK)], 
                    value=current_year, 
                    label="Year"
                ).classes('w-24')
                
                month_select = ui.select(
                    options={i: date(2000, i, 1).strftime('%B') for i in range(1, 13)}, 
                    value=current_month, 
                    label="Month"
                ).classes('w-32')
                
                # "All Year" toggle (clears month)
                def toggle_month(e):
                    if e.value:
                        month_select.disable()
                        month_select.value = None
                    else:
                        month_select.enable()
                        month_select.value = current_month
                        
                all_year_switch = ui.switch('Whole Year', on_change=toggle_month)

        # Content Container (to be refreshed)
        content = ui.column().classes('w-full gap-6')

        def refresh_dashboard():
            content.clear()
            
            selected_year = year_select.value
            selected_month = month_select.value if not all_year_switch.value else None
            
            db = next(get_db())
            try:
                stats = ExpenseService.get_stats(db, year=selected_year, month=selected_month)
                expenses = ExpenseService.get_expenses(db, limit=5) # Recent transactions stay global for now
            finally:
                db.close()

            with content:
                # Metrics Row
                with ui.row().classes('w-full gap-4'):
                    # Total Spent Card
                    label_text = f"Total Spent ({'All Year' if not selected_month else date(2000, selected_month, 1).strftime('%B')})"
                    with ui.card().classes('flex-1 p-4 border-l-4 border-blue-500 shadow-sm'):
                        ui.label(label_text).classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(format_currency(stats["total_spent"])).classes('text-3xl font-bold text-gray-800')
                    
                    # Top Category Card
                    with ui.card().classes('flex-1 p-4 border-l-4 border-pink-500 shadow-sm'):
                        ui.label('Top Category').classes('text-gray-500 text-sm uppercase tracking-wide')
                        if stats["by_category"]:
                            top_cat = max(stats["by_category"], key=stats["by_category"].get)
                            amount = stats['by_category'][top_cat]
                            ui.label(f"{top_cat}").classes('text-3xl font-bold text-gray-800')
                            ui.label(format_currency(amount)).classes('text-sm text-gray-500')
                        else:
                            ui.label('N/A').classes('text-3xl font-bold text-gray-800')

                # Chart & Recent Transactions
                with ui.row().classes('w-full gap-6'):
                    # Chart
                    with ui.card().classes('w-full md:w-1/2 p-6 shadow-sm'):
                        ui.label('Expenses by Category').classes('text-lg font-bold mb-4 text-gray-700')
                        if stats["by_category"]:
                            df = pd.DataFrame(list(stats["by_category"].items()), columns=["Category", "Amount"])
                            fig = px.pie(df, values="Amount", names="Category", hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300, showlegend=True)
                            ui.plotly(fig).classes('w-full h-80')
                        else:
                            ui.label('No data available for this period.').classes('text-gray-400 italic')

                    # Recent Transactions
                    with ui.card().classes('w-full md:w-1/2 p-6 shadow-sm'):
                        ui.label('Recent Transactions').classes('text-lg font-bold mb-4 text-gray-700')
                        if expenses:
                            columns = [
                                {'name': 'date', 'label': 'Date', 'field': 'date', 'align': 'left'},
                                {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left'},
                                {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'align': 'right'},
                            ]
                            rows = [
                                {
                                    'date': e.date.strftime('%Y-%m-%d'),
                                    'category': e.category,
                                    'amount': format_currency(e.amount_eur)
                                } for e in expenses
                            ]
                            ui.table(columns=columns, rows=rows, pagination=None).classes('w-full')
                        else:
                            ui.label('No transactions yet.').classes('text-gray-400 italic')

        # Bind refresh to filters
        year_select.on_value_change(refresh_dashboard)
        month_select.on_value_change(refresh_dashboard)
        all_year_switch.on_value_change(refresh_dashboard)
        
        # Initial Load
        refresh_dashboard()
