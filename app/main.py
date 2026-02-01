from nicegui import ui, app
from fastapi.responses import RedirectResponse
from app.core.database import Base, engine
from app.core.config import settings
from app.ui.dashboard import dashboard_page
from app.ui.add_expense import add_expense_page
from app.ui.history import history_page
from app.ui.settings_page import settings_page
import os

# Ensure data directory exists for SQLite and settings
os.makedirs('app/data', exist_ok=True)

# Initialize DB tables (optional for faster startup in production)
if settings.INIT_DB_ON_STARTUP:
    Base.metadata.create_all(bind=engine)

# Serve uploads directory
os.makedirs('app/data/uploads', exist_ok=True)
app.add_static_files('/uploads', 'app/data/uploads')
app.add_static_files('/ui/static', 'app/ui/static')

def check_auth():
    if not app.storage.user.get('authenticated', False):
        return RedirectResponse('/login')
    return None

@ui.page('/login')
def login():
    def try_login():
        if username.value == settings.ADMIN_USERNAME and password.value == settings.ADMIN_PASSWORD:
            app.storage.user['authenticated'] = True
            ui.navigate.to('/')
        else:
            ui.notify('Invalid username or password', color='negative')

    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')

    with ui.card().classes('absolute-center w-80 p-6 shadow-lg'):
        ui.label('🔐 Login').classes('text-2xl font-bold mb-4 text-center w-full')
        username = ui.input('Username').classes('w-full mb-2').on('keydown.enter', try_login)
        password = ui.input('Password', password=True, password_toggle_button=True).classes('w-full mb-4').on('keydown.enter', try_login)
        ui.button('Login', on_click=try_login).classes('w-full').props('color=primary')

@ui.page('/')
def index_page():
    if auth := check_auth(): return auth
    dashboard_page()

@ui.page('/add')
def add_page():
    if auth := check_auth(): return auth
    add_expense_page()

@ui.page('/history')
def history_page_route():
    if auth := check_auth(): return auth
    history_page()

@ui.page('/settings')
def settings_page_route():
    if auth := check_auth(): return auth
    settings_page()

ui.run(
    title='XpenseTracker',
    port=8501,
    favicon='💰',
    storage_secret=settings.AUTH_SECRET,
    reload=False
)
