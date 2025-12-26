from nicegui import ui
from datetime import date, datetime
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.services.receipt_service import ReceiptService
from app.db.schemas import ExpenseCreate
from app.core.config import settings
from app.ui.layout import theme, BREAKPOINT
from app.utils.logger import get_logger
import io
import os

# Configure logging
logger = get_logger(__name__)

def add_expense_page():
    theme('add_expense')
    
    # --- Custom CSS ---
    
    ## center and enlarge the upload button
    ui.add_css('''
        .receipt-uploader .q-uploader__header-content {
            justify-content: center !important;
        }
        .receipt-uploader .q-uploader__header .q-icon {
            font-size: 3rem !important;
        }
        .receipt-uploader .q-uploader__header {
            padding: 5px !important;
        }
        
        /* Ensure receipt preview is centered and behaves consistently */
        .receipt-card .preview-container {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
        }
        .receipt-card .preview-image,
        .receipt-card .preview-container img,
        .receipt-card .preview-container .q-img {
            display: block !important;
            margin-left: auto !important;
            margin-right: auto !important;
            max-width: 100% !important;
            width: 180px !important;
            height: 120px !important;
            object-fit: contain !important;
        }

        /* On desktop, stack and center the preview above the form fields (page-scoped) */
        @media (min-width: {BREAKPOINT}px) {
            .receipt-card .responsive-row {
                flex-direction: column !important;
                align-items: center !important;
            }
            .receipt-card .preview-container {
                width: 100% !important;
                margin-bottom: 0.5rem !important;
            }
            .receipt-card .preview-container img,
            .receipt-card .preview-image,
            .receipt-card .preview-container .q-img {
                display: block !important;
                width: 100% !important;            
                max-width: 500px !important;
                height: auto !important;
                max-height: 160px !important;
                object-fit: contain !important;
            }
            .receipt-card .responsive-row > .q-column,
            .receipt-card .responsive-row > .q-row,
            .receipt-card .responsive-row > .flex-grow {
                width: 100% !important;
            }
        }

    ''')
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6'):
        ui.label('➕ Add New Expense').classes('text-2xl font-bold text-gray-800')
        
        # --- Helpers ---
        def sanitize_amount(e):
            # Only update if comma is present to avoid race conditions while typing digits
            val = e.value
            if val and ',' in val:
                e.sender.set_value(val.replace(',', '.'))

        def format_on_blur(e):
            val = e.sender.value
            if not val: return
            
            # Clean up: allow only digits and one dot
            cleaned = ''
            dot_seen = False
            for c in val.replace(',', '.'):
                if c.isdigit():
                    cleaned += c
                elif c == '.' and not dot_seen:
                    cleaned += c
                    dot_seen = True
            
            try:
                if cleaned:
                    num = float(cleaned)
                    e.sender.set_value(f"{abs(num):.2f}")
                else:
                    e.sender.set_value(None)
            except ValueError:
                e.sender.set_value(None)
                
        # --- Main Content ---

        with ui.tabs().classes('w-full text-blue-600').props('align="left"') as tabs:
            ai_tab = ui.tab('AI Upload')
            manual_tab = ui.tab('Manual Entry')
            
        with ui.tab_panels(tabs, value=ai_tab).classes('w-full bg-transparent'):
            
            # --- AI TAB ---
            with ui.tab_panel(ai_tab).classes('p-0'):
                with ui.card().classes('w-full p-6 shadow-sm'):
                    ui.label('Upload Receipts').classes('text-lg font-bold mb-4 text-gray-700')
                    
                    # Image Preview & Dialog
                    with ui.dialog() as image_dialog, ui.card().classes('w-full max-w-5xl p-0 overflow-hidden'):
                        large_image = ui.image().classes('w-full max-h-[80vh] object-contain')
                        with ui.row().classes('w-full justify-center p-2 bg-gray-100'):
                            ui.button('Close', on_click=image_dialog.close).props('flat')

                    def show_full_image(src):
                        large_image.set_source(src)
                        image_dialog.open()

                    # Container for receipt cards
                    receipts_container = ui.column().classes('w-full gap-4 mt-4')
                    
                    # State tracking
                    active_receipts = []
                    upload_state = {'active_count': 0, 'notification': None}

                    def remove_receipt(entry):
                        if entry in active_receipts:
                            active_receipts.remove(entry)
                        entry['card'].delete()
                        if not active_receipts:
                            save_all_btn.classes(add='hidden')

                    async def save_all():
                        saved_count = 0
                        errors = 0
                        # Iterate over a copy since this list might be modified
                        for entry in list(active_receipts):
                            try:
                                inputs = entry['inputs']
                                # Sanitize amount (replace comma with dot)
                                amount_val = str(inputs['amount'].value).replace(',', '.')
                                
                                expense_data = ExpenseCreate(
                                    date=date.fromisoformat(inputs['date'].value),
                                    category=inputs['category'].value,
                                    description=inputs['description'].value,
                                    amount=amount_val,
                                    currency=inputs['currency'].value
                                )
                                db = next(get_db())
                                ExpenseService.create_expense(db, expense_data)
                                remove_receipt(entry)
                                saved_count += 1
                            except Exception as e:
                                errors += 1
                                ui.notify(f'Error saving item: {str(e)}', type='negative')
                        
                        if saved_count > 0:
                            ui.notify(f'Saved {saved_count} expenses successfully!', type='positive')
                        if errors == 0 and saved_count > 0:
                            save_all_btn.classes(add='hidden')

                    save_all_btn = ui.button('Save All', on_click=save_all, icon='save') \
                        .classes('w-full bg-green-600 text-white mt-4 hidden')

                    async def handle_upload(e):
                        logger.info(f"File Upload triggered.")
                        
                        upload_state['active_count'] += 1
                        if upload_state['notification'] is None:
                            upload_state['notification'] = ui.notification('Processing receipts...', type='info', spinner=True, timeout=None)
                        
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
                                ui.notify("Error: Upload content missing.", type='negative', timeout=5000)
                                return

                            # Delegate processing to ReceiptService
                            result, file_path = await ReceiptService.process_receipt(content, filename)
                            
                            # Create UI Card for this receipt
                            with receipts_container:
                                with ui.card().classes('w-full p-4 shadow-sm border border-gray-200 relative receipt-card') as card:
                                    entry = {'card': card}
                                    
                                    # Close Button
                                    ui.button(icon='close', on_click=lambda: remove_receipt(entry)) \
                                        .props('flat round dense color=red aria-label="Remove receipt" title="Remove receipt"').classes('absolute top-2 right-2 z-10')
                                    
                                    with ui.row().classes('w-full gap-4 responsive-row items-center sm:items-start'):
                                        # Image Preview
                                        with ui.element('div').classes('w-full preview-container'):
                                            # Construct the web path through the helper (serves as single source of truth)
                                            filename = os.path.basename(file_path)
                                            web_path = ReceiptService.get_public_url(filename)
                                            # Use page-scoped classes to control size via CSS
                                            ui.image(web_path).props('alt="Receipt preview"').classes('preview-image bg-gray-50 rounded cursor-pointer border border-gray-100') \
                                                .on('click', lambda src=web_path: show_full_image(src))
                                        
                                        # Form Fields
                                        with ui.column().classes('flex-grow gap-2 w-full'):
                                            # Mobile: Stack fields vertically, Desktop: Use grid
                                            with ui.grid().classes('w-full gap-2 responsive-grid-2'):
                                                date_input = ui.input(label='Date', value=result.date.strftime('%Y-%m-%d')).props('type=date').classes('w-full')
                                                cat_input = ui.select(options=settings.EXPENSE_CATEGORIES, label="Category", value=result.category).classes('w-full')
                                                desc_input = ui.input(label="Description", value=result.description).classes('w-full sm:col-span-2')
                                                with ui.row().classes('w-full gap-2 sm:col-span-2'):
                                                    amount_input = ui.input(label="Amount", value=f"{float(result.amount):.2f}").classes('flex-1') \
                                                        .on('input', sanitize_amount) \
                                                        .on('blur', format_on_blur)
                                                    curr_input = ui.select(options=settings.CURRENCIES, label="Currency", value=result.currency).classes('w-24')
                                    
                                    entry['inputs'] = {
                                        'date': date_input,
                                        'category': cat_input,
                                        'description': desc_input,
                                        'amount': amount_input,
                                        'currency': curr_input
                                    }
                                    active_receipts.append(entry)
                            
                            # Show Save All button
                            save_all_btn.classes(remove='hidden')
                            
                            ui.notify('Receipt scanned! Review and save.', type='positive', timeout=5000)
                            
                        except Exception as err:
                            ui.notify(f'Error scanning receipt: {str(err)}', type='negative', timeout=5000)
                            logger.error(f"Error in handle_upload: {err}", exc_info=True)
                        finally:
                            upload_state['active_count'] -= 1
                            if upload_state['active_count'] <= 0:
                                if upload_state['notification']:
                                    upload_state['notification'].dismiss()
                                    upload_state['notification'] = None
                                uploader.reset()

                    uploader = ui.upload(on_upload=handle_upload, label="Drop receipt images here", auto_upload=True, multiple=True) \
                        .props('color=bg-blue-600 accept=".jpg, .jpeg, .png, .heic" no-thumbnails') \
                        .classes('w-full mb-6 receipt-uploader')


            # --- MANUAL TAB ---
            with ui.tab_panel(manual_tab).classes('p-0'):
                with ui.card().classes('w-full p-6 shadow-sm'):
                    ui.label('Manual Entry').classes('text-lg font-bold mb-4 text-gray-700')
                    
                    # Type Toggle
                    type_toggle = ui.toggle(['Expense', 'Income'], value='Expense') \
                        .props('spread toggle-color=red') \
                        .classes('w-full mb-4')
                    
                    # Mobile Layout (stacked)
                    with ui.column().classes('mobile-layout mobile-only w-full gap-4'):
                        # Date Picker
                        with ui.input('Date', value=date.today().strftime('%d.%m.%Y')) as date_field:
                            with date_field.add_slot('prepend'):
                                ui.icon('event').classes('cursor-pointer').on('click', lambda: date_menu.open())
                                with ui.menu() as date_menu:
                                    ui.date().bind_value(date_field).props('mask="DD.MM.YYYY"')
                        
                        # Category Select
                        category_select = ui.select(
                            options=settings.EXPENSE_CATEGORIES,
                            label="Category", value="Lebensmittel"
                        ).classes('w-full')
                        
                        def update_categories():
                            if type_toggle.value == 'Expense':
                                category_select.options = settings.EXPENSE_CATEGORIES
                                category_select.value = settings.EXPENSE_CATEGORIES[0]
                                type_toggle.props('toggle-color=red')
                            else:
                                category_select.options = settings.INCOME_CATEGORIES
                                category_select.value = settings.INCOME_CATEGORIES[0]
                                type_toggle.props('toggle-color=green')
                        
                        type_toggle.on_value_change(update_categories)
                        
                        # Description
                        desc_input = ui.input(label="Description").classes('w-full')
                        
                        # Amount
                        amount_input = ui.input(label="Amount", placeholder="0.00").classes('w-full') \
                            .on('input', sanitize_amount) \
                            .on('blur', format_on_blur)
                        
                        # Currency
                        currency_select = ui.select(options=settings.CURRENCIES, label="Currency", value=settings.DEFAULT_CURRENCY).classes('w-full')
                    
                    # Desktop Layout (rows)
                    with ui.column().classes('desktop-layout desktop-only w-full gap-4'):
                        with ui.row().classes('w-full gap-4 flex-wrap'):
                            # Date Picker
                            with ui.input('Date', value=date.today().strftime('%d.%m.%Y')).classes('flex-1 min-w-0') as date_field:
                                with date_field.add_slot('prepend'):
                                    ui.icon('event').classes('cursor-pointer').on('click', lambda: date_menu.open())
                                    with ui.menu() as date_menu:
                                        ui.date().bind_value(date_field).props('mask="DD.MM.YYYY"')
                            # Category Select
                            category_select = ui.select(
                                options=settings.EXPENSE_CATEGORIES,
                                label="Category", value="Lebensmittel"
                            ).classes('flex-1 min-w-0')
                        
                        def update_categories():
                            if type_toggle.value == 'Expense':
                                category_select.options = settings.EXPENSE_CATEGORIES
                                category_select.value = settings.EXPENSE_CATEGORIES[0]
                                type_toggle.props('toggle-color=red')
                            else:
                                category_select.options = settings.INCOME_CATEGORIES
                                category_select.value = settings.INCOME_CATEGORIES[0]
                                type_toggle.props('toggle-color=green')
                        
                        type_toggle.on_value_change(update_categories)
                        
                        # Description
                        desc_input = ui.input(label="Description").classes('w-full')
                        
                        # Amount & Currency
                        with ui.row().classes('w-full gap-4 flex-wrap'):
                            amount_input = ui.input(label="Amount", placeholder="0.00").classes('flex-1 min-w-0') \
                                .on('input', sanitize_amount) \
                                .on('blur', format_on_blur)
                            currency_select = ui.select(options=settings.CURRENCIES, label="Currency", value=settings.DEFAULT_CURRENCY).classes('flex-1 min-w-0')
                    
                    def save_manual():
                        try:
                            # Sanitize amount (replace comma with dot)
                            amount_val = str(amount_input.value).replace(',', '.')

                            expense_data = ExpenseCreate(
                                date=datetime.strptime(date_field.value, '%d.%m.%Y').date(),
                                type=type_toggle.value.lower(),
                                category=category_select.value,
                                description=desc_input.value,
                                amount=amount_val,
                                currency=currency_select.value
                            )
                            db = next(get_db())
                            ExpenseService.create_expense(db, expense_data)
                            ui.notify('Transaction saved successfully!', type='positive')
                            # Reset
                            desc_input.value = ""
                            amount_input.value = None
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')

                    ui.button('Save Transaction', on_click=save_manual, icon='save').classes('mt-6 bg-blue-600 text-white w-full')
