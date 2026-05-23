from nicegui import ui
from datetime import date, datetime
from decimal import Decimal
from app.core.database import get_db
from app.services.expense_service import ExpenseService
from app.services.receipt_service import ReceiptService
from app.services.bank_ai_service import map_bank_categories, apply_recurring_mappings_to_entries
from app.db.models import Expense
from app.db.schemas import ExpenseCreate
from app.core.config import settings, USER_SETTINGS_PATH
from app.ui.layout import theme
from app.utils.logger import get_logger
from app.utils.bank_csv import parse_easybank_csv
import io
import os
import asyncio
import hashlib
import json

# Configure logging
logger = get_logger(__name__)

def add_expense_page():
    theme('add_expense')

    bank_import_history_path = os.path.join('app', 'data', 'bank_import_history.json')
    
    
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
            banking_tab = ui.tab('Banking Upload')
            
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

                            # Save receipt only (scan on demand for performance)
                            file_path = await ReceiptService.save_receipt(content, filename)
                            
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
                                                date_input = ui.input(label='Date', value=date.today().strftime('%Y-%m-%d')).props('type=date').classes('w-full')
                                                cat_input = ui.select(options=settings.EXPENSE_CATEGORIES, label="Category", value=settings.EXPENSE_CATEGORIES[0]).classes('w-full')
                                                desc_input = ui.input(label="Description", value='').classes('w-full sm:col-span-2')
                                                with ui.row().classes('w-full gap-2 sm:col-span-2'):
                                                    amount_input = ui.input(label="Amount", value=None).classes('flex-1') \
                                                        .on('input', sanitize_amount) \
                                                        .on('blur', format_on_blur)
                                                    curr_input = ui.select(options=settings.CURRENCIES, label="Currency", value=settings.DEFAULT_CURRENCY).classes('w-24')

                                            with ui.row().classes('w-full justify-center'):
                                                scan_btn = ui.button('Scan', icon='auto_fix_high', on_click=lambda: None) \
                                                    .props('outline color=blue').classes('mt-2 w-full sm:w-40')
                                    
                                    entry['inputs'] = {
                                        'date': date_input,
                                        'category': cat_input,
                                        'description': desc_input,
                                        'amount': amount_input,
                                        'currency': curr_input
                                    }
                                    entry['file_path'] = file_path
                                    entry['scan_btn'] = scan_btn
                                    active_receipts.append(entry)
                            
                            # Show Save All button
                            save_all_btn.classes(remove='hidden')
                            
                            async def run_scan(entry_ref):
                                entry_ref['scan_btn'].disable()
                                entry_ref['scan_btn'].props('loading')

                                try:
                                    result = await ReceiptService.scan_receipt(entry_ref['file_path'])

                                    entry_ref['inputs']['date'].set_value(result.date.strftime('%Y-%m-%d'))
                                    entry_ref['inputs']['category'].set_value(result.category)
                                    entry_ref['inputs']['description'].set_value(result.description)
                                    entry_ref['inputs']['amount'].set_value(f"{float(result.amount):.2f}")
                                    entry_ref['inputs']['currency'].set_value(result.currency)
                                    ui.notify('Receipt scanned! Review and save.', type='positive', timeout=5000)
                                except Exception as scan_err:
                                    ui.notify(f'Scan failed: {scan_err}', type='negative', timeout=5000)
                                finally:
                                    entry_ref['scan_btn'].enable()
                                    entry_ref['scan_btn'].props(remove='loading')

                            scan_btn.on('click', lambda e, entry_ref=entry: asyncio.create_task(run_scan(entry_ref)))
                            
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
                    
                    # Responsive Layout
                    with ui.column().classes('w-full gap-4'):
                        with ui.grid().classes('w-full gap-4 responsive-grid-2'):
                            # Date Picker
                            with ui.input('Date', value=date.today().strftime('%d.%m.%Y')).classes('w-full') as date_field:
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
                        
                        # Amount & Currency
                        with ui.grid().classes('w-full gap-4 responsive-grid-2'):
                            amount_input = ui.input(label="Amount", placeholder="0.00").classes('w-full') \
                                .on('input', sanitize_amount) \
                                .on('blur', format_on_blur)
                            currency_select = ui.select(options=settings.CURRENCIES, label="Currency", value=settings.DEFAULT_CURRENCY).classes('w-full')
                    
                    def save_manual():
                        try:
                            if not amount_input.value:
                                ui.notify('Please enter an amount', type='warning')
                                return

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

            # --- BANKING TAB ---
            with ui.tab_panel(banking_tab).classes('p-0'):
                with ui.card().classes('w-full p-6 shadow-sm'):
                    with ui.row().classes('w-full items-center justify-between sticky top-0 z-20 bg-white dark:bg-slate-900 py-1 mb-2'):
                        ui.label('Banking Upload (Easybank CSV)').classes('text-lg font-bold text-gray-700')
                        options_btn = ui.button('Options', icon='tune').props('outline color=blue')
                        with ui.menu().props('anchor="bottom end" self="top end"') as options_menu:
                            with ui.column().classes('p-3 gap-3 min-w-[260px]'):
                                ui.label('Import Options').classes('text-sm font-semibold text-gray-700')
                                skip_duplicates_toggle = ui.toggle(['Skip duplicates', 'Import all'], value='Skip duplicates') \
                                    .props('toggle-color=blue').classes('w-full')
                                ai_auto_switch = ui.switch('Auto AI Category Mapping', value=settings.BANK_AI_AUTO_MAPPING)
                                ai_auto_switch.on_value_change(lambda _: (
                                    setattr(settings, 'BANK_AI_AUTO_MAPPING', ai_auto_switch.value),
                                    persist_ai_auto_mapping(),
                                    update_mapping_visibility(),
                                ))
                                ui.button('Recurring Payments/Gehalt', icon='rule', on_click=lambda: recurring_dialog.open()) \
                                    .props('flat color=blue').classes('justify-start')
                                ui.button('Uploaded CSVs', icon='manage_history', on_click=lambda: uploaded_csvs_dialog.open()) \
                                    .props('flat color=blue').classes('justify-start')
                        options_btn.on('click', options_menu.open)

                    ui.label('Upload the Easybank Kontoauszug CSV to import all transactions from a month.').classes('text-sm text-gray-600 dark:text-gray-300 mb-2')

                    bank_state = {
                        'entries': [],
                        'csv_hash': None,
                        'duplicate_csv': False,
                        'allow_reimport': False,
                        'recurring_mappings': list(settings.BANK_RECURRING_MAPPINGS or []),
                    }

                    async def ask_overwrite_confirmation() -> bool:
                        with ui.dialog().props('persistent no-esc-dismiss no-backdrop-dismiss') as dialog, ui.card().classes('p-4 max-w-md'):
                            ui.label('This CSV was already uploaded. OVERWRITE?').classes('text-lg font-bold')
                            ui.label('Use "Yes" to reimport this CSV anyway.').classes('text-sm text-gray-600 mb-2')
                            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                ui.button('No', on_click=lambda: dialog.submit(False)).props('flat autofocus')
                                ui.button('Yes', on_click=lambda: dialog.submit(True)).classes('bg-blue-600 text-white')
                        return bool(await dialog)

                    def persist_recurring_mappings():
                        try:
                            os.makedirs(os.path.dirname(USER_SETTINGS_PATH), exist_ok=True)
                            data = {}
                            if os.path.exists(USER_SETTINGS_PATH):
                                with open(USER_SETTINGS_PATH, 'r') as f:
                                    data = json.load(f)
                            data['BANK_RECURRING_MAPPINGS'] = bank_state['recurring_mappings']
                            with open(USER_SETTINGS_PATH, 'w') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            settings.BANK_RECURRING_MAPPINGS = bank_state['recurring_mappings']
                        except Exception as exc:
                            logger.error(f"Failed to save recurring mappings: {exc}")
                            ui.notify(f'Failed to save recurring mappings: {exc}', type='negative')

                    def persist_ai_auto_mapping():
                        try:
                            os.makedirs(os.path.dirname(USER_SETTINGS_PATH), exist_ok=True)
                            data = {}
                            if os.path.exists(USER_SETTINGS_PATH):
                                with open(USER_SETTINGS_PATH, 'r') as f:
                                    data = json.load(f)
                            data['BANK_AI_AUTO_MAPPING'] = settings.BANK_AI_AUTO_MAPPING
                            with open(USER_SETTINGS_PATH, 'w') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                        except Exception as exc:
                            logger.error(f"Failed to save AI auto mapping setting: {exc}")
                            ui.notify(f'Failed to save AI auto mapping setting: {exc}', type='negative')

                    def remove_recurring_rule(index: int):
                        if 0 <= index < len(bank_state['recurring_mappings']):
                            bank_state['recurring_mappings'].pop(index)
                            persist_recurring_mappings()
                            ui.notify('Recurring mapping removed.', type='positive')
                            render_recurring_rules()

                    with ui.dialog() as recurring_dialog, ui.card().classes('w-full max-w-2xl p-4'):
                        ui.label('Recurring Payments / Gehalt Mapping').classes('text-lg font-bold text-gray-800')
                        ui.label('Rules here override AI: if description contains text, force category.').classes('text-sm text-gray-500')

                        recurring_rules_container = ui.column().classes('w-full gap-2 mt-2')
                        recurring_category_options = sorted(set(settings.EXPENSE_CATEGORIES + settings.INCOME_CATEGORIES))

                        def render_recurring_rules():
                            recurring_rules_container.clear()
                            with recurring_rules_container:
                                if not bank_state['recurring_mappings']:
                                    ui.label('No recurring mapping rules yet.').classes('text-sm text-gray-500')
                                for idx, rule in enumerate(bank_state['recurring_mappings']):
                                    with ui.row().classes('w-full items-center gap-2'):
                                        ui.label(f"contains: {rule.get('contains', '')}").classes('text-sm flex-1')
                                        ui.label(f"category: {rule.get('category', '')}").classes('text-sm flex-1')
                                        ui.button(icon='delete', on_click=lambda _, i=idx: remove_recurring_rule(i)) \
                                            .props('flat round dense color=red')

                        recurring_contains_input = ui.input('Description contains').classes('w-full')
                        recurring_category_select = ui.select(
                            options=recurring_category_options,
                            label='Category',
                            value=(recurring_category_options[0] if recurring_category_options else None),
                        ).classes('w-full')

                        def add_recurring_rule():
                            contains = (recurring_contains_input.value or '').strip()
                            category = (recurring_category_select.value or '').strip()
                            if not contains or not category:
                                ui.notify('Please fill both fields.', type='warning')
                                return
                            bank_state['recurring_mappings'].append({'contains': contains, 'category': category})
                            persist_recurring_mappings()
                            recurring_contains_input.set_value('')
                            if recurring_category_options:
                                recurring_category_select.set_value(recurring_category_options[0])
                            ui.notify('Recurring mapping added.', type='positive')
                            render_recurring_rules()

                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Close', on_click=recurring_dialog.close).props('flat')
                            ui.button('Add Rule', on_click=add_recurring_rule).classes('bg-blue-600 text-white')

                        render_recurring_rules()

                    def load_import_history_payload():
                        try:
                            if os.path.exists(bank_import_history_path):
                                with open(bank_import_history_path, 'r') as file_handle:
                                    data = json.load(file_handle)
                                hashes = set(data.get('hashes', []))
                                meta = data.get('meta', {}) if isinstance(data.get('meta', {}), dict) else {}
                                return hashes, meta
                        except Exception as exc:
                            logger.warning(f"Failed to load bank import history: {exc}")
                        return set(), {}

                    def load_import_history():
                        hashes, _ = load_import_history_payload()
                        return hashes

                    def save_import_history(hashes, meta=None):
                        try:
                            os.makedirs(os.path.dirname(bank_import_history_path), exist_ok=True)
                            if meta is None:
                                _, existing_meta = load_import_history_payload()
                                meta = existing_meta
                            # Keep metadata only for currently stored hashes
                            meta = {h: meta.get(h, {}) for h in hashes}
                            with open(bank_import_history_path, 'w') as file_handle:
                                json.dump({'hashes': sorted(hashes), 'meta': meta}, file_handle)
                        except Exception as exc:
                            logger.warning(f"Failed to save bank import history: {exc}")

                    def derive_import_months(entries):
                        months = sorted({entry.date.strftime('%Y-%m') for entry in entries if getattr(entry, 'date', None)})
                        return months

                    def compute_csv_hash(content_bytes: bytes) -> str:
                        return hashlib.sha256(content_bytes).hexdigest()

                    with ui.dialog() as uploaded_csvs_dialog, ui.card().classes('w-full max-w-2xl p-4'):
                        ui.label('Uploaded CSV Hashes').classes('text-lg font-bold text-gray-800')
                        ui.label('Delete hashes to allow reupload without overwrite notice.').classes('text-sm text-gray-500')

                        uploaded_hashes_container = ui.column().classes('w-full gap-2 mt-2')

                        def render_uploaded_hashes():
                            uploaded_hashes_container.clear()
                            hashes, meta = load_import_history_payload()
                            hashes = sorted(hashes)
                            with uploaded_hashes_container:
                                if not hashes:
                                    ui.label('No uploaded CSV hashes saved.').classes('text-sm text-gray-500')
                                for csv_hash in hashes:
                                    csv_meta = meta.get(csv_hash, {}) if isinstance(meta, dict) else {}
                                    months = csv_meta.get('months', [])
                                    imported_at = csv_meta.get('imported_at', '')
                                    months_label = ', '.join(months) if months else 'unknown month'
                                    with ui.row().classes('w-full items-center gap-2'):
                                        with ui.column().classes('flex-1 gap-0'):
                                            ui.label(csv_hash).classes('text-xs break-all')
                                            ui.label(f"months: {months_label} | imported: {imported_at or 'unknown'}").classes('text-[11px] text-gray-500')
                                        ui.button(icon='delete', on_click=lambda _, h=csv_hash: remove_uploaded_hash(h)) \
                                            .props('flat round dense color=red')

                        def remove_uploaded_hash(csv_hash: str):
                            hashes, meta = load_import_history_payload()
                            if csv_hash in hashes:
                                hashes.remove(csv_hash)
                                if csv_hash in meta:
                                    meta.pop(csv_hash, None)
                                save_import_history(hashes, meta)
                                ui.notify('Uploaded CSV hash removed.', type='positive')
                                render_uploaded_hashes()

                        def clear_uploaded_hashes():
                            save_import_history(set(), {})
                            ui.notify('All uploaded CSV hashes removed.', type='positive')
                            render_uploaded_hashes()

                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Close', on_click=uploaded_csvs_dialog.close).props('flat')
                            ui.button('Clear All', on_click=clear_uploaded_hashes).props('outline color=red')

                        render_uploaded_hashes()

                    async def handle_bank_upload(e):
                        try:
                            content = getattr(e, 'content', None)
                            filename = getattr(e, 'name', None)

                            if hasattr(e, 'file'):
                                if not filename and hasattr(e.file, 'name'):
                                    filename = e.file.name
                                if content is None:
                                    if hasattr(e.file, '_data'):
                                        content = e.file._data
                                    elif hasattr(e.file, 'read'):
                                        file_data = await e.file.read()
                                        content = file_data

                            if content is None:
                                ui.notify('Error: Upload content missing.', type='negative', timeout=5000)
                                return

                            csv_hash = compute_csv_hash(content)
                            history = load_import_history()
                            bank_state['csv_hash'] = csv_hash
                            bank_state['duplicate_csv'] = csv_hash in history
                            bank_state['allow_reimport'] = False

                            if bank_state['duplicate_csv']:
                                confirmed = await ask_overwrite_confirmation()
                                if confirmed:
                                    bank_state['allow_reimport'] = True
                                    bank_state['duplicate_csv'] = False
                                else:
                                    bank_state['allow_reimport'] = False

                            entries, errors, transfer_count = parse_easybank_csv(content)
                            apply_recurring_mappings_to_entries(entries)
                            bank_state['entries'] = entries
                            update_bank_table()

                            if csv_hash in history and bank_state['allow_reimport']:
                                ui.notify('Reimport enabled for this already uploaded CSV.', type='warning', timeout=7000)
                            elif bank_state['duplicate_csv']:
                                ui.notify('This CSV was already imported. Import is disabled.', type='warning', timeout=7000)
                            elif errors:
                                ui.notify(f"Loaded with {len(errors)} row errors.", type='warning', timeout=7000)
                            else:
                                ui.notify('CSV loaded successfully.', type='positive', timeout=5000)
                            if transfer_count:
                                ui.notify(f'Detected {transfer_count} account transfer(s) — they will be imported as type "transfer".', type='info', timeout=7000)

                            if settings.BANK_AI_AUTO_MAPPING:
                                ai_preview_btn.disable()
                                ai_preview_btn.props('loading')
                                try:
                                    mapping = await asyncio.to_thread(map_bank_categories, bank_state['entries'])
                                    changed = 0
                                    for idx, entry in enumerate(bank_state['entries'], start=1):
                                        proposed = mapping.get(idx)
                                        if proposed and proposed != entry.category:
                                            entry.category = proposed
                                            changed += 1
                                    update_bank_table()
                                    if changed > 0:
                                        ui.notify(f'AI categories auto-applied: {changed} changes.', type='positive')
                                    else:
                                        ui.notify('AI found no category changes.', type='warning')
                                except Exception as exc:
                                    logger.error(f"Auto AI mapping failed: {exc}")
                                    ui.notify(f'Auto AI mapping failed: {exc}', type='negative')
                                finally:
                                    ai_preview_btn.enable()
                                    ai_preview_btn.props(remove='loading')

                        except Exception as err:
                            ui.notify(f'Error reading CSV: {err}', type='negative', timeout=7000)
                        finally:
                            bank_uploader.reset()

                    bank_uploader = ui.upload(
                        on_upload=handle_bank_upload,
                        label='Drop CSV here',
                        auto_upload=True,
                        multiple=False,
                    ).props('color=bg-blue-600 accept=".csv"').classes('w-full mt-4')

                    summary_label = ui.label('No data loaded yet.').classes('text-sm text-gray-500 mt-4')

                    with ui.element('div').classes('w-full overflow-x-auto mt-4'):
                        bank_table = ui.aggrid({
                            'columnDefs': [
                                {
                                    'headerName': '',
                                    'field': 'select',
                                    'checkboxSelection': True,
                                    'headerCheckboxSelection': True,
                                    'width': 50,
                                    'editable': False,
                                    'sortable': False,
                                },
                                {'headerName': 'Date', 'field': 'date', 'editable': True, 'width': 120},
                                {'headerName': 'Description', 'field': 'description', 'editable': True, 'width': 260},
                                {
                                    'headerName': 'Amount',
                                    'field': 'amount',
                                    'editable': True,
                                    'width': 110,
                                    'valueFormatter': 'Number(value).toFixed(2)',
                                },
                                {
                                    'headerName': 'Currency',
                                    'field': 'currency',
                                    'editable': True,
                                    'cellEditor': 'agSelectCellEditor',
                                    'cellEditorParams': {'values': settings.CURRENCIES},
                                    'width': 110,
                                },
                                {
                                    'headerName': 'Type',
                                    'field': 'type',
                                    'editable': True,
                                    'cellEditor': 'agSelectCellEditor',
                                    'cellEditorParams': {'values': ['expense', 'income', 'transfer']},
                                    'width': 110,
                                },
                                {
                                    'headerName': 'Category',
                                    'field': 'category',
                                    'editable': True,
                                    'width': 170,
                                    'cellClassRules': {
                                        'text-red-600 font-bold': "data.ai_preview && data.ai_preview !== ''",
                                        'text-blue-600': "data.type === 'transfer'",
                                    },
                                    ':cellEditorSelector': f"""(params) => {{
                                        if (params.data.type === 'income') {{
                                            return {{
                                                component: 'agSelectCellEditor',
                                                params: {{ values: {json.dumps(settings.INCOME_CATEGORIES)} }}
                                            }};
                                        }}
                                        if (params.data.type === 'transfer') {{
                                            return {{
                                                component: 'agSelectCellEditor',
                                                params: {{ values: {json.dumps(sorted(set(settings.INCOME_CATEGORIES + settings.EXPENSE_CATEGORIES)))} }}
                                            }};
                                        }}
                                        return {{
                                            component: 'agSelectCellEditor',
                                            params: {{ values: {json.dumps(settings.EXPENSE_CATEGORIES)} }}
                                        }};
                                    }}"""
                                },
                                {
                                    'headerName': 'AI Preview',
                                    'field': 'ai_preview',
                                    'editable': False,
                                    'width': 170,
                                    'cellClassRules': {
                                        'text-green-700 font-bold': "data.ai_preview && data.ai_preview !== ''",
                                    },
                                },
                                {'headerName': 'Duplicate', 'field': 'duplicate', 'editable': False, 'width': 110},
                            ],
                            'rowData': [],
                            'pagination': False,
                            'rowSelection': 'multiple',
                            'domLayout': 'normal',
                            'defaultColDef': {
                                'resizable': True,
                                'sortable': True,
                            },
                        }).classes('min-w-[980px] shadow-sm h-[420px] relative z-0')
                    ai_state = {'proposed': {}}

                    def refresh_duplicate_flags():
                        if not bank_state['entries']:
                            return

                        db = next(get_db())
                        for entry in bank_state['entries']:
                            exists = db.query(Expense).filter(
                                Expense.date == entry.date,
                                Expense.type == entry.entry_type,
                                Expense.description == entry.description,
                                Expense.amount == entry.amount,
                                Expense.currency == entry.currency,
                            ).first()
                            entry.is_duplicate = bool(exists)

                    def get_entry_by_id(row_id: int):
                        if not row_id:
                            return None
                        idx = int(row_id) - 1
                        if idx < 0 or idx >= len(bank_state['entries']):
                            return None
                        return bank_state['entries'][idx]

                    async def handle_bank_cell_value_change(e):
                        row_id = int(e.args['data']['id'])
                        field = e.args['colId']
                        new_value = e.args['newValue']

                        entry = get_entry_by_id(row_id)
                        if not entry:
                            return

                        try:
                            if field == 'date':
                                entry.date = datetime.strptime(str(new_value), '%Y-%m-%d').date()
                            elif field == 'amount':
                                entry.amount = Decimal(str(new_value).replace(',', '.'))
                            elif field == 'description':
                                entry.description = str(new_value or '').strip()
                            elif field == 'currency':
                                entry.currency = str(new_value)
                            elif field == 'type':
                                entry.entry_type = str(new_value)
                                if entry.entry_type == 'transfer':
                                    allowed = sorted(set(settings.INCOME_CATEGORIES + settings.EXPENSE_CATEGORIES))
                                else:
                                    allowed = settings.INCOME_CATEGORIES if entry.entry_type == 'income' else settings.EXPENSE_CATEGORIES
                                if entry.category not in allowed:
                                    entry.category = allowed[0]
                            elif field == 'category':
                                entry.category = str(new_value)
                            else:
                                return

                            ai_state['proposed'].pop(row_id, None)
                            update_bank_table()
                            # Keep the edited row in view after re-render to avoid jumping to top.
                            bank_table.run_grid_method('ensureIndexVisible', row_id - 1, 'middle')
                        except Exception as exc:
                            ui.notify(f'Invalid value: {exc}', type='negative')
                            update_bank_table()
                            bank_table.run_grid_method('ensureIndexVisible', row_id - 1, 'middle')

                    def update_bank_table():
                        refresh_duplicate_flags()
                        rows = []
                        total_income = 0
                        total_expense = 0
                        total_transfers = 0
                        for idx, entry in enumerate(bank_state['entries'], start=1):
                            amount_value = float(entry.amount)
                            if entry.entry_type == 'income':
                                total_income += amount_value
                            elif entry.entry_type == 'transfer':
                                total_transfers += amount_value
                            else:
                                total_expense += amount_value
                            proposed = ai_state['proposed'].get(idx)
                            rows.append({
                                'id': idx,
                                'date': entry.date.strftime('%Y-%m-%d'),
                                'description': entry.description,
                                'amount': amount_value,
                                'currency': entry.currency,
                                'type': entry.entry_type,
                                'category': entry.category,
                                'ai_preview': proposed if proposed and proposed != entry.category else '',
                                'duplicate': 'Yes' if getattr(entry, 'is_duplicate', False) else '',
                            })

                        bank_table.options['rowData'] = rows
                        bank_table.update()
                        duplicate_notice = ' (CSV already imported)' if bank_state.get('duplicate_csv') else ''
                        summary_parts = [
                            f"Loaded {len(rows)} transactions{duplicate_notice}.",
                            f"Income: {total_income:.2f} EUR",
                            f"Expense: {total_expense:.2f} EUR",
                        ]
                        if total_transfers:
                            summary_parts.append(f"Transfers: {total_transfers:.2f} EUR")
                        summary_label.text = " ".join(summary_parts)
                        import_btn.disable() if bank_state.get('duplicate_csv') else import_btn.enable()

                    bank_table.on('cellValueChanged', handle_bank_cell_value_change)

                    async def generate_ai_preview():
                        if not bank_state['entries']:
                            ui.notify('No transactions loaded.', type='warning')
                            return

                        ui.notify(f"Generating AI preview via {settings.AI_PROVIDER}...", type='info', timeout=2500)
                        ai_preview_btn.disable()
                        ai_preview_btn.props('loading')

                        try:
                            mapping = await asyncio.to_thread(map_bank_categories, bank_state['entries'])
                            ai_state['proposed'] = {}
                            changed = 0
                            for idx, entry in enumerate(bank_state['entries'], start=1):
                                proposed = mapping.get(idx)
                                if proposed and proposed != entry.category:
                                    changed += 1
                                    ai_state['proposed'][idx] = proposed

                            update_bank_table()
                            if changed > 0:
                                apply_ai_btn.enable()
                                ui.notify(f'AI preview ready: {changed} proposed changes.', type='positive')
                            else:
                                apply_ai_btn.disable()
                                ui.notify('AI preview found no category changes.', type='warning')
                        except Exception as exc:
                            logger.error(f"AI mapping failed: {exc}")
                            ui.notify(f'AI mapping failed: {exc}', type='negative')
                        finally:
                            ai_preview_btn.enable()
                            ai_preview_btn.props(remove='loading')

                    def apply_ai_mapping():
                        if not ai_state['proposed']:
                            ui.notify('No AI preview available.', type='warning')
                            return

                        updated = 0
                        for idx, entry in enumerate(bank_state['entries'], start=1):
                            proposed = ai_state['proposed'].get(idx)
                            if proposed and proposed != entry.category:
                                entry.category = proposed
                                updated += 1

                        ai_state['proposed'] = {}
                        apply_ai_btn.disable()
                        update_bank_table()
                        ui.notify(f'Applied {updated} AI category changes.', type='positive')

                    def update_mapping_visibility():
                        if settings.BANK_AI_AUTO_MAPPING:
                            ai_preview_btn.classes(add='hidden')
                            apply_ai_btn.classes(add='hidden')
                        else:
                            ai_preview_btn.classes(remove='hidden')
                            apply_ai_btn.classes(remove='hidden')

                    def import_bank_entries():
                        if not bank_state['entries']:
                            ui.notify('No transactions loaded.', type='warning')
                            return

                        if bank_state.get('duplicate_csv') and not bank_state.get('allow_reimport'):
                            ui.notify('This CSV was already imported.', type='warning')
                            return

                        history = load_import_history()
                        if bank_state.get('csv_hash') in history and not bank_state.get('allow_reimport'):
                            ui.notify('This CSV was already imported.', type='warning')
                            bank_state['duplicate_csv'] = True
                            update_bank_table()
                            return

                        saved_count = 0
                        skipped_duplicates = 0
                        errors = 0
                        db = next(get_db())
                        for entry in bank_state['entries']:
                            try:
                                if skip_duplicates_toggle.value == 'Skip duplicates':
                                    exists = db.query(Expense).filter(
                                        Expense.date == entry.date,
                                        Expense.type == entry.entry_type,
                                        Expense.description == entry.description,
                                        Expense.amount == entry.amount,
                                        Expense.currency == entry.currency,
                                    ).first()
                                    if exists:
                                        skipped_duplicates += 1
                                        continue

                                expense_data = ExpenseCreate(
                                    date=entry.date,
                                    type=entry.entry_type,
                                    category=entry.category,
                                    description=entry.description,
                                    amount=entry.amount,
                                    currency=entry.currency,
                                )
                                ExpenseService.create_expense(db, expense_data)
                                saved_count += 1
                            except Exception as exc:
                                errors += 1
                                logger.error(f"Bank CSV import failed: {exc}")

                        ui.notify(f'Imported {saved_count} transactions.', type='positive')
                        if skipped_duplicates:
                            ui.notify(f'Skipped {skipped_duplicates} duplicate rows.', type='warning')
                        if errors:
                            ui.notify(f'Failed to import {errors} rows.', type='warning')

                        if bank_state.get('csv_hash'):
                            history.add(bank_state['csv_hash'])
                            _, history_meta = load_import_history_payload()
                            history_meta[bank_state['csv_hash']] = {
                                'months': derive_import_months(bank_state['entries']),
                                'imported_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            }
                            save_import_history(history, history_meta)

                        bank_state['entries'] = []
                        bank_state['csv_hash'] = None
                        bank_state['duplicate_csv'] = False
                        bank_state['allow_reimport'] = False
                        update_bank_table()

                    async def remove_selected_preview_rows():
                        selected_rows = await bank_table.get_selected_rows()
                        if not selected_rows:
                            ui.notify('No rows selected.', type='warning')
                            return

                        selected_ids = {int(row.get('id')) for row in selected_rows if row.get('id') is not None}
                        if not selected_ids:
                            ui.notify('No rows selected.', type='warning')
                            return

                        bank_state['entries'] = [
                            entry for idx, entry in enumerate(bank_state['entries'], start=1)
                            if idx not in selected_ids
                        ]
                        # Reset AI proposals because row indexing changes after deletion.
                        ai_state['proposed'] = {}
                        apply_ai_btn.disable()
                        update_bank_table()
                        ui.notify(f'Removed {len(selected_ids)} rows from preview.', type='positive')

                    with ui.row().classes('w-full gap-3 mt-4 items-center flex-wrap relative z-10'):
                        ai_preview_btn = ui.button('Generate AI Preview', on_click=generate_ai_preview, icon='auto_fix_high') \
                            .classes('bg-blue-600 text-white')
                        apply_ai_btn = ui.button('Apply AI Changes', on_click=apply_ai_mapping) \
                            .classes('bg-green-600 text-white')
                        apply_ai_btn.disable()
                        ui.button('Delete Selected from Preview', on_click=remove_selected_preview_rows, icon='delete') \
                            .props('outline color=red').classes('text-red-600')
                        import_btn = ui.button('Import All', on_click=import_bank_entries, icon='upload') \
                            .classes('bg-green-600 text-white')
                        ui.button(
                            'Clear',
                            on_click=lambda: (
                                bank_state.update({'entries': [], 'csv_hash': None, 'duplicate_csv': False, 'allow_reimport': False}),
                                ai_state.update({'proposed': {}}),
                                update_bank_table(),
                            )
                        ) \
                            .props('outline').classes('text-gray-600')

                    update_mapping_visibility()

