from nicegui import ui
from app.core.config import settings
from app.ui.layout import theme
import json
import os

def settings_page():
    theme('settings')
    
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto gap-6'):
        ui.label('⚙️ Settings').classes('text-2xl font-bold text-gray-800')
        
        with ui.card().classes('w-full p-6 shadow-sm gap-4'):
            ui.label('AI Configuration').classes('text-lg font-bold text-gray-700')
            
            ai_provider = ui.select(
                options=['gemini', 'openai', 'testing'],
                label='AI Provider',
                value=settings.AI_PROVIDER
            ).classes('w-full')
            
            google_key = ui.input(
                label='Google API Key',
                value=settings.GOOGLE_API_KEY,
                password=True
            ).classes('w-full')
            
            openai_key = ui.input(
                label='OpenAI API Key',
                value=settings.OPENAI_API_KEY,
                password=True
            ).classes('w-full')

        with ui.card().classes('w-full p-6 shadow-sm gap-4'):
            ui.label('App Constants').classes('text-lg font-bold text-gray-700')
            
            def list_to_str(l):
                return ", ".join(l)
            
            def str_to_list(s):
                return [x.strip() for x in s.split(',') if x.strip()]

            expense_cats = ui.textarea(
                label='Expense Categories (comma separated)',
                value=list_to_str(settings.EXPENSE_CATEGORIES)
            ).classes('w-full')
            
            income_cats = ui.textarea(
                label='Income Categories (comma separated)',
                value=list_to_str(settings.INCOME_CATEGORIES)
            ).classes('w-full')
            
            currencies = ui.input(
                label='Currencies (comma separated)',
                value=list_to_str(settings.CURRENCIES)
            ).classes('w-full')

        with ui.card().classes('w-full p-6 shadow-sm gap-4'):
            ui.label('Other Settings').classes('text-lg font-bold text-gray-700')
            
            lookback = ui.number(
                label='Dashboard Years Lookback',
                value=settings.DASHBOARD_YEARS_LOOKBACK,
                precision=0
            ).classes('w-full')
            
            retention = ui.number(
                label='Upload Retention (Minutes)',
                value=settings.UPLOAD_RETENTION_MINUTES,
                precision=0
            ).classes('w-full')

        def save_settings():
            try:
                # Update in-memory settings
                settings.AI_PROVIDER = ai_provider.value
                settings.GOOGLE_API_KEY = google_key.value
                settings.OPENAI_API_KEY = openai_key.value
                
                settings.EXPENSE_CATEGORIES = str_to_list(expense_cats.value)
                settings.INCOME_CATEGORIES = str_to_list(income_cats.value)
                settings.CURRENCIES = str_to_list(currencies.value)
                
                settings.DASHBOARD_YEARS_LOOKBACK = int(lookback.value)
                settings.UPLOAD_RETENTION_MINUTES = int(retention.value)
                
                # Persist to .env
                env_content = ""
                # Read existing env to preserve DB settings if they exist
                env_path = ".env"
                existing_env = {}
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            if "=" in line:
                                key, val = line.strip().split("=", 1)
                                existing_env[key] = val
                
                # Update values
                existing_env['AI_PROVIDER'] = settings.AI_PROVIDER
                existing_env['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
                existing_env['OPENAI_API_KEY'] = settings.OPENAI_API_KEY
                
                # For lists, Pydantic BaseSettings can read JSON strings
                existing_env['EXPENSE_CATEGORIES'] = json.dumps(settings.EXPENSE_CATEGORIES)
                existing_env['INCOME_CATEGORIES'] = json.dumps(settings.INCOME_CATEGORIES)
                existing_env['CURRENCIES'] = json.dumps(settings.CURRENCIES)
                
                existing_env['DASHBOARD_YEARS_LOOKBACK'] = str(settings.DASHBOARD_YEARS_LOOKBACK)
                existing_env['UPLOAD_RETENTION_MINUTES'] = str(settings.UPLOAD_RETENTION_MINUTES)
                
                # Write back
                with open(env_path, "w") as f:
                    for key, val in existing_env.items():
                        f.write(f"{key}={val}\n")
                
                ui.notify('Settings saved successfully!', type='positive')
                
            except Exception as e:
                ui.notify(f'Error saving settings: {str(e)}', type='negative')

        ui.button('Save Settings', on_click=save_settings).classes('w-full bg-blue-600 text-white text-lg h-12')
