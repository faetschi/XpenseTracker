import asyncio
import time

from nicegui import ui, app
from datetime import date
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency
from app.core.config import settings
from app.ui.layout import theme

def dashboard_page():
    theme('dashboard')
    
    # Mobile quick action (sticky bottom footer bar)
    with ui.element('div').classes('mobile-bottom-bar mobile-only'):
        ui.button('Add Expense', icon='add_circle', on_click=lambda: ui.navigate.to('/add')) \
            .props('no-caps unelevated') \
            .classes('mobile-add-btn')
    
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

        now_ts = time.time()
        saved_filters = app.storage.user.get('dashboard_filters')
        use_saved_filters = False
        if isinstance(saved_filters, dict):
            saved_ts = saved_filters.get('ts')
            if isinstance(saved_ts, (int, float)) and now_ts - saved_ts <= 300:
                use_saved_filters = True

        saved_year = saved_filters.get('year') if use_saved_filters else None
        saved_month = saved_filters.get('month') if use_saved_filters else None
        saved_all_year = saved_filters.get('all_year') if use_saved_filters else False

        initial_year = saved_year if isinstance(saved_year, int) and saved_year in year_options else current_year
        initial_month = saved_month if isinstance(saved_month, int) and 1 <= saved_month <= 12 else current_month
        initial_all_year = bool(saved_all_year)
        last_month = initial_month if initial_month is not None else current_month

        def persist_filters():
            app.storage.user['dashboard_filters'] = {
                'year': year_select.value,
                'month': month_select.value,
                'all_year': all_year_switch.value,
                'ts': time.time(),
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
                month_select.value = last_month


        def apply_all_year_state(is_all_year: bool, month_value: int):
            all_year_switch.value = is_all_year
            if is_all_year:
                month_select.disable()
                btn_prev.disable()
                btn_next.disable()
                month_select.value = None
            else:
                month_select.enable()
                btn_prev.enable()
                btn_next.enable()
                month_select.value = month_value

        def jump_to_current_date():
            nonlocal last_month
            today = date.today()
            year_select.value = today.year
            last_month = today.month
            apply_all_year_state(False, today.month)
            persist_filters()
            refresh_dashboard()

        with ui.row().classes('filter-toolbar responsive-row w-full gap-3 p-3 bg-white rounded-lg shadow-sm border border-gray-200 items-start justify-start'):
            # Year Selector
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-start'):
                    year_select = ui.select(
                        options=year_options,
                        value=initial_year,
                        label="Year"
                    ).props('outlined dense options-dense behavior="menu"').classes('filter-select px-1')
            # Month Selector
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-start flex-nowrap'):
                    btn_prev = ui.button(icon='chevron_left', on_click=lambda: change_month(-1)).props('flat round dense color=gray')
                    month_select = ui.select(
                        options=month_map,
                        value=initial_month,
                        label="Month"
                    ).props('outlined dense options-dense behavior="menu"').classes('filter-select px-1')
                    btn_next = ui.button(icon='chevron_right', on_click=lambda: change_month(1)).props('flat round dense color=gray')
            # Jump to current date
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto self-center'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-center md:justify-start flex-wrap'):
                    (
                        ui.button('📅 Current Date', on_click=jump_to_current_date)
                        .props('outline dense color=black no-caps')
                        .classes('text-sm px-3 font-normal w-auto mx-2')
                        .style('margin-left: auto; margin-right: auto; display: flex; justify-content: center;')
                    )
            # Toggle Month
            with ui.column().classes('filter-group w-full gap-3 items-center md:items-start lg:w-auto md:-ml-2'):
                with ui.row().classes('items-center gap-1 w-full md:max-w-md justify-center md:justify-start flex-wrap'):
                    all_year_switch = (
                        ui.switch('All Year', on_change=toggle_month)
                        .classes('filter-switch px-1 w-auto mx-2')
                        .style('margin-left: auto; margin-right: auto; display: flex; justify-content: center;')
                    )

        # Content Container (to be refreshed)
        content = ui.column().classes('w-full gap-6')

        stats_cache: dict[tuple[int | None, int | None], tuple[float, dict]] = {}

        def refresh_dashboard():
            content.clear()
            
            selected_year = year_select.value
            selected_month = month_select.value if not all_year_switch.value else None
            
            cache_key = (selected_year, selected_month)
            now = time.time()
            cached = stats_cache.get(cache_key)

            if cached and settings.DASHBOARD_CACHE_TTL_SECONDS > 0:
                cached_at, cached_summary = cached
                if now - cached_at <= settings.DASHBOARD_CACHE_TTL_SECONDS:
                    summary = cached_summary
                else:
                    summary = None
            else:
                summary = None

            if summary is None:
                db = next(get_db())
                try:
                    summary = ExpenseService.get_summary(db, year=selected_year, month=selected_month)
                finally:
                    db.close()
                stats_cache[cache_key] = (now, summary)

            db = next(get_db())
            try:
                expenses = ExpenseService.get_expenses(db, limit=5)
            finally:
                db.close()

            # Chart containers (initialized before the with block for closure access)
            chart_container = None
            bar_chart_container = None
            daily_bar_container = None
            show_income_toggle = None

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
                        savings_color = 'blue'

                    with ui.card().classes(f'flex-1 w-full p-4 border-l-4 border-{savings_color}-500 shadow-sm'):
                        ui.label('Savings Rate').classes('text-gray-500 text-sm uppercase tracking-wide')
                        ui.label(f'{savings_rate:.1f}%').classes(f'text-3xl font-bold text-{savings_color}-600')

                # Charts Section
                if all_year_switch.value:
                    # All Year Mode: Monthly bar chart (full width)
                    with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                        ui.label('Monthly Income vs Expenses').classes('text-lg font-bold mb-4 text-gray-700')
                        bar_chart_container = ui.column().classes('w-full')
                        with bar_chart_container:
                            if settings.ENABLE_CHARTS:
                                ui.label('Loading chart...').classes('text-gray-400 italic')
                            else:
                                ui.label('Charts disabled for performance.').classes('text-gray-400 italic')
                else:
                    # Month Mode: Pie chart + Daily bar chart side by side
                    with ui.row().classes('w-full gap-4 responsive-row'):
                        # Pie Chart
                        with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                            ui.label('Expenses by Category').classes('text-lg font-bold mb-4 text-gray-700')
                            chart_container = ui.column().classes('w-full')
                            with chart_container:
                                if settings.ENABLE_CHARTS:
                                    ui.label('Loading chart...').classes('text-gray-400 italic')
                                else:
                                    ui.label('Charts disabled for performance.').classes('text-gray-400 italic')

                        # Daily Bar Chart
                        with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                            with ui.row().classes('w-full items-center justify-between mb-4'):
                                ui.label('Daily Expenses').classes('text-lg font-bold text-gray-700')
                                show_income_toggle = ui.switch('Income', value=False).props('color=green size=sm')
                            daily_bar_container = ui.column().classes('w-full')
                            with daily_bar_container:
                                if settings.ENABLE_CHARTS:
                                    ui.label('Loading chart...').classes('text-gray-400 italic')
                                else:
                                    ui.label('Charts disabled for performance.').classes('text-gray-400 italic')

                # --- Recent Transactions ---
                with ui.card().classes('flex-1 w-full p-6 shadow-sm min-w-[280px]'):
                    ui.label('Recent Transactions').classes('text-lg font-bold mb-4 text-gray-700')
                    if expenses:
                        with ui.column().classes('w-full gap-3'):
                            for expense in expenses[:5]:
                                with ui.card().classes('w-full p-3 shadow-sm border border-gray-200 hover:shadow-md transition-shadow'):
                                    with ui.row().classes('w-full items-center justify-between flex-wrap gap-2'):
                                        with ui.column().classes('flex-1 min-w-0'):
                                            ui.label(expense.date.strftime('%d.%m.%Y')).classes('text-sm text-gray-600 font-medium')
                                            ui.label(expense.category).classes('text-sm text-gray-800 truncate')
                                        
                                        etype = getattr(expense, 'type', 'expense')
                                        if etype == 'income':
                                            amount_class = 'text-green-600 font-bold'
                                            prefix = '+'
                                        elif etype == 'transfer':
                                            amount_class = 'text-blue-600 font-bold'
                                            prefix = '↔'
                                        else:
                                            amount_class = 'text-red-600'
                                            prefix = '-'
                                        ui.label(
                                            f"{prefix}{format_currency(expense.amount_eur)}"
                                        ).classes(f'text-lg font-semibold {amount_class} whitespace-nowrap')
                    else:
                        ui.label('No transactions yet.').classes('text-gray-400 italic')

            async def load_chart():
                if not settings.ENABLE_CHARTS:
                    return

                from app.ui.charts import (
                    render_expenses_by_category_lightweight,
                    render_expenses_by_category_pie,
                    render_monthly_bar_chart,
                    render_monthly_bar_chart_lightweight,
                    render_daily_bar_chart,
                )

                if all_year_switch.value:
                    # All Year Mode: Monthly bar chart
                    monthly_cache_key = (selected_year, 'monthly')
                    cached_monthly = stats_cache.get(monthly_cache_key)
                    monthly_data = None
                    if cached_monthly and settings.DASHBOARD_CACHE_TTL_SECONDS > 0:
                        cached_at, data = cached_monthly
                        if now - cached_at <= settings.DASHBOARD_CACHE_TTL_SECONDS:
                            monthly_data = data

                    if monthly_data is None:
                        db = next(get_db())
                        try:
                            monthly_data = ExpenseService.get_monthly_breakdown(db, year=selected_year)
                        finally:
                            db.close()
                        stats_cache[monthly_cache_key] = (now, monthly_data)

                    if bar_chart_container:
                        bar_chart_container.clear()
                        with bar_chart_container:
                            if monthly_data and any(m['spent'] > 0 or m['income'] > 0 for m in monthly_data):
                                if settings.LIGHTWEIGHT_CHARTS:
                                    render_monthly_bar_chart_lightweight(
                                        monthly_data=monthly_data,
                                        format_currency=format_currency,
                                    )
                                else:
                                    render_monthly_bar_chart(
                                        monthly_data=monthly_data,
                                        format_currency=format_currency,
                                    )
                            else:
                                ui.label('No data available for this year.').classes('text-gray-400 italic')
                else:
                    # Month Mode: Pie chart + Daily bar chart
                    
                    # Pie chart (category breakdown)
                    category_cache_key = (selected_year, selected_month)
                    cached_cat = stats_cache.get(category_cache_key)
                    by_category = None
                    if cached_cat and settings.DASHBOARD_CACHE_TTL_SECONDS > 0:
                        cached_at, cached_summary = cached_cat
                        if now - cached_at <= settings.DASHBOARD_CACHE_TTL_SECONDS:
                            by_category = cached_summary.get('by_category')

                    if by_category is None:
                        db = next(get_db())
                        try:
                            by_category = ExpenseService.get_category_breakdown(db, year=selected_year, month=selected_month)
                        finally:
                            db.close()
                        if cached_cat and settings.DASHBOARD_CACHE_TTL_SECONDS > 0:
                            stats_cache[category_cache_key] = (now, {**cached_summary, 'by_category': by_category})

                    if chart_container:
                        chart_container.clear()
                        with chart_container:
                            if by_category:
                                if settings.LIGHTWEIGHT_CHARTS:
                                    render_expenses_by_category_lightweight(
                                        by_category=by_category,
                                        expenses_label=expenses_label,
                                        format_currency=format_currency,
                                    )
                                else:
                                    render_expenses_by_category_pie(
                                        by_category=by_category,
                                        expenses_label=expenses_label,
                                        format_currency=format_currency,
                                    )
                            else:
                                ui.label('No expense data yet.').classes('text-gray-400 italic')

                    # Daily bar chart
                    daily_cache_key = (selected_year, selected_month, 'daily')
                    cached_daily = stats_cache.get(daily_cache_key)
                    daily_data = None
                    if cached_daily and settings.DASHBOARD_CACHE_TTL_SECONDS > 0:
                        cached_at, data = cached_daily
                        if now - cached_at <= settings.DASHBOARD_CACHE_TTL_SECONDS:
                            daily_data = data

                    if daily_data is None:
                        db = next(get_db())
                        try:
                            daily_data = ExpenseService.get_daily_breakdown(db, year=selected_year, month=selected_month)
                        finally:
                            db.close()
                        stats_cache[daily_cache_key] = (now, daily_data)

                    if daily_bar_container:
                        daily_bar_container.clear()
                        with daily_bar_container:
                            show_income = show_income_toggle.value if show_income_toggle else False
                            if daily_data and any(d['spent'] > 0 for d in daily_data):
                                render_daily_bar_chart(
                                    daily_data=daily_data,
                                    format_currency=format_currency,
                                    show_income=show_income,
                                )
                            else:
                                ui.label('No expense data for this month.').classes('text-gray-400 italic')

            def on_income_toggle_change(_):
                asyncio.create_task(load_chart())

            if show_income_toggle is not None:
                show_income_toggle.on_value_change(on_income_toggle_change)

            ui.timer(0.05, lambda: asyncio.create_task(load_chart()), once=True)

        def on_filters_change():
            nonlocal last_month
            if month_select.value:
                last_month = month_select.value
            persist_filters()
            refresh_dashboard()

        apply_all_year_state(initial_all_year, initial_month)

        # Bind refresh to filters
        year_select.on_value_change(on_filters_change)
        month_select.on_value_change(on_filters_change)
        all_year_switch.on_value_change(on_filters_change)
        
        # Initial Load
        refresh_dashboard()
