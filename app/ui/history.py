from nicegui import ui
from datetime import datetime
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency
from app.core.config import settings
from app.ui.layout import theme
import json

def history_page():
    theme('history')
    
    # Inject responsive styles directly to ensure they are applied correctly
    ui.add_head_html('''
        <style>
            @media (min-width: 785px) {
                .history-mobile-only { display: none !important; }
                .history-desktop-only { display: block !important; }
            }
            @media (max-width: 784px) {
                .history-desktop-only { display: none !important; }
                .history-mobile-only { display: block !important; }
            }
        </style>
    ''')
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6 history-container'):
        ui.label('📜 Transaction History').classes('text-2xl font-bold text-gray-800')
        
        # Fetch Data
        db = next(get_db())
        try:
            expenses = ExpenseService.get_expenses(db, limit=1000)
        finally:
            db.close()
        
        if not expenses:
            ui.label('No transactions found.').classes('text-gray-500')
            return

        # Prepare data for AgGrid
        rows = [
            {
                'id': e.id,
                'date': e.date.strftime('%d.%m.%Y'),
                'type': e.type,
                'category': e.category,
                'description': e.description,
                'amount': float(e.amount),
                'currency': e.currency,
                'amount_eur': float(e.amount_eur),
                'actions': '<span style="cursor: pointer; font-size: 1.2em;">❌</span>'
            } for e in expenses
        ]
        
        async def handle_cell_value_change(e):
            row_id = int(e.args['data']['id'])
            field = e.args['colId']
            new_value = e.args['newValue']
            
            updates = {}
            if field == 'amount':
                try:
                    updates['amount'] = float(new_value)
                except ValueError:
                    ui.notify('Invalid amount', type='negative')
                    return
            elif field == 'date':
                try:
                    dt = datetime.strptime(new_value, '%d.%m.%Y').date()
                    updates['date'] = dt
                except ValueError:
                    try:
                        dt = datetime.strptime(new_value, '%d.%m.%Y').date()
                        updates['date'] = dt
                    except ValueError:
                        ui.notify('Invalid date format. Use DD.MM.YYYY', type='negative')
                        return
            else:
                updates[field] = new_value

            db = next(get_db())
            try:
                updated = ExpenseService.update_expense(db, row_id, updates)
                if updated:
                    ui.notify(f'Updated {field}', type='positive')
                else:
                    ui.notify('Failed to update', type='negative')
            except Exception as ex:
                ui.notify(f'Error: {str(ex)}', type='negative')
            finally:
                db.close()

        async def delete_handler(expense_id, expense_type=None, category=None, amount_eur=None):
            # If we have details, show a nice confirmation. If not (from grid), just delete or show simple confirm.
            msg = f"Are you sure you want to delete this {expense_type or 'transaction'}?"
            detail = f"{category} - {format_currency(amount_eur)}" if category and amount_eur else ""
            
            with ui.dialog() as dialog, ui.card().classes('p-4'):
                ui.label(msg).classes('text-lg font-bold')
                if detail:
                    ui.label(detail).classes('text-gray-600 mb-4')
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=lambda: dialog.submit(False)).props('flat')
                    ui.button('Delete', on_click=lambda: dialog.submit(True)).props('color=red')

            if await dialog:
                db = next(get_db())
                try:
                    if ExpenseService.delete_expense(db, expense_id):
                        ui.notify('Deleted successfully', type='positive')
                        ui.navigate.to('/history')
                    else:
                        ui.notify('Failed to delete', type='negative')
                finally:
                    db.close()

        async def show_edit_dialog(expense):
            with ui.dialog() as edit_dialog, ui.card().classes('w-full max-w-md p-4'):
                ui.label(f'Edit {expense.type.capitalize()}').classes('text-xl font-bold mb-4')
                
                # Date with picker
                with ui.input('Date') as date_input:
                    date_input.classes('w-full mb-2')
                    date_input.value = expense.date.strftime('%Y-%m-%d')
                    with date_input.add_slot('append'):
                        ui.icon('edit_calendar').classes('cursor-pointer').on('click', lambda: menu.open())
                    with ui.menu() as menu:
                        ui.date().bind_value(date_input)
                
                type_select = ui.select(['expense', 'income'], label='Type', value=expense.type).classes('w-full mb-2')
                
                category_options = settings.INCOME_CATEGORIES if expense.type == 'income' else settings.EXPENSE_CATEGORIES
                category_select = ui.select(category_options, label='Category', value=expense.category).classes('w-full mb-2')
                
                desc_input = ui.input('Description', value=expense.description or '').classes('w-full mb-2')
                amount_input = ui.number('Amount', value=float(expense.amount), format='%.2f').classes('w-full mb-2')
                currency_select = ui.select(settings.CURRENCIES, label='Currency', value=expense.currency).classes('w-full mb-4')
                
                def update_category_options():
                    if type_select.value == 'income':
                        category_select.options = settings.INCOME_CATEGORIES
                        if category_select.value not in settings.INCOME_CATEGORIES:
                            category_select.value = settings.INCOME_CATEGORIES[0]
                    else:
                        category_select.options = settings.EXPENSE_CATEGORIES
                        if category_select.value not in settings.EXPENSE_CATEGORIES:
                            category_select.value = settings.EXPENSE_CATEGORIES[0]
                
                type_select.on_value_change(update_category_options)
                
                async def save_changes():
                    try:
                        # Parse date from YYYY-MM-DD (from ui.date)
                        try:
                            dt = datetime.strptime(date_input.value, '%Y-%m-%d').date()
                        except ValueError:
                            # Fallback to DD.MM.YYYY if manually entered
                            dt = datetime.strptime(date_input.value, '%d.%m.%Y').date()
                        
                        updates = {
                            'date': dt,
                            'type': type_select.value,
                            'category': category_select.value,
                            'description': desc_input.value,
                            'amount': float(amount_input.value),
                            'currency': currency_select.value
                        }
                        
                        db = next(get_db())
                        try:
                            updated = ExpenseService.update_expense(db, expense.id, updates)
                            if updated:
                                ui.notify('Updated successfully', type='positive')
                                edit_dialog.close()
                                ui.navigate.to('/history')
                            else:
                                ui.notify('Failed to update', type='negative')
                        finally:
                            db.close()
                    except Exception as e:
                        ui.notify(f'Error: {str(e)}', type='negative')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=edit_dialog.close).props('flat')
                    ui.button('Save', on_click=save_changes).props('color=primary')
            
            edit_dialog.open()

        # Desktop Table View
        with ui.element('div').classes('w-full history-desktop-only'):
            grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Date', 'field': 'date', 'sortable': True, 'filter': True, 'editable': True, 'width': 100},
                    {'headerName': 'Type', 'field': 'type', 'sortable': True, 'filter': True, 'editable': True,
                     'cellEditor': 'agSelectCellEditor',
                     'cellEditorParams': {'values': ['expense', 'income']}, 'width': 80},
                    {'headerName': 'Category', 'field': 'category', 'sortable': True, 'filter': True, 'editable': True, 'width': 120,
                     ':cellEditorSelector': f"""(params) => {{
                         if (params.data.type === 'income') {{
                             return {{
                                 component: 'agSelectCellEditor',
                                 params: {{ values: {json.dumps(settings.INCOME_CATEGORIES)} }}
                             }};
                         }}
                         return {{
                             component: 'agSelectCellEditor',
                             params: {{ values: {json.dumps(settings.EXPENSE_CATEGORIES)} }}
                         }};
                     }}"""
                    },
                    {'headerName': 'Description', 'field': 'description', 'sortable': True, 'filter': True, 'editable': True, 'width': 200},
                    {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': 'agNumberColumnFilter', 'editable': True,
                     'valueFormatter': "Number(value).toFixed(2)", 'width': 100,
                     'cellClassRules': {
                         'text-green-600 font-bold': 'data.type == "income"',
                         'text-red-600': 'data.type == "expense"'
                     }},
                    {'headerName': 'Currency', 'field': 'currency', 'sortable': True, 'filter': True, 'editable': True,
                     'cellEditor': 'agSelectCellEditor',
                     'cellEditorParams': {'values': settings.CURRENCIES}, 'width': 80},
                    {'headerName': 'Actions', 'field': 'actions', 'width': 80, 'editable': False, 'pinned': 'right'}
                ],
                'rowData': rows,
                'pagination': True,
                'paginationPageSize': 25,
                'domLayout': 'autoHeight',
                'defaultColDef': {
                    'resizable': True,
                    'sortable': True,
                    'filter': True
                }
            }, html_columns=[6]).classes('w-full shadow-sm').on('cellValueChanged', handle_cell_value_change)
            
            async def handle_cell_clicked(e):
                if e.args['colId'] == 'actions':
                    data = e.args['data']
                    await delete_handler(
                        int(data['id']), 
                        data['type'], 
                        data['category'], 
                        data['amount_eur']
                    )
                    
            grid.on('cellClicked', handle_cell_clicked)

        # Mobile Card View
        with ui.element('div').classes('w-full history-mobile-only'):
            with ui.column().classes('w-full gap-4'):
                for expense in expenses:
                    with ui.card().classes('w-full p-0 shadow-sm border border-gray-200 hover:shadow-md transition-shadow overflow-hidden cursor-pointer') \
                        .on('click', lambda _, e=expense: show_edit_dialog(e)):
                        # Color strip at the top based on type
                        strip_color = 'bg-green-500' if expense.type == 'income' else 'bg-red-500'
                        ui.element('div').classes(f'w-full h-1 {strip_color}')
                        
                        with ui.column().classes('w-full px-2 pb-2 pt-0 gap-1 m-0'):
                            # Header: Date and Actions
                            with ui.row().classes('w-full items-center justify-between'):
                                ui.label(expense.date.strftime('%d.%m.%Y')).classes('text-s font-bold text-gray-500 uppercase tracking-wider')
                                with ui.row().classes('gap-0'):
                                    ui.button(icon='edit').props('flat round dense').classes('text-blue-600 scale-90') \
                                        .on('click.stop', lambda _, e=expense: show_edit_dialog(e))
                                    ui.button(icon='delete').props('flat round dense').classes('text-red-600 scale-90') \
                                        .on('click.stop', lambda _, e=expense: delete_handler(e.id, e.type, e.category, e.amount_eur))
                            
                            # Category & Amount Row (Combined for slimness)
                            with ui.row().classes('w-full items-center justify-between'):
                                ui.label(expense.category).classes('text-base font-bold text-gray-900 leading-tight')
                                
                                amount_class = 'text-green-600' if expense.type == 'income' else 'text-red-600'
                                ui.label(
                                    f"{'+' if expense.type == 'income' else '-'}{format_currency(expense.amount_eur)}"
                                ).classes(f'text-base font-black {amount_class}')
                            
                            # Description & Secondary Currency (if any)
                            if expense.description or expense.currency != 'EUR':
                                with ui.row().classes('w-full items-center justify-between'):
                                    if expense.description:
                                        ui.label(expense.description).classes('text-sm text-gray-600 italic truncate max-w-[60%]')
                                    else:
                                        ui.element('div')
                                        
                                    if expense.currency != 'EUR':
                                        ui.label(f"{float(expense.amount):.2f} {expense.currency}").classes('text-s text-gray-500')
