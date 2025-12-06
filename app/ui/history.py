from nicegui import ui
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.utils.formatting import format_currency
from app.core.config import settings
from app.ui.layout import theme

def history_page():
    theme()
    
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
                'category': e.category,
                'description': e.description,
                'amount': float(e.amount),
                'currency': e.currency,
                'amount_eur': float(e.amount_eur)
            } for e in expenses
        ]
        
        async def delete_row(row_id):
            db = next(get_db())
            try:
                if ExpenseService.delete_expense(db, row_id):
                    ui.notify(f'Deleted expense {row_id}', type='positive')
                    # Remove from grid
                    rows[:] = [r for r in rows if r['id'] != row_id]
                    grid.update()
                else:
                    ui.notify('Failed to delete expense', type='negative')
            except Exception as e:
                ui.notify(f'Error: {str(e)}', type='negative')
            finally:
                db.close()

        # Custom Cell Renderer for Delete Button
        # We need to register this component in the grid options
        grid = ui.aggrid({
            'columnDefs': [
                {'headerName': 'Date', 'field': 'date', 'sortable': True, 'filter': True, 'editable': True},
                {'headerName': 'Category', 'field': 'category', 'sortable': True, 'filter': True, 'editable': True, 
                 'cellEditor': 'agSelectCellEditor', 
                 'cellEditorParams': {'values': settings.EXPENSE_CATEGORIES}},
                {'headerName': 'Description', 'field': 'description', 'sortable': True, 'filter': True, 'editable': True},
                {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': 'agNumberColumnFilter', 'editable': True},
                {'headerName': 'Currency', 'field': 'currency', 'sortable': True, 'filter': True, 'editable': True,
                 'cellEditor': 'agSelectCellEditor',
                 'cellEditorParams': {'values': settings.CURRENCIES}},
                {'headerName': 'Actions', 'field': 'id', 'cellRenderer': 'deleteButtonRenderer', 'width': 100}
            ],
            'rowData': rows,
            'pagination': True,
            'paginationPageSize': 20,
            'domLayout': 'autoHeight',
            'components': {
                'deleteButtonRenderer': """
                    class DeleteButtonRenderer {
                        init(params) {
                            this.eGui = document.createElement('div');
                            this.eGui.innerHTML = '<button style="color: red; font-weight: bold; cursor: pointer;">🗑️</button>';
                            this.eGui.querySelector('button').addEventListener('click', () => {
                                params.context.componentParent.delete_row(params.value);
                            });
                        }
                        getGui() { return this.eGui; }
                    }
                """
            },
            'context': {'componentParent': None} # Will be set below
        }).classes('w-full shadow-sm')
        
        # Hack to pass the python function to the JS context
        grid.options['context']['componentParent'] = ui.context.client
        # delete_row function needs to be exposed to client
        # -> but NiceGUI's AgGrid wrapper doesn't support direct JS-to-Python callbacks easily via 'context' in this version.
        # ALTERNATIVE APPROACH: Use a separate column of buttons outside AgGrid or use ui.table instead.
        # Since AgGrid is complex to wire up with custom renderers in Python-only NiceGUI without extra JS files
        # -> switch to ui.table which is native and easier for this "Action" button requirement.
        
        # Re-implementing with ui.table for better "Action" support
        grid.delete() # Remove the AgGrid we just defined
        
        columns = [
            {'name': 'date', 'label': 'Date', 'field': 'date', 'sortable': True, 'align': 'left'},
            {'name': 'category', 'label': 'Category', 'field': 'category', 'sortable': True, 'align': 'left'},
            {'name': 'description', 'label': 'Description', 'field': 'description', 'sortable': True, 'align': 'left'},
            {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'sortable': True, 'align': 'right'},
            {'name': 'currency', 'label': 'Currency', 'field': 'currency', 'sortable': True, 'align': 'center'},
            {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
        ]
        
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
                        table.rows = [r for r in table.rows if r['id'] != row_id]
                        table.update()
                    else:
                        ui.notify('Failed to delete', type='negative')
                finally:
                    db.close()

        with ui.table(columns=columns, rows=rows, pagination=10).classes('w-full') as table:
            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn @click="$parent.$emit('delete', props.row.id)" icon="delete" flat dense color="negative" />
                </q-td>
            ''')
            table.on('delete', lambda e: delete_handler(e.args))

        ui.label('Note: Inline editing is currently disabled in this view.').classes('text-xs text-gray-400 mt-2')
