import asyncio

from nicegui import ui
from datetime import date
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency
from app.core.config import settings
from app.ui.layout import theme
from app.ui.charts import render_expenses_by_category_pie

def dashboard_page():
    theme('dashboard')
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6'):
        # Header
        ui.label('💰 XpenseTracker Dashboard').classes('text-2xl font-bold text-gray-800')
        
        # Filter Toolbar
        current_year = date.today().year
        current_month = date.today().month
        year_options = [current_year - i for i in range(settings.DASHBOARD_YEARS_LOOKBACK)]
        month_map = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }

        def change_month(delta):
            if not month_select.value:
                return
            new_val = month_select.value + delta
            if 1 <= new_val <= 12:
                month_select.value = new_val

        def toggle_month(e):
            if e.value:
                month_select.disable()
                btn_prev.disable()
                btn_next.disable()
                month_select.value = None
            else:
                month_select.enable()
                btn_prev.enable()
                btn_next.enable()
                month_select.value = current_month

        with ui.row().classes('filter-toolbar responsive-row w-full gap-3 p-3 bg-white rounded-lg shadow-sm border border-gray-200 items-start justify-start'):
            # Year Selector
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-start'):
                    year_select = ui.select(
                        options=year_options,
                        value=current_year,
                        label="Year"
                    ).props('outlined dense options-dense behavior="menu"').classes('filter-select px-1')
            # Month Selector
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-start flex-nowrap'):
                    btn_prev = ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round dense color=gray')
                    month_select = ui.select(
                        options=month_map,
                        value=current_month,
                        label="Month"
                    ).props('outlined dense options-dense behavior="menu"').classes('filter-select px-1')
                    btn_next = ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round dense color=gray')
            # Toggle Month
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-center md:justify-start flex-wrap'):
                    all_year_switch = (
                        ui.switch('Whole Year', on_change=toggle_month)
                        .classes('filter-input filter-switch px-1')
                        .style('margin-left: auto; margin-right: auto; display: flex; justify-content: center;')
                    )

        # Content Container (to be refreshed)
        content = ui.column().classes('w-full gap-6')

        def refresh_dashboard():
            content.clear()
            
            selected_year = year_select.value
            selected_month = month_select.value if not all_year_switch.value else None
            
            db = next(get_db())
            try:
                summary = ExpenseService.get_summary(db, year=selected_year, month=selected_month)
                expenses = ExpenseService.get_expenses(db, limit=5)  # Recent transactions stay global for now
            finally:
                db.close()

            with content:
                # Metrics Row
                with ui.row().classes('w-full gap-4 responsive-row'):
                    period_label = 'All Year' if not selected_month else date(2000, selected_month, 1).strftime('%B')
                    
                    # --- Income Card ---
                    with ui.card().classes('flex-1 w-full p-4 border-l-4 border-green-500 shadow-sm'):
                        ui.label(f"Income ({period_label})").classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(format_currency(summary["total_income"])).classes('text-3xl font-bold text-gray-800')

                    # --- Expenses Card ---
                    with ui.card().classes('flex-1 w-full p-4 border-l-4 border-red-500 shadow-sm'):
                        ui.label(f"Expenses ({period_label})").classes('text-gray-500 text-sm uppercase tracking-wide')
                        expenses_label = ui.label(format_currency(summary["total_spent"])).classes('text-3xl font-bold text-gray-800')

                    # --- Leftover-Balance Card ---
                    balance = summary["balance"]
                    color = 'green' if balance >= 0 else 'red'
                    with ui.card().classes(f'flex-1 w-full p-4 border-l-4 border-{color}-500 shadow-sm'):
                        ui.label(f"Leftover ({period_label})").classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(format_currency(balance)).classes(f'text-3xl font-bold text-{color}-600')

                    # --- Savings Rate Card ---
                    savings_rate = (summary["balance"] / summary["total_income"]) * 100 if summary["total_income"] > 0 else 0
                    
                    if savings_rate > 1:
                        savings_color = 'green'
                    elif savings_rate < -1:
                        savings_color = 'red'
                    else:
                        savings_color = 'blue' # Neutral color for near-zero rates

                    with ui.card().classes(f'flex-1 w-full p-4 border-l-4 border-{savings_color}-500 shadow-sm'):
                        ui.label('Savings Rate').classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(f'{savings_rate:.1f}%').classes(f'text-3xl font-bold text-{savings_color}-600')

                # --- Pie Chart & Recent Transactions ---
                with ui.row().classes('w-full gap-4 responsive-row'):
                    # Pie Chart
                    with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                        ui.label('Expenses by Category').classes('text-lg font-bold mb-4 text-gray-700')
                        chart_container = ui.column().classes('w-full')
                        with chart_container:
                            ui.label('Loading chart...').classes('text-gray-400 italic')

                    # --- Recent Transactions ---
                    with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                        ui.label('Recent Transactions').classes('text-lg font-bold mb-4 text-gray-700')
                        if expenses:
                            # Mobile-friendly card layout for recent transactions
                            with ui.column().classes('w-full gap-3'):
                                for expense in expenses[:5]:  # Limit to 5 most recent
                                    with ui.card().classes('w-full p-3 shadow-sm border border-gray-200 hover:shadow-md transition-shadow'):
                                        with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
                                            # Date and Category
                                            with ui.column().classes('flex-1 min-w-0'):
                                                ui.label(expense.date.strftime('%d.%m.%Y')).classes('text-sm text-gray-600 font-medium')
                                                ui.label(expense.category).classes('text-sm text-gray-800 truncate')
                                            
                                            # Amount
                                            amount_class = 'text-green-600 font-bold' if getattr(expense, 'type', 'expense') == 'income' else 'text-red-600'
                                            ui.label(
                                                f"{'+' if getattr(expense, 'type', 'expense') == 'income' else '-'}{format_currency(expense.amount_eur)}"
                                            ).classes(f'text-lg font-semibold {amount_class} whitespace-nowrap')
                        else:
                            ui.label('No transactions yet.').classes('text-gray-400 italic')

            async def load_chart():
                db = next(get_db())
                try:
                    by_category = ExpenseService.get_category_breakdown(db, year=selected_year, month=selected_month)
                finally:
                    db.close()

                chart_container.clear()
                with chart_container:
                    if by_category:
                        render_expenses_by_category_pie(
                            by_category=by_category,
                            expenses_label=expenses_label,
                            format_currency=format_currency,
                        )
                    else:
                        ui.label('No expense data yet.').classes('text-gray-400 italic')

            ui.timer(0.05, lambda: asyncio.create_task(load_chart()), once=True)

        # Bind refresh to filters
        year_select.on_value_change(refresh_dashboard)
        month_select.on_value_change(refresh_dashboard)
        all_year_switch.on_value_change(refresh_dashboard)
        
        # Initial Load
        refresh_dashboard()
