from nicegui import ui
from datetime import date, datetime
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.services.receipt_service import ReceiptService
from app.schemas.expense import ExpenseCreate
from app.core.config import settings
from app.ui.layout import theme
from app.utils.logger import get_logger
import io
import os

# Configure logging
logger = get_logger(__name__)

def add_expense_page():
    theme('add_expense')
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6'):
        ui.label('➕ Add New Expense').classes('text-2xl font-bold text-gray-800')
        
        with ui.tabs().classes('w-full text-blue-600').props('align="left"') as tabs:
            ai_tab = ui.tab('AI Upload')
            manual_tab = ui.tab('Manual Entry')
            
        with ui.tab_panels(tabs, value=ai_tab).classes('w-full bg-transparent'):
            
            # --- AI TAB ---
            with ui.tab_panel(ai_tab).classes('p-0'):
                with ui.card().classes('w-full p-6 shadow-sm'):
                    ui.label('Upload Receipt').classes('text-lg font-bold mb-4 text-gray-700')
                    
                    # Image Preview
                    preview_image = ui.image().classes('max-h-64 w-full object-contain mb-4 rounded-lg hidden')

                    # Container for manual entry -> initially hidden
                    ai_form_container = ui.column().classes('w-full gap-4 mt-4')
                    ai_form_container.set_visibility(False)
                    
                    with ai_form_container:
                        with ui.grid(columns=2).classes('w-full gap-4'):
                            ai_date = ui.input(label='Date').props('type=date')
                            ai_category = ui.select(
                                options=settings.EXPENSE_CATEGORIES,
                                label="Category"
                            ).classes('w-full')
                            ai_desc = ui.input(label="Description").classes('col-span-2 w-full')
                            ai_amount = ui.number(label="Amount", format="%.2f").classes('w-full')
                            ai_currency = ui.select(options=settings.CURRENCIES, label="Currency").classes('w-full')
                        
                        def save_ai():
                            try:
                                expense_data = ExpenseCreate(
                                    date=date.fromisoformat(ai_date.value),
                                    category=ai_category.value,
                                    description=ai_desc.value,
                                    amount=ai_amount.value,
                                    currency=ai_currency.value
                                )
                                db = next(get_db())
                                ExpenseService.create_expense(db, expense_data)
                                ui.notify('Expense saved successfully!', type='positive')
                                # Clear form and hide
                                ai_desc.value = ""
                                ai_amount.value = None
                                ai_form_container.set_visibility(False) ### hides the manual entry form
                                preview_image.classes(add='hidden')
                                preview_image.set_source('')
                            except Exception as e:
                                ui.notify(f'Error saving: {str(e)}', type='negative')

                        ui.button('Save to Database', on_click=save_ai).classes('w-full bg-green-600 text-white mt-4')

                    async def handle_upload(e):
                        logger.info(f"File Upload triggered.")
                        
                        notification = ui.notification('Processing receipt...', type='info', spinner=True, timeout=None)
                        try:
                            # Extract content and filename
                            content = getattr(e, 'content', None)
                            filename = getattr(e, 'name', None)
                            
                            # Handle SmallFileUpload structure
                            if hasattr(e, 'file'):
                                if not filename and hasattr(e.file, 'name'):
                                    filename = e.file.name
                                
                                if content is None:
                                    if hasattr(e.file, '_data'):
                                        content = io.BytesIO(e.file._data)
                                    elif hasattr(e.file, 'read'):
                                        file_data = await e.file.read()
                                        content = io.BytesIO(file_data)
                            
                            if content is None:
                                logger.error("Upload content missing")
                                if notification:
                                    notification.message = "Error: Upload content missing."
                                    notification.spinner = False
                                    notification.type = 'negative'
                                    notification.timeout = 5000
                                return

                            # Delegate processing to ReceiptService
                            result, file_path = await ReceiptService.process_receipt(content, filename)
                            
                            # Show Preview
                            web_path = f"/{file_path.replace(os.sep, '/')}"
                            preview_image.set_source(web_path)
                            preview_image.classes(remove='hidden')

                            # Update Form
                            ai_date.value = result.date.strftime('%Y-%m-%d')
                            ai_amount.value = float(result.amount)
                            ai_currency.value = result.currency
                            ai_category.value = result.category
                            ai_desc.value = result.description
                            
                            # Show the form for review
                            ai_form_container.set_visibility(True)
                            
                            # Update notification to success state
                            if notification:
                                notification.message = 'Receipt scanned! Review and save.'
                                notification.spinner = False
                                notification.type = 'positive'
                                notification.timeout = 5000
                            
                            # Reset uploader to clear progress bar and file list
                            uploader.reset()
                            
                        except Exception as err:
                            if notification:
                                notification.message = f'Error scanning receipt: {str(err)}'
                                notification.spinner = False
                                notification.type = 'negative'
                                notification.timeout = 5000
                            logger.error(f"Error in handle_upload: {err}", exc_info=True)
                            uploader.reset()

                    uploader = ui.upload(on_upload=handle_upload, label="Drop receipt image here", auto_upload=True) \
                        .props('flat bordered color=blue-6 accept=".jpg, .jpeg, .png, .heic" no-thumbnails') \
                        .classes('w-full mb-6')

            # --- MANUAL TAB ---
            with ui.tab_panel(manual_tab).classes('p-0'):
                with ui.card().classes('w-full p-6 shadow-sm'):
                    ui.label('Manual Entry').classes('text-lg font-bold mb-4 text-gray-700')
                    
                    # Type Toggle
                    type_toggle = ui.toggle(['Expense', 'Income'], value='Expense').props('spread').classes('w-full mb-4')
                    
                    with ui.grid(columns=2).classes('w-full gap-4'):
                        # Date Picker
                        with ui.input('Date', value=date.today().strftime('%d.%m.%Y')) as date_field:
                            with date_field.add_slot('prepend'):
                                ui.icon('event').classes('cursor-pointer').on('click', lambda: date_menu.open())
                                with ui.menu() as date_menu:
                                    ui.date().bind_value(date_field)
                        
                        category_select = ui.select(
                            options=settings.EXPENSE_CATEGORIES,
                            label="Category", value="Lebensmittel"
                        ).classes('w-full')
                        
                        def update_categories():
                            if type_toggle.value == 'Expense':
                                category_select.options = settings.EXPENSE_CATEGORIES
                                category_select.value = settings.EXPENSE_CATEGORIES[0]
                            else:
                                category_select.options = settings.INCOME_CATEGORIES
                                category_select.value = settings.INCOME_CATEGORIES[0]
                        
                        type_toggle.on_value_change(update_categories)
                        
                        desc_input = ui.input(label="Description").classes('col-span-2 w-full')
                        
                        amount_input = ui.number(label="Amount", value=0.0, format="%.2f").classes('w-full')
                        currency_select = ui.select(options=settings.CURRENCIES, label="Currency", value="EUR").classes('w-full')
                    
                    def save_manual():
                        try:
                            expense_data = ExpenseCreate(
                                date=date.fromisoformat(date_field.value),
                                type=type_toggle.value.lower(),
                                category=category_select.value,
                                description=desc_input.value,
                                amount=amount_input.value,
                                currency=currency_select.value
                            )
                            db = next(get_db())
                            ExpenseService.create_expense(db, expense_data)
                            ui.notify('Transaction saved successfully!', type='positive')
                            # Reset
                            desc_input.value = ""
                            amount_input.value = 0.0
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')

                    ui.button('Save Transaction', on_click=save_manual).classes('mt-6 bg-blue-600 text-white w-full')
