from nicegui import ui
from app.core.config import settings, USER_SETTINGS_PATH
from app.ui.layout import theme
import json
import os

class ListEditor:
    sortable_loaded = False

    def __init__(self, label, initial_items):
        self.items = list(initial_items) # Copy
        self.label = label
        
    def render(self):
        with ui.column().classes('w-full gap-2 p-2 border rounded-lg bg-gray-50'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(self.label).classes('text-sm font-bold text-gray-600')
                ui.label('Drag to reorder').classes('text-xs text-gray-400 italic')
            
            # Container for sortable items
            self.chip_container = ui.element('div').classes('w-full gap-2 flex flex-wrap items-center')
            self.update_chips()
            
            # Enable SortableJS on the container (load once)
            if not ListEditor.sortable_loaded:
                ui.add_head_html('<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>')
                ListEditor.sortable_loaded = True
            
            # Initialize SortableJS
            ui.run_javascript(f'''
                new Sortable(getElement({self.chip_container.id}), {{
                    animation: 150,
                    ghostClass: 'opacity-50',
                    onEnd: function (evt) {{
                        // Emit custom event to Python
                        emitEvent('reorder_{self.chip_container.id}', {{
                            oldIndex: evt.oldIndex,
                            newIndex: evt.newIndex
                        }});
                    }}
                }});
            ''')
            
            # Listen for the reorder event
            ui.on(f'reorder_{self.chip_container.id}', self.handle_reorder)
            
            with ui.row().classes('w-full items-center gap-2'):
                self.new_item_input = ui.input(placeholder='Add item...').classes('flex-grow dense') \
                    .on('keydown.enter', self.add_item)
                ui.button(icon='add', on_click=self.add_item).props('flat round dense color=green')

    def handle_reorder(self, e):
        old_index = e.args['oldIndex']
        new_index = e.args['newIndex']
        if old_index is not None and new_index is not None:
            item = self.items.pop(old_index)
            self.items.insert(new_index, item)
            # Force re-render to ensure UI state (classes) matches server state
            self.update_chips()

    def update_chips(self):
        self.chip_container.clear()
        with self.chip_container:
            for item in self.items:
                # Chip-like styling
                with ui.element('div').classes('flex items-center gap-1 bg-blue-100 rounded-full pl-3 pr-1 py-1 cursor-move select-none hover:bg-blue-200 transition-colors'):
                    ui.label(item).classes('text-blue-900 text-sm font-medium')
                    ui.icon('close').classes('cursor-pointer text-red-500 hover:text-red-700 text-xs ml-1') \
                        .on('click', lambda _, val=item: self.remove_item(val))

    def add_item(self):
        val = self.new_item_input.value.strip()
        if val and val not in self.items:
            self.items.append(val)
            self.new_item_input.value = ""
            self.update_chips()

    # NOTE: Deleting an item only removes it from the list of available options and persists it writing into .env.
    # It does not affect historical records that already use this value.
    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            self.update_chips()

def settings_page():
    theme('settings')
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6 pb-24'):
        ui.label('⚙️ Settings').classes('text-2xl font-bold text-gray-800')
        
        # --- AI Configuration ---
        with ui.card().classes('w-full p-6 shadow-sm gap-4'):
            ui.label('🤖 AI Configuration').classes('text-lg font-bold text-gray-700')
            
            with ui.grid(columns=1).classes('w-full gap-4'):
                ai_provider = ui.select(
                    options=['gemini', 'openai', 'testing'],
                    label='AI Provider',
                    value=settings.AI_PROVIDER
                ).classes('w-full')
                with ai_provider:
                    ui.tooltip('Choose the AI provider used to scan receipts.').props('anchor="bottom left" self="top left"')
                
                google_key = ui.input(
                    label='Google API Key',
                    value=settings.GOOGLE_API_KEY,
                    password=True
                ).props('reveal').classes('w-full') \
                 .bind_visibility_from(ai_provider, 'value', backward=lambda v: v == 'gemini')
                with google_key:
                    ui.tooltip('API key for Google Generative AI / Gemini.').props('anchor="bottom left" self="top left"')
                
                openai_key = ui.input(
                    label='OpenAI API Key',
                    value=settings.OPENAI_API_KEY,
                    password=True
                ).props('reveal').classes('w-full') \
                 .bind_visibility_from(ai_provider, 'value', backward=lambda v: v == 'openai')
                with openai_key:
                    ui.tooltip('API key for OpenAI.').props('anchor="bottom left" self="top left"')

        # --- App Constants (Lists) ---
        with ui.card().classes('w-full p-6 shadow-sm gap-4'):
            ui.label('📋 App Constants').classes('text-lg font-bold text-gray-700')
            ui.label('Manage categories and currencies available in dropdowns.').classes('text-sm text-gray-500 -mt-2 mb-2')

            expense_cats_editor = ListEditor('Expense Categories', settings.EXPENSE_CATEGORIES)
            expense_cats_editor.render()
            
            income_cats_editor = ListEditor('Income Categories', settings.INCOME_CATEGORIES)
            income_cats_editor.render()
            
            currencies_editor = ListEditor('Currencies', settings.CURRENCIES)
            currencies_editor.render()

        # --- UI & System Settings ---
        with ui.card().classes('w-full p-6 shadow-sm gap-4'):
            ui.label('🛠️ UI & System Settings').classes('text-lg font-bold text-gray-700')
            
            with ui.grid(columns=2).classes('w-full gap-4'):
                default_currency = ui.select(
                    options=settings.CURRENCIES,
                    label='Default Currency',
                    value=settings.DEFAULT_CURRENCY
                ).classes('w-full')
                with default_currency:
                    ui.tooltip('Pre-selected currency when adding a new transaction.').props('anchor="bottom left" self="top left"')

                theme_mode = ui.select(
                    options=['light', 'dark', 'auto'],
                    label='Theme Mode',
                    value=settings.THEME_MODE
                ).classes('w-full')
                with theme_mode:
                    ui.tooltip('Choose app theme: light, dark, or follow system (auto).').props('anchor="bottom left" self="top left"')

                lookback = ui.number(
                    label='Dashboard Years Lookback',
                    value=settings.DASHBOARD_YEARS_LOOKBACK,
                    precision=0,
                    min=1, max=50
                ).classes('w-full')
                with lookback:
                    ui.tooltip('How many years back the dashboard filters should include.').props('anchor="bottom left" self="top left"')
                
                retention = ui.number(
                    label='Upload Retention (Minutes)',
                    value=settings.UPLOAD_RETENTION_MINUTES,
                    precision=0,
                    min=1
                ).classes('w-full')
                with retention:
                    ui.tooltip('Automatically delete uploaded receipt images older than this value (minutes).').props('anchor="bottom left" self="top left"')

                enable_charts = ui.switch(
                    text='Enable Charts',
                    value=settings.ENABLE_CHARTS
                ).classes('w-full')
                with enable_charts:
                    ui.tooltip('Toggle chart rendering on the dashboard.').props('anchor="bottom left" self="top left"')

                lightweight_charts = ui.switch(
                    text='Lightweight Charts',
                    value=settings.LIGHTWEIGHT_CHARTS
                ).classes('w-full')
                with lightweight_charts:
                    ui.tooltip('Use lightweight charts for better performance.').props('anchor="bottom left" self="top left"')

        def save_settings():
            try:
                # Update in-memory settings
                settings.AI_PROVIDER = ai_provider.value
                settings.GOOGLE_API_KEY = google_key.value
                settings.OPENAI_API_KEY = openai_key.value
                
                settings.EXPENSE_CATEGORIES = expense_cats_editor.items
                settings.INCOME_CATEGORIES = income_cats_editor.items
                settings.CURRENCIES = currencies_editor.items
                
                settings.DEFAULT_CURRENCY = default_currency.value
                settings.THEME_MODE = theme_mode.value

                settings.DASHBOARD_YEARS_LOOKBACK = int(lookback.value)
                settings.UPLOAD_RETENTION_MINUTES = int(retention.value)
                settings.ENABLE_CHARTS = bool(enable_charts.value)
                settings.LIGHTWEIGHT_CHARTS = bool(lightweight_charts.value)
                
                # Persist to user_settings.json (JSON is better suited for complex data types and user prefs)
                # NOTE: API keys are excluded here to prevent saving secrets to this file.
                user_settings = {
                    "AI_PROVIDER": settings.AI_PROVIDER,
                    "EXPENSE_CATEGORIES": settings.EXPENSE_CATEGORIES,
                    "INCOME_CATEGORIES": settings.INCOME_CATEGORIES,
                    "CURRENCIES": settings.CURRENCIES,
                    "DEFAULT_CURRENCY": settings.DEFAULT_CURRENCY,
                    "THEME_MODE": settings.THEME_MODE,
                    "DASHBOARD_YEARS_LOOKBACK": settings.DASHBOARD_YEARS_LOOKBACK,
                    "UPLOAD_RETENTION_MINUTES": settings.UPLOAD_RETENTION_MINUTES,
                    "ENABLE_CHARTS": settings.ENABLE_CHARTS,
                    "LIGHTWEIGHT_CHARTS": settings.LIGHTWEIGHT_CHARTS
                }
                
                with open(USER_SETTINGS_PATH, "w") as f:
                    json.dump(user_settings, f, indent=4)
                
                ui.notify('Settings saved successfully!', type='positive')
                
            except Exception as e:
                ui.notify(f'Error saving settings: {str(e)}', type='negative')

    # Floating Save Button (Pinned)
    with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        ui.button('Save Changes', on_click=save_settings, icon='save') \
            .classes('bg-blue-600 text-white text-lg px-8 py-2 shadow-lg')
