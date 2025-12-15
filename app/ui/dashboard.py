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

        with ui.row().classes('filter-toolbar w-full gap-3 p-3 bg-white rounded-lg shadow-sm border border-gray-200 flex flex-row items-start justify-start'):
            with ui.column().classes('w-full gap-3 items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full max-w-md justify-start'):
                    year_select = ui.select(
                        options=year_options,
                        value=current_year,
                        label="Year"
                    ).props('outlined dense options-dense behavior="menu"').classes('filter-select px-1')
            with ui.column().classes('w-full gap-3 items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full max-w-md justify-start flex-nowrap'):
                    btn_prev = ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round dense color=gray')
                    month_select = ui.select(
                        options=month_map,
                        value=current_month,
                        label="Month"
                    ).props('outlined dense options-dense behavior="menu"').classes('filter-select px-1')
                    btn_next = ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round dense color=gray')
            with ui.column().classes('w-full gap-3 items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full max-w-md justify-start flex-wrap'):
                    all_year_switch = ui.switch('Whole Year', on_change=toggle_month).classes('filter-input px-1')

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
                with ui.row().classes('w-full gap-4 flex-col md:flex-row'):
                    period_label = 'All Year' if not selected_month else date(2000, selected_month, 1).strftime('%B')
                    
                    # --- Income Card ---
                    with ui.card().classes('flex-1 w-full p-4 border-l-4 border-green-500 shadow-sm'):
                        ui.label(f"Income ({period_label})").classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(format_currency(stats["total_income"])).classes('text-3xl font-bold text-gray-800')

                    # --- Expenses Card ---
                    with ui.card().classes('flex-1 w-full p-4 border-l-4 border-red-500 shadow-sm'):
                        ui.label(f"Expenses ({period_label})").classes('text-gray-500 text-sm uppercase tracking-wide')
                        expenses_label = ui.label(format_currency(stats["total_spent"])).classes('text-3xl font-bold text-gray-800')

                    # --- Leftover-Balance Card ---
                    balance = stats["balance"]
                    color = 'green' if balance >= 0 else 'red'
                    with ui.card().classes(f'flex-1 w-full p-4 border-l-4 border-{color}-500 shadow-sm'):
                        ui.label(f"Leftover ({period_label})").classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(format_currency(balance)).classes(f'text-3xl font-bold text-{color}-600')

                    # --- Savings Rate Card ---
                    savings_rate = (stats["balance"] / stats["total_income"]) * 100 if stats["total_income"] > 0 else 0
                    
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
                with ui.row().classes('w-full gap-4 flex-col lg:flex-row'):
                    # Pie Chart
                    with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                        ui.label('Expenses by Category').classes('text-lg font-bold mb-4 text-gray-700')
                        render_expenses_by_category_pie(
                            by_category=stats.get('by_category'),
                            expenses_label=expenses_label,
                            format_currency=format_currency,
                        )

                    # --- Recent Transactions ---
                    with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                        ui.label('Recent Transactions').classes('text-lg font-bold mb-4 text-gray-700')
                        if expenses:
                            columns = [
                                {'name': 'date', 'label': 'Date', 'field': 'date', 'align': 'left'},
                                {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left'},
                                {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'align': 'right'},
                            ]
                            rows = [
                                {
                                    'date': e.date.strftime('%d.%m.%Y'),
                                    'category': e.category,
                                    'amount': format_currency(e.amount_eur),
                                    'type': getattr(e, 'type', 'expense') # Fallback if not loaded yet
                                } for e in expenses
                            ]
                            with ui.element('div').classes('w-full overflow-x-auto'):
                                table = ui.table(columns=columns, rows=rows, pagination=None).classes('w-full min-w-[320px]')
                            table.add_slot('body-cell-amount', '''
                                <q-td :props="props" :class="props.row.type === 'income' ? 'text-green-600 font-bold' : 'text-red-600'">
                                    {{ props.row.type === 'income' ? '+' : '-' }} {{ props.value }}
                                </q-td>
                            ''')
                        else:
                            ui.label('No transactions yet.').classes('text-gray-400 italic')

        # Bind refresh to filters
        year_select.on_value_change(refresh_dashboard)
        month_select.on_value_change(refresh_dashboard)
        all_year_switch.on_value_change(refresh_dashboard)
        
        # Initial Load
        refresh_dashboard()
