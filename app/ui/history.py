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
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6'):
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

        async def delete_handler(row_id):
            with ui.dialog() as dialog, ui.card():
                ui.label('Are you sure you want to delete this expense?').classes('text-lg font-bold')
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button('Cancel', on_click=lambda: dialog.submit(False)).props('flat')
                    ui.button('Delete', on_click=lambda: dialog.submit(True)).props('color=red')

            if await dialog:
                db = next(get_db())
                try:
                    if ExpenseService.delete_expense(db, row_id):
                        ui.notify(f'Deleted expense', type='positive')
                        # Reload the page to refresh data
                        ui.navigate.to('/history')
                    else:
                        ui.notify('Failed to delete', type='negative')
                finally:
                    db.close()

        grid = ui.aggrid({
            'columnDefs': [
                {'headerName': 'Date', 'field': 'date', 'sortable': True, 'filter': True, 'editable': True},
                {'headerName': 'Type', 'field': 'type', 'sortable': True, 'filter': True, 'editable': True,
                 'cellEditor': 'agSelectCellEditor',
                 'cellEditorParams': {'values': ['expense', 'income']}},
                {'headerName': 'Category', 'field': 'category', 'sortable': True, 'filter': True, 'editable': True, 
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
                {'headerName': 'Description', 'field': 'description', 'sortable': True, 'filter': True, 'editable': True},
                {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': 'agNumberColumnFilter', 'editable': True,
                 'valueFormatter': "Number(value).toFixed(2)",
                 'cellClassRules': {
                     'text-green-600 font-bold': 'data.type == "income"',
                     'text-red-600': 'data.type == "expense"'
                 }},
                {'headerName': 'Currency', 'field': 'currency', 'sortable': True, 'filter': True, 'editable': True,
                 'cellEditor': 'agSelectCellEditor',
                 'cellEditorParams': {'values': settings.CURRENCIES}},
                {'headerName': 'Actions', 'field': 'actions', 'width': 100, 'editable': False}
            ],
            'rowData': rows,
            'pagination': True,
            'paginationPageSize': 25,
            'domLayout': 'autoHeight',
        }, html_columns=[6]).classes('w-full shadow-sm').on('cellValueChanged', handle_cell_value_change)
        
        async def handle_cell_clicked(e):
            if e.args['colId'] == 'actions':
                row_id = int(e.args['data']['id'])
                await delete_handler(row_id)
                
        grid.on('cellClicked', handle_cell_clicked)
